from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from pathlib import Path
from typing import Any, Optional
from urllib import error, request


def _ensure_repo_root_on_path_for_direct_run() -> None:
    """Allow direct file execution without breaking package imports."""
    if __package__ not in (None, ""):
        return
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_ensure_repo_root_on_path_for_direct_run()

if __package__ in (None, ""):
    from Backend.settings import Settings, get_settings
else:
    from .settings import Settings, get_settings

# F5 direct-debug defaults (edit these quickly when debugging).
DEBUG_DEFAULT_USER_INPUT = "近日油价调整消息。"
DEBUG_DEFAULT_MESSAGES_JSON = ""
DEBUG_DEFAULT_TIMEOUT_SECONDS = 90.0
DEBUG_VERBOSE_DEFAULT = True
FIXED_SEARCH_RECENCY_FILTER = "week"
FIXED_EDITION = "lite"
FIXED_SEARCH_SOURCE = "baidu_search_v2"
DEFAULT_WEB_TOP_K = 3
MAX_WEB_TOP_K = 50


class SearchProviderError(RuntimeError):
    """Structured provider error for clearer CLI diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        api_code: int | str | None = None,
        request_id: str | None = None,
        api_message: str | None = None,
        raw_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.api_code = api_code
        self.request_id = request_id
        self.api_message = api_message
        self.raw_text = raw_text


def _try_parse_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _resolve_search_api_key(settings: Settings) -> str:
    api_key = (settings.baidu_search_api_key or "").strip()
    if not api_key:
        raise RuntimeError(
            "Missing API key. Set BAIDU_QIANFAN_API_KEY (or QIANFAN_API_KEY / BAIDU_API_KEY) in the environment or .env."
        )
    return api_key


def _build_search_endpoint(settings: Settings) -> str:
    base_url = (settings.baidu_search_base_url or "").rstrip("/")
    if not base_url:
        raise RuntimeError("Invalid BAIDU_SEARCH_BASE_URL: empty value")
    return f"{base_url}/v2/ai_search/web_search"


def _normalize_messages(messages: Any, user_input: str | None = None) -> list[dict[str, str]]:
    if isinstance(messages, list) and messages:
        normalized_messages: list[dict[str, str]] = []
        for item in messages:
            if not isinstance(item, dict):
                raise ValueError("messages items must be objects with role/content")
            role = str(item.get("role", "")).strip()
            content = str(item.get("content", "")).strip()
            if not role or not content:
                raise ValueError("each message requires non-empty role and content")
            normalized_messages.append({"role": role, "content": content})
        return normalized_messages

    text = (user_input or "").strip()
    if not text:
        raise ValueError("messages cannot be empty (or provide user_input)")
    return [{"role": "user", "content": text}]


def _build_resource_type_filter(web_top_k: int | None = None) -> list[dict[str, int | str]]:
    resolved_top_k = DEFAULT_WEB_TOP_K if web_top_k is None else int(web_top_k)
    if resolved_top_k < 1 or resolved_top_k > MAX_WEB_TOP_K:
        raise ValueError(f"web_top_k must be between 1 and {MAX_WEB_TOP_K}")
    return [{"type": "web", "top_k": resolved_top_k}]


def _request_baidu_search(
    *,
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(endpoint, data=body, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            response_text = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        err_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        err_json = _try_parse_json(err_text)
        api_code = err_json.get("code") if err_json else None
        request_id = None
        api_message = None
        if err_json:
            request_id = str(err_json.get("requestId") or err_json.get("request_id") or "") or None
            api_message = str(err_json.get("message") or "") or None
        raise SearchProviderError(
            f"Baidu search request failed (HTTP {exc.code})",
            status_code=exc.code,
            api_code=api_code,
            request_id=request_id,
            api_message=api_message,
            raw_text=err_text or str(exc.reason),
        ) from exc
    except error.URLError as exc:
        raise SearchProviderError(
            "Baidu search network request failed",
            api_message=str(exc.reason),
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise SearchProviderError(
            "Baidu search request timed out",
            api_message=str(exc),
        ) from exc

    try:
        return json.loads(response_text or "{}")
    except json.JSONDecodeError as exc:
        raise SearchProviderError(
            "Baidu search response is not valid JSON",
            raw_text=response_text[:200],
        ) from exc


def baidu_web_search(
    *,
    messages: Any,
    user_input: str | None = None,
    web_top_k: int | None = None,
    timeout: Optional[float] = None,
) -> dict[str, Any]:
    """Call Baidu Qianfan web search API (/v2/ai_search/web_search)."""
    settings = get_settings()
    api_key = _resolve_search_api_key(settings)
    endpoint = _build_search_endpoint(settings)

    payload: dict[str, Any] = {
        "messages": _normalize_messages(messages=messages, user_input=user_input),
        "edition": FIXED_EDITION,
        "search_source": FIXED_SEARCH_SOURCE,
        "resource_type_filter": _build_resource_type_filter(web_top_k),
        "search_recency_filter": FIXED_SEARCH_RECENCY_FILTER,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    timeout_seconds = (
        float(timeout)
        if timeout is not None
        else float(settings.baidu_search_timeout_seconds)
    )
    return _request_baidu_search(
        endpoint=endpoint,
        headers=headers,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


class SearchProvider:
    """Facade class for backend search integrations."""

    @staticmethod
    def web_search(
        *,
        messages: Any,
        user_input: str | None = None,
        web_top_k: int | None = None,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        return baidu_web_search(
            messages=messages,
            user_input=user_input,
            web_top_k=web_top_k,
            timeout=timeout,
        )


def _parse_messages_json(raw: str | None) -> Any:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--messages-json is invalid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("--messages-json must be a JSON array")
    return parsed


def _format_cli_error(exc: Exception) -> str:
    if isinstance(exc, SearchProviderError):
        lines = ["[search-debug] ERROR", f"  summary: {exc}"]
        if exc.status_code is not None:
            lines.append(f"  http_status: {exc.status_code}")
        if exc.api_code is not None:
            lines.append(f"  api_code: {exc.api_code}")
        if exc.request_id:
            lines.append(f"  request_id: {exc.request_id}")
        if exc.api_message:
            lines.append(f"  api_message: {exc.api_message}")
        if exc.raw_text:
            lines.append(f"  raw: {exc.raw_text[:300]}")

        # Common onboarding pitfall for Qianfan auth.
        if exc.status_code == 401:
            lines.append(
                "  hint: Check BAIDU_QIANFAN_API_KEY; use the exact Qianfan API key value only (no 'Bearer' prefix, no quotes, no extra spaces)."
            )
        if "timed out" in (exc.api_message or "").lower() or "timed out" in str(exc).lower():
            lines.append(
                "  hint: Try --timeout 90 or disable deep search with --disable-deep-search during debugging."
            )
        return "\n".join(lines)

    return f"[search-debug] ERROR: {exc}"


def _build_debug_request_payload(
    *,
    messages: Any,
    user_input: str | None,
) -> dict[str, Any]:
    return {
        "messages": _normalize_messages(messages=messages, user_input=user_input),
        "edition": FIXED_EDITION,
        "search_source": FIXED_SEARCH_SOURCE,
        "resource_type_filter": _build_resource_type_filter(),
        "search_recency_filter": FIXED_SEARCH_RECENCY_FILTER,
    }


def _extract_verbose_metrics(response: dict[str, Any], elapsed_seconds: float) -> dict[str, Any]:
    search_results = response.get("search_results") if isinstance(response, dict) else None
    results_count = len(search_results) if isinstance(search_results, list) else 0
    return {
        "latency_seconds": elapsed_seconds,
        "request_id": response.get("request_id") if isinstance(response, dict) else None,
        "results_count": results_count,
    }


def _format_verbose_metrics(metrics: dict[str, Any], timeout_seconds: float) -> str:
    return (
        f"[VERBOSE] endpoint=/v2/ai_search/web_search\n"
        f"[VERBOSE] edition={FIXED_EDITION} recency={FIXED_SEARCH_RECENCY_FILTER}\n"
        f"[VERBOSE] web_top_k={DEFAULT_WEB_TOP_K}\n"
        f"[VERBOSE] timeout={timeout_seconds:.1f}s\n"
        f"[VERBOSE] latency={metrics.get('latency_seconds', 0.0):.3f}s\n"
        f"[VERBOSE] request_id={metrics.get('request_id')}\n"
        f"[VERBOSE] results={metrics.get('results_count')}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Standalone Baidu web search debugger (Backend.search_provider)."
    )
    parser.add_argument(
        "--user-input",
        default=DEBUG_DEFAULT_USER_INPUT,
        help="User query text. Used when --messages-json is not provided.",
    )
    parser.add_argument(
        "--messages-json",
        default=DEBUG_DEFAULT_MESSAGES_JSON,
        help='Optional full messages JSON array, e.g. [{"role":"user","content":"..."}]',
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEBUG_DEFAULT_TIMEOUT_SECONDS,
        help="Override request timeout seconds",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON output",
    )
    parser.add_argument(
        "--show-request",
        action="store_true",
        help="Pretty print the outgoing request body before sending.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=DEBUG_VERBOSE_DEFAULT,
        help="Print timing and diagnostics to stderr.",
    )
    parser.add_argument(
        "--quiet-verbose",
        action="store_true",
        help="Disable verbose diagnostics for this run.",
    )

    args = parser.parse_args()
    verbose_enabled = bool(args.verbose and not args.quiet_verbose)
    started = time.perf_counter()

    try:
        messages = _parse_messages_json(args.messages_json)
        request_preview: dict[str, Any] | None = None
        if args.show_request:
            request_preview = _build_debug_request_payload(
                messages=messages,
                user_input=args.user_input,
            )
            print("[search-debug] request:")
            print(json.dumps(request_preview, ensure_ascii=False, indent=2))

        response = SearchProvider.web_search(
            messages=messages,
            user_input=args.user_input,
            timeout=args.timeout,
        )
        elapsed_seconds = time.perf_counter() - started
    except Exception as exc:
        if verbose_enabled:
            print(f"[VERBOSE] failed_after={time.perf_counter() - started:.3f}s", file=sys.stderr)
        print(_format_cli_error(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    if args.compact:
        print(json.dumps(response, ensure_ascii=False))
    else:
        print(json.dumps(response, ensure_ascii=False, indent=2))

    if verbose_enabled:
        metrics = _extract_verbose_metrics(response=response, elapsed_seconds=elapsed_seconds)
        print(
            _format_verbose_metrics(metrics=metrics, timeout_seconds=float(args.timeout)),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
