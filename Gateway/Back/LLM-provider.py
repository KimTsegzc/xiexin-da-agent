import json
import os
import threading
import time
from pathlib import Path
from typing import Iterator, Optional

from openai import OpenAI

# Keep model choice centralized in code for eahisier controlled switching.
ACTIVE_MODEL = "qwen3.5-flash"
VERBOSE_MODE_DEFAULT = True
STREAM_MODE_DEFAULT = True
STREAM_SMOOTH_MIN_CHARS = 12
STREAM_SMOOTH_MAX_WAIT_SECONDS = 0.05


def load_config() -> dict:
    """Load config from ./config.json (cwd first, then script directory)."""
    repo_root = Path(__file__).resolve().parents[2]
    candidate_paths = [
        repo_root / "config.json",
        Path(__file__).resolve().parent / "config.json",
        Path.cwd() / "config.json",
    ]

    config_path = next((p for p in candidate_paths if p.exists()), None)
    if not config_path:
        searched = "\n".join(str(p) for p in candidate_paths)
        raise FileNotFoundError(
            "config.json not found. Please create it in one of these locations:\n"
            f"{searched}"
        )

    try:
        with open(config_path, "r", encoding="utf-8") as fp:
            config = json.load(fp)
            if not isinstance(config, dict):
                raise ValueError("config.json root must be a JSON object")
            return config
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in config file: {config_path} ({exc})") from exc


def build_client(config: dict) -> OpenAI:
    api_key = (
        config.get("api_key")
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("ALIYUN_BAILIAN_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "Missing api_key. Fill it in config.json or set DASHSCOPE_API_KEY/ALIYUN_BAILIAN_API_KEY."
        )

    base_url = config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def _resolve_model(model: Optional[str] = None) -> str:
    return model or ACTIVE_MODEL


def _resolve_request_options(config: dict) -> dict:
    """Pick optional generation parameters from config when provided."""
    options = {}
    for key in ("temperature", "top_p", "max_tokens"):
        if key in config and config[key] is not None:
            options[key] = config[key]
    return options


def _extract_usage_metrics(completion) -> dict:
    usage = getattr(completion, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def _build_messages(config: dict, user_input: str) -> list[dict]:
    return [
        {"role": "system", "content": config.get("system_prompt", "You are a helpful assistant.")},
        {"role": "user", "content": user_input},
    ]


def LLM_stream(
    user_input: str,
    model: Optional[str] = None,
    smooth: bool = True,
) -> Iterator[dict]:
    """Stream model output as events for backend usage.

    Yields events with shape:
    - {"type": "pulse", "stage": "accepted|first_token", "elapsed_seconds": float}
    - {"type": "delta", "content": "..."}
    - {"type": "done", "content": "full text", "metrics": {...}}
    """
    config = load_config()
    client = build_client(config)
    model_name = _resolve_model(model=model)
    request_options = _resolve_request_options(config)

    started = time.perf_counter()
    yield {"type": "pulse", "stage": "accepted", "elapsed_seconds": 0.0}

    stream = client.chat.completions.create(
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model=model_name,
        messages=_build_messages(config, user_input),
        stream=True,
        stream_options={"include_usage": True},
        **request_options,
    )

    all_parts = []
    pending_parts = []
    last_emit = started
    first_token_emitted = False
    usage_metrics = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }

    for chunk in stream:
        chunk_usage = _extract_usage_metrics(chunk)
        if chunk_usage["total_tokens"] is not None:
            usage_metrics = chunk_usage

        if not getattr(chunk, "choices", None):
            continue

        delta = chunk.choices[0].delta
        piece = getattr(delta, "content", None)
        if piece:
            if not first_token_emitted:
                first_token_emitted = True
                yield {
                    "type": "pulse",
                    "stage": "first_token",
                    "elapsed_seconds": time.perf_counter() - started,
                }

            all_parts.append(piece)
            if not smooth:
                yield {"type": "delta", "content": piece}
                continue

            pending_parts.append(piece)
            pending_text = "".join(pending_parts)
            now = time.perf_counter()
            should_flush = (
                len(pending_text) >= STREAM_SMOOTH_MIN_CHARS
                or (now - last_emit) >= STREAM_SMOOTH_MAX_WAIT_SECONDS
            )
            if should_flush:
                yield {"type": "delta", "content": pending_text}
                pending_parts.clear()
                last_emit = now

    if pending_parts:
        yield {"type": "delta", "content": "".join(pending_parts)}

    elapsed = time.perf_counter() - started
    content = "".join(all_parts)
    throughput_tokens = usage_metrics["completion_tokens"] or usage_metrics["total_tokens"]
    metrics = {
        "model": model_name,
        "base_url": config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "request_options": request_options,
        "latency_seconds": elapsed,
        "throughput_tokens_per_second": (
            (throughput_tokens / elapsed) if throughput_tokens and elapsed > 0 else None
        ),
        **usage_metrics,
    }
    yield {"type": "done", "content": content, "metrics": metrics}


def LLM_with_metrics(
    user_input: str,
    model: Optional[str] = None,
) -> tuple[str, dict]:
    """Call LLM and return assistant content plus runtime metrics."""
    final_content = ""
    final_metrics = {}
    for event in LLM_stream(user_input, model=model):
        if event.get("type") == "done":
            final_content = event.get("content", "")
            final_metrics = event.get("metrics", {})
    return final_content, final_metrics


def LLM(user_input: str, model: Optional[str] = None) -> str:
    """Call LLM and return assistant content only."""
    content, _ = LLM_with_metrics(user_input, model=model)
    return content


def _format_verbose_metrics(metrics: dict) -> str:
    throughput = metrics.get("throughput_tokens_per_second")
    throughput_text = f"{throughput:.2f} tokens/s" if throughput is not None else "N/A"
    return (
        f"[VERBOSE] model={metrics.get('model')}\n"
        f"[VERBOSE] latency={metrics.get('latency_seconds', 0.0):.3f}s\n"
        f"[VERBOSE] usage prompt={metrics.get('prompt_tokens')} completion={metrics.get('completion_tokens')} total={metrics.get('total_tokens')}\n"
        f"[VERBOSE] throughput={throughput_text}"
    )


def _start_cli_wait_spinner(prefix: str = "output >> "):
    stop_event = threading.Event()

    def _spin() -> None:
        frames = "|/-\\"
        index = 0
        while not stop_event.is_set():
            frame = frames[index % len(frames)]
            print(f"\r{prefix}[waiting {frame}]", end="", flush=True)
            index += 1
            stop_event.wait(0.12)
        print(f"\r{prefix}", end="", flush=True)

    thread = threading.Thread(target=_spin, daemon=True)
    thread.start()
    return stop_event, thread


def _stop_cli_wait_spinner(stop_event, thread) -> None:
    if stop_event is None or thread is None:
        return
    stop_event.set()
    thread.join(timeout=0.4)


def main() -> None:
    verbose_mode = VERBOSE_MODE_DEFAULT
    stream_mode = STREAM_MODE_DEFAULT
    print("LLM Provider ready. Type your prompt after 'input >>'. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("input >> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nbye")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("bye")
            break
        if not user_input:
            continue

        try:
            if stream_mode:
                print("output >> ", end="", flush=True)
                final_metrics = {}
                spinner_stop_event = None
                spinner_thread = None
                for event in LLM_stream(user_input):
                    if event.get("type") == "pulse":
                        if event.get("stage") == "accepted" and spinner_stop_event is None:
                            spinner_stop_event, spinner_thread = _start_cli_wait_spinner("output >> ")
                        elif event.get("stage") == "first_token":
                            _stop_cli_wait_spinner(spinner_stop_event, spinner_thread)
                            spinner_stop_event, spinner_thread = None, None
                    elif event.get("type") == "delta":
                        _stop_cli_wait_spinner(spinner_stop_event, spinner_thread)
                        spinner_stop_event, spinner_thread = None, None
                        print(event.get("content", ""), end="", flush=True)
                    elif event.get("type") == "done":
                        final_metrics = event.get("metrics", {})
                _stop_cli_wait_spinner(spinner_stop_event, spinner_thread)
                print()
                if verbose_mode:
                    print(_format_verbose_metrics(final_metrics))
            else:
                answer, metrics = LLM_with_metrics(user_input)
                print(f"output >> {answer}")
                if verbose_mode:
                    print(_format_verbose_metrics(metrics))
        except KeyboardInterrupt:
            print("\noutput >> [CANCELLED]")
        except Exception as exc:
            print(f"output >> [ERROR] {exc}")


if __name__ == "__main__":
    main()