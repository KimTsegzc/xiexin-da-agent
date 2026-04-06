from __future__ import annotations

import threading
import time
from typing import Iterator, Optional

from openai import OpenAI
from .settings import AVAILABLE_MODELS, Settings, get_settings, load_system_prompt


def get_model_list() -> list[str]:
    """Return the registry of available models (for frontend dropdowns etc.)."""
    return AVAILABLE_MODELS

VERBOSE_MODE_DEFAULT = True
STREAM_MODE_DEFAULT = True
STREAM_SMOOTH_MIN_CHARS = 12
STREAM_SMOOTH_MAX_WAIT_SECONDS = 0.05


def build_client(settings: Settings) -> OpenAI:
    if not settings.api_key:
        raise RuntimeError(
            "Missing API key. Set DASHSCOPE_API_KEY or ALIYUN_BAILIAN_API_KEY in the environment or .env."
        )

    return OpenAI(api_key=settings.api_key, base_url=settings.base_url)


def _resolve_model(settings: Settings, model: Optional[str] = None) -> str:
    return model or settings.model


def _resolve_request_options(settings: Settings) -> dict:
    """Pick optional generation parameters from settings when provided."""
    options = {}
    for key in ("temperature", "top_p", "max_tokens"):
        value = getattr(settings, key)
        if value is not None:
            options[key] = value
    return options


def _extract_usage_metrics(completion) -> dict:
    usage = getattr(completion, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def _build_messages(settings: Settings, user_input: str) -> list[dict]:
    return [
        {"role": "system", "content": load_system_prompt()},
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
    settings = get_settings()
    client = build_client(settings)
    model_name = _resolve_model(settings, model=model)
    request_options = _resolve_request_options(settings)

    started = time.perf_counter()
    yield {"type": "pulse", "stage": "accepted", "elapsed_seconds": 0.0}

    stream = client.chat.completions.create(
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model=model_name,
        messages=_build_messages(settings, user_input),
        stream=True,
        stream_options={"include_usage": True},
        **request_options,
    )

    all_parts = []
    pending_parts = []
    last_emit = started
    first_token_emitted = False
    first_token_latency_seconds = None
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
                first_token_latency_seconds = time.perf_counter() - started
                yield {
                    "type": "pulse",
                    "stage": "first_token",
                    "elapsed_seconds": first_token_latency_seconds,
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
        "base_url": settings.base_url,
        "request_options": request_options,
        "first_token_latency_seconds": first_token_latency_seconds,
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
    first_token_latency = metrics.get("first_token_latency_seconds")
    first_token_latency_text = (
        f"{first_token_latency:.3f}s" if first_token_latency is not None else "N/A"
    )
    return (
        f"[VERBOSE] model={metrics.get('model')}\n"
        f"[VERBOSE] first_token_latency={first_token_latency_text}\n"
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


class LLMProvider:
    """Facade class for external imports from Backend."""

    @staticmethod
    def stream(
        user_input: str,
        model: Optional[str] = None,
        smooth: bool = True,
    ) -> Iterator[dict]:
        yield from LLM_stream(user_input=user_input, model=model, smooth=smooth)

    @staticmethod
    def with_metrics(
        user_input: str,
        model: Optional[str] = None,
    ) -> tuple[str, dict]:
        return LLM_with_metrics(user_input=user_input, model=model)

    @staticmethod
    def text(
        user_input: str,
        model: Optional[str] = None,
    ) -> str:
        return LLM(user_input=user_input, model=model)


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