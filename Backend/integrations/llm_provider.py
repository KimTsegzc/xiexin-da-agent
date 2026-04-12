from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from openai import OpenAI


def _ensure_repo_root_on_path_for_direct_run() -> None:
    if __package__ not in (None, ""):
        return
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_ensure_repo_root_on_path_for_direct_run()

if __package__ in (None, ""):
    from Backend.settings import AVAILABLE_MODELS, Settings, get_llm_settings, get_settings, load_system_prompt
else:
    from ..settings import AVAILABLE_MODELS, Settings, get_llm_settings, get_settings, load_system_prompt


def get_model_list() -> list[str]:
    """Return the registry of available models for UI and routing consumers."""
    return AVAILABLE_MODELS


VERBOSE_MODE_DEFAULT = True
STREAM_MODE_DEFAULT = True
STREAM_SMOOTH_MIN_CHARS = 12
STREAM_SMOOTH_MAX_WAIT_SECONDS = 0.05


def build_client(settings: Settings) -> OpenAI:
    llm_settings = get_llm_settings(settings)
    if not llm_settings.api_key:
        raise RuntimeError(
            "Missing API key. Set DASHSCOPE_API_KEY or ALIYUN_BAILIAN_API_KEY in the environment or .env."
        )
    return OpenAI(api_key=llm_settings.api_key, base_url=llm_settings.base_url)


def _resolve_model(settings: Settings, model: Optional[str] = None) -> str:
    llm_settings = get_llm_settings(settings)
    return model or llm_settings.model


def _resolve_request_options(settings: Settings) -> dict:
    llm_settings = get_llm_settings(settings)
    options = {}
    for key in ("temperature", "top_p", "max_tokens"):
        value = getattr(llm_settings, key)
        if value is not None:
            options[key] = value
    return options


def _resolve_enable_search(settings: Settings, enable_search: Optional[bool] = None) -> bool:
    if enable_search is None:
        return get_llm_settings(settings).enable_search
    return bool(enable_search)


def _build_extra_body(enable_search: bool) -> dict:
    return {"enable_search": enable_search}


def _merge_request_options(
    settings: Settings,
    request_options_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_options = _resolve_request_options(settings)
    if not request_options_override:
        return request_options
    for key, value in request_options_override.items():
        if value is None:
            request_options.pop(key, None)
            continue
        request_options[key] = value
    return request_options


def _safe_json_loads(raw_text: str) -> Any:
    if not raw_text:
        return {}
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text


def _extract_usage_metrics(completion) -> dict:
    usage = getattr(completion, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def _extract_message_content(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(getattr(item, "text", "") or ""))
        return "".join(parts)
    return str(content or "")


def _extract_tool_calls(message) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for tool_call in getattr(message, "tool_calls", None) or []:
        function = getattr(tool_call, "function", None)
        arguments_text = str(getattr(function, "arguments", "") or "")
        calls.append(
            {
                "id": getattr(tool_call, "id", None),
                "type": getattr(tool_call, "type", None) or "function",
                "function": {
                    "name": getattr(function, "name", None),
                    "arguments": _safe_json_loads(arguments_text),
                    "arguments_text": arguments_text,
                },
            }
        )
    return calls


def _build_runtime_system_tail(now: Optional[datetime] = None) -> str:
    current = now or datetime.now()
    return f"今天是“{current.strftime('%Y年%m月%d日')}”，现在是“{current.strftime('%H:%M')}”"


def _attach_runtime_system_tail(messages: list[dict], now: Optional[datetime] = None) -> list[dict]:
    runtime_tail = _build_runtime_system_tail(now)
    normalized_messages = [dict(message) for message in messages]
    for index, message in enumerate(normalized_messages):
        if str(message.get("role") or "").strip() != "system":
            continue
        content = str(message.get("content") or "").rstrip()
        if runtime_tail in content:
            return normalized_messages
        normalized_messages[index]["content"] = f"{content}\n\n{runtime_tail}" if content else runtime_tail
        return normalized_messages
    return [{"role": "system", "content": runtime_tail}, *normalized_messages]


def _build_messages(settings: Settings, user_input: str) -> list[dict]:
    return _attach_runtime_system_tail(
        [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user_input},
        ]
    )


def _create_chat_completion(
    *,
    settings: Settings,
    messages: list[dict],
    model: Optional[str],
    enable_search: Optional[bool],
    stream: bool,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | str | None = None,
    request_options_override: dict[str, Any] | None = None,
    extra_body_override: dict[str, Any] | None = None,
):
    llm_settings = get_llm_settings(settings)
    client = build_client(settings)
    model_name = _resolve_model(settings, model=model)
    request_options = _merge_request_options(
        settings,
        request_options_override=request_options_override,
    )
    resolved_enable_search = _resolve_enable_search(settings, enable_search=enable_search)
    extra_body = _build_extra_body(resolved_enable_search)
    if extra_body_override:
        extra_body.update(extra_body_override)
    normalized_messages = _attach_runtime_system_tail(messages)
    create_kwargs: dict[str, Any] = {
        "model": model_name,
        "messages": normalized_messages,
        "stream": stream,
        "extra_body": extra_body,
        **request_options,
    }
    if stream:
        create_kwargs["stream_options"] = {"include_usage": True}
    if tools:
        create_kwargs["tools"] = tools
    if tool_choice is not None:
        create_kwargs["tool_choice"] = tool_choice
    return (
        client.chat.completions.create(**create_kwargs),
        model_name,
        request_options,
        resolved_enable_search,
        llm_settings.base_url,
    )


def _stream_chat_completion(
    *,
    settings: Settings,
    messages: list[dict],
    model: Optional[str],
    smooth: bool,
    enable_search: Optional[bool],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | str | None = None,
    request_options_override: dict[str, Any] | None = None,
    extra_body_override: dict[str, Any] | None = None,
) -> Iterator[dict]:
    started = time.perf_counter()
    yield {"type": "pulse", "stage": "accepted", "elapsed_seconds": 0.0}

    stream, model_name, request_options, resolved_enable_search, base_url = _create_chat_completion(
        settings=settings,
        messages=messages,
        model=model,
        enable_search=enable_search,
        stream=True,
        tools=tools,
        tool_choice=tool_choice,
        request_options_override=request_options_override,
        extra_body_override=extra_body_override,
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
    tool_call_parts: dict[int, dict[str, Any]] = {}

    for chunk in stream:
        chunk_usage = _extract_usage_metrics(chunk)
        if chunk_usage["total_tokens"] is not None:
            usage_metrics = chunk_usage

        if not getattr(chunk, "choices", None):
            continue

        delta = chunk.choices[0].delta
        for tool_delta in getattr(delta, "tool_calls", None) or []:
            call_index = int(getattr(tool_delta, "index", 0) or 0)
            current = tool_call_parts.setdefault(
                call_index,
                {"id": None, "type": "function", "function": {"name": "", "arguments_text": ""}},
            )
            if getattr(tool_delta, "id", None):
                current["id"] = tool_delta.id
            if getattr(tool_delta, "type", None):
                current["type"] = tool_delta.type
            function = getattr(tool_delta, "function", None)
            if function is not None:
                if getattr(function, "name", None):
                    current["function"]["name"] = function.name
                if getattr(function, "arguments", None):
                    current["function"]["arguments_text"] += function.arguments

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
    tool_calls = []
    for index in sorted(tool_call_parts):
        item = tool_call_parts[index]
        arguments_text = item["function"].get("arguments_text", "")
        tool_calls.append(
            {
                "id": item.get("id"),
                "type": item.get("type") or "function",
                "function": {
                    "name": item["function"].get("name") or None,
                    "arguments": _safe_json_loads(arguments_text),
                    "arguments_text": arguments_text,
                },
            }
        )
    throughput_tokens = usage_metrics["completion_tokens"] or usage_metrics["total_tokens"]
    metrics = {
        "model": model_name,
        "base_url": base_url,
        "enable_search": resolved_enable_search,
        "request_options": request_options,
        "tool_choice_used": tool_choice,
        "tool_count": len(tools or []),
        "first_token_latency_seconds": first_token_latency_seconds,
        "latency_seconds": elapsed,
        "throughput_tokens_per_second": (
            (throughput_tokens / elapsed) if throughput_tokens and elapsed > 0 else None
        ),
        **usage_metrics,
    }
    yield {"type": "done", "content": content, "metrics": metrics, "tool_calls": tool_calls}


def LLM_stream_messages(
    messages: list[dict],
    model: Optional[str] = None,
    smooth: bool = True,
    enable_search: Optional[bool] = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | str | None = None,
    request_options_override: dict[str, Any] | None = None,
    extra_body_override: dict[str, Any] | None = None,
) -> Iterator[dict]:
    settings = get_settings()
    yield from _stream_chat_completion(
        settings=settings,
        messages=messages,
        model=model,
        smooth=smooth,
        enable_search=enable_search,
        tools=tools,
        tool_choice=tool_choice,
        request_options_override=request_options_override,
        extra_body_override=extra_body_override,
    )


def LLM_with_metrics_messages(
    messages: list[dict],
    model: Optional[str] = None,
    enable_search: Optional[bool] = None,
) -> tuple[str, dict]:
    final_content = ""
    final_metrics = {}
    for event in LLM_stream_messages(messages, model=model, smooth=True, enable_search=enable_search):
        if event.get("type") == "done":
            final_content = event.get("content", "")
            final_metrics = event.get("metrics", {})
    return final_content, final_metrics


def LLM_with_response_messages(
    messages: list[dict],
    model: Optional[str] = None,
    enable_search: Optional[bool] = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | str | None = None,
    request_options_override: dict[str, Any] | None = None,
    extra_body_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    started = time.perf_counter()
    completion, model_name, request_options, resolved_enable_search, base_url = _create_chat_completion(
        settings=settings,
        messages=messages,
        model=model,
        enable_search=enable_search,
        stream=False,
        tools=tools,
        tool_choice=tool_choice,
        request_options_override=request_options_override,
        extra_body_override=extra_body_override,
    )
    elapsed = time.perf_counter() - started
    message = completion.choices[0].message if getattr(completion, "choices", None) else None
    usage_metrics = _extract_usage_metrics(completion)
    tool_calls = _extract_tool_calls(message) if message is not None else []
    return {
        "content": _extract_message_content(message) if message is not None else "",
        "tool_calls": tool_calls,
        "metrics": {
            "model": model_name,
            "base_url": base_url,
            "enable_search": resolved_enable_search,
            "request_options": request_options,
            "tool_choice_used": tool_choice,
            "tool_count": len(tools or []),
            "latency_seconds": elapsed,
            **usage_metrics,
        },
    }


def LLM_stream(
    user_input: str,
    model: Optional[str] = None,
    smooth: bool = True,
    enable_search: Optional[bool] = None,
) -> Iterator[dict]:
    settings = get_settings()
    yield from _stream_chat_completion(
        settings=settings,
        messages=_build_messages(settings, user_input),
        model=model,
        smooth=smooth,
        enable_search=enable_search,
    )


def LLM_with_metrics(
    user_input: str,
    model: Optional[str] = None,
    enable_search: Optional[bool] = None,
) -> tuple[str, dict]:
    final_content = ""
    final_metrics = {}
    for event in LLM_stream(user_input, model=model, enable_search=enable_search):
        if event.get("type") == "done":
            final_content = event.get("content", "")
            final_metrics = event.get("metrics", {})
    return final_content, final_metrics


def LLM(
    user_input: str,
    model: Optional[str] = None,
    enable_search: Optional[bool] = None,
) -> str:
    content, _ = LLM_with_metrics(user_input, model=model, enable_search=enable_search)
    return content


def _format_verbose_metrics(metrics: dict) -> str:
    throughput = metrics.get("throughput_tokens_per_second")
    throughput_text = f"{throughput:.2f} tokens/s" if throughput is not None else "N/A"
    first_token_latency = metrics.get("first_token_latency_seconds")
    first_token_latency_text = f"{first_token_latency:.3f}s" if first_token_latency is not None else "N/A"
    return (
        f"[VERBOSE] model={metrics.get('model')}\n"
        f"[VERBOSE] enable_search={metrics.get('enable_search')}\n"
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
    """Facade class for LLM integration calls."""

    @staticmethod
    def stream(
        user_input: str,
        model: Optional[str] = None,
        smooth: bool = True,
        enable_search: Optional[bool] = None,
    ) -> Iterator[dict]:
        yield from LLM_stream(
            user_input=user_input,
            model=model,
            smooth=smooth,
            enable_search=enable_search,
        )

    @staticmethod
    def stream_messages(
        messages: list[dict],
        model: Optional[str] = None,
        smooth: bool = True,
        enable_search: Optional[bool] = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | str | None = None,
        request_options_override: dict[str, Any] | None = None,
        extra_body_override: dict[str, Any] | None = None,
    ) -> Iterator[dict]:
        yield from LLM_stream_messages(
            messages=messages,
            model=model,
            smooth=smooth,
            enable_search=enable_search,
            tools=tools,
            tool_choice=tool_choice,
            request_options_override=request_options_override,
            extra_body_override=extra_body_override,
        )

    @staticmethod
    def with_metrics(
        user_input: str,
        model: Optional[str] = None,
        enable_search: Optional[bool] = None,
    ) -> tuple[str, dict]:
        return LLM_with_metrics(
            user_input=user_input,
            model=model,
            enable_search=enable_search,
        )

    @staticmethod
    def with_metrics_messages(
        messages: list[dict],
        model: Optional[str] = None,
        enable_search: Optional[bool] = None,
    ) -> tuple[str, dict]:
        return LLM_with_metrics_messages(
            messages=messages,
            model=model,
            enable_search=enable_search,
        )

    @staticmethod
    def with_response_messages(
        messages: list[dict],
        model: Optional[str] = None,
        enable_search: Optional[bool] = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | str | None = None,
        request_options_override: dict[str, Any] | None = None,
        extra_body_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return LLM_with_response_messages(
            messages=messages,
            model=model,
            enable_search=enable_search,
            tools=tools,
            tool_choice=tool_choice,
            request_options_override=request_options_override,
            extra_body_override=extra_body_override,
        )

    @staticmethod
    def complete(
        user_input: str,
        model: Optional[str] = None,
        enable_search: Optional[bool] = None,
    ) -> str:
        return LLM(
            user_input=user_input,
            model=model,
            enable_search=enable_search,
        )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Standalone LLM debugger (Backend.integrations.llm_provider).")
    parser.add_argument("user_input", nargs="?", default="你好", help="User input text")
    parser.add_argument("--model", default=None, help="Optional model override")
    parser.add_argument("--disable-search", action="store_true", help="Disable model-side search")
    parser.add_argument("--no-stream", action="store_true", help="Use non-stream mode")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose metrics")
    args = parser.parse_args()

    if args.no_stream:
        content, metrics = LLM_with_metrics(
            args.user_input,
            model=args.model,
            enable_search=False if args.disable_search else None,
        )
        print(content)
        if not args.quiet:
            print(_format_verbose_metrics(metrics), file=sys.stderr)
        return 0

    stop_event = None
    thread = None
    first_output = True
    try:
        if not args.quiet:
            stop_event, thread = _start_cli_wait_spinner()
        for event in LLM_stream(
            args.user_input,
            model=args.model,
            enable_search=False if args.disable_search else None,
        ):
            if event.get("type") == "delta":
                if stop_event is not None:
                    _stop_cli_wait_spinner(stop_event, thread)
                    stop_event, thread = None, None
                text = event.get("content", "")
                print(text, end="", flush=True)
                first_output = False
            if event.get("type") == "done":
                if stop_event is not None:
                    _stop_cli_wait_spinner(stop_event, thread)
                if not first_output:
                    print()
                if not args.quiet:
                    print(_format_verbose_metrics(event.get("metrics", {})), file=sys.stderr)
                return 0
    finally:
        if stop_event is not None:
            _stop_cli_wait_spinner(stop_event, thread)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())