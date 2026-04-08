from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import parse_qs, urlparse

def _ensure_repo_root_on_path_for_direct_run() -> None:
    """Allow running this file directly without breaking absolute imports."""
    if __package__ not in (None, ""):
        return
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_ensure_repo_root_on_path_for_direct_run()

from openai import OpenAI

from Backend.llm_provider import get_model_list
from Backend.search_provider import SearchProvider
from Backend.runtime import get_runtime
from Backend.runtime.contracts import AgentRequest
from Backend.settings import get_settings
from Prompt import welcome as welcome_assets


STREAM_SERVER_HOST = "0.0.0.0"
STREAM_SERVER_PORT = 8766
GLOBAL_DEBUG_ENV = "XIEXIN_DEBUG"

_STREAM_SERVER = None
_STREAM_SERVER_THREAD = None
_WELCOME_RELOAD_LOCK = threading.Lock()
_WELCOME_LAST_MTIME: float | None = None


def _is_welcome_hot_reload_enabled() -> bool:
    env_value = os.getenv("XIEXIN_WELCOME_HOT_RELOAD", "1").strip().lower()
    return env_value in {"1", "true", "yes", "on"}


def _maybe_reload_welcome_assets() -> bool:
    global _WELCOME_LAST_MTIME

    if not _is_welcome_hot_reload_enabled():
        return False

    module_file = Path(getattr(welcome_assets, "__file__", "") or "")
    if not module_file.exists():
        return False

    try:
        current_mtime = module_file.stat().st_mtime
    except OSError:
        return False

    with _WELCOME_RELOAD_LOCK:
        if _WELCOME_LAST_MTIME is None:
            _WELCOME_LAST_MTIME = current_mtime
            return False

        if current_mtime <= _WELCOME_LAST_MTIME:
            return False

        importlib.reload(welcome_assets)
        _WELCOME_LAST_MTIME = current_mtime
        return True


def _is_global_debug_enabled(debug_requested: bool = False) -> bool:
    if debug_requested:
        return True
    env_value = os.getenv(GLOBAL_DEBUG_ENV, "").strip().lower()
    return env_value in {"1", "true", "yes", "on"}


def _parse_debug_flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "on", "debug"}


def _is_debug_requested_from_query(parsed_url) -> bool:
    query = parse_qs(parsed_url.query, keep_blank_values=True)
    values = query.get("debug")
    if not values:
        return False
    return any(_parse_debug_flag(v) for v in values)


def _debug_print(stage: str, payload: dict) -> None:
    try:
        print(f"[DEBUG] {stage}: {json.dumps(payload, ensure_ascii=False)}")
    except Exception:
        print(f"[DEBUG] {stage}: {payload}")


def _build_frontend_config_payload(
    debug_requested: bool = False,
    *,
    session_id: str,
) -> dict:
    settings = get_settings()
    debug_enabled = _is_global_debug_enabled(debug_requested=debug_requested)
    reloaded = _maybe_reload_welcome_assets()
    hero_text, debug_payload = _generate_hero_welcome_text(
        debug_enabled=debug_enabled,
        session_id=session_id,
    )

    response_payload = {
        "availableModels": get_model_list(),
        "defaultModel": settings.model,
        "heroWelcomeText": hero_text,
        "welcomeSessionId": session_id,
        "requestOptions": {
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "max_tokens": settings.max_tokens,
        },
    }
    if debug_payload is not None:
        response_payload["debug"] = {
            "enabled": True,
            "welcome": debug_payload,
            "hotReload": {
                "enabled": _is_welcome_hot_reload_enabled(),
                "reloaded": reloaded,
            },
        }
        _debug_print("frontend-config", response_payload["debug"])
    return response_payload


def _generate_hero_welcome_text(
    wlcm_gen_prompt: str | None = None,
    *,
    debug_enabled: bool = False,
    session_id: str,
) -> tuple[str, dict | None]:
    settings = get_settings()
    default_welcome = welcome_assets.get_default_welcome()
    config = welcome_assets.get_welcome_generation_config(
        wlcm_gen_prompt=wlcm_gen_prompt,
        session_id=session_id,
    )
    system_prompt = str(config.get("system_prompt", "")).strip()
    first_token_timeout_seconds = float(config["first_token_timeout_seconds"])

    debug_payload = (
        {
            "enabled": True,
            "request": {
                "model": str(config["model"]),
                "temperature": float(config["temperature"]),
                "max_tokens": int(config["max_tokens"]),
                "timeout": first_token_timeout_seconds,
                "sessionId": session_id,
                "messages": [],
                "ab": config.get("ab", {}),
                "shortTermMemory": config.get("short_term_memory", []),
            },
            "response": {
                "rawText": "",
                "normalizedText": default_welcome,
                "chunks": [],
                "firstTokenLatencySeconds": None,
            },
            "error": None,
        }
        if debug_enabled
        else None
    )

    if not system_prompt or not settings.api_key:
        if debug_payload is not None:
            debug_payload["error"] = "missing prompt or api_key"
        return default_welcome, debug_payload

    try:
        client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
        deadline = time.monotonic() + first_token_timeout_seconds
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": welcome_assets.get_welcome_user_prompt()},
        ]
        if debug_payload is not None:
            debug_payload["request"]["messages"] = messages

        stream = client.chat.completions.create(
            model=str(config["model"]),
            messages=messages,
            temperature=float(config["temperature"]),
            max_tokens=int(config["max_tokens"]),
            stream=True,
            timeout=first_token_timeout_seconds,
        )

        parts: list[str] = []
        first_token_received = False
        first_token_latency: float | None = None
        started = time.monotonic()
        for chunk in stream:
            if not first_token_received and time.monotonic() > deadline:
                if debug_payload is not None:
                    debug_payload["error"] = "first token timeout"
                return default_welcome, debug_payload

            if not chunk.choices:
                continue

            delta_text = chunk.choices[0].delta.content or ""
            if delta_text:
                first_token_received = True
                if first_token_latency is None:
                    first_token_latency = round(time.monotonic() - started, 4)
                parts.append(delta_text)
                if debug_payload is not None:
                    debug_payload["response"]["chunks"].append(delta_text)

        raw_text = "".join(parts)
        normalized_text = welcome_assets.normalize_welcome_text(raw_text)
        if normalized_text and normalized_text != default_welcome:
            updated_memory = welcome_assets.record_welcome_word(
                session_id=session_id,
                text=normalized_text,
            )
            if debug_payload is not None:
                debug_payload["response"]["updatedShortTermMemory"] = updated_memory
        if debug_payload is not None:
            debug_payload["response"]["rawText"] = raw_text
            debug_payload["response"]["normalizedText"] = normalized_text
            debug_payload["response"]["firstTokenLatencySeconds"] = first_token_latency
        return normalized_text, debug_payload
    except Exception:
        if debug_payload is not None:
            debug_payload["error"] = "welcome generation failed"
        return default_welcome, debug_payload


def _normalize_bind_host(host: str) -> str:
    return (host or "").strip() or "127.0.0.1"


def _get_bound_server_address() -> tuple[str, int] | None:
    if _STREAM_SERVER is None:
        return None
    bound_host, bound_port = _STREAM_SERVER.server_address[:2]
    return str(bound_host), int(bound_port)


def _stop_stream_server() -> None:
    global _STREAM_SERVER, _STREAM_SERVER_THREAD

    if _STREAM_SERVER is not None:
        _STREAM_SERVER.shutdown()
        _STREAM_SERVER.server_close()

    if _STREAM_SERVER_THREAD is not None and _STREAM_SERVER_THREAD.is_alive():
        _STREAM_SERVER_THREAD.join(timeout=1.0)

    _STREAM_SERVER = None
    _STREAM_SERVER_THREAD = None


def _normalize_user_input(user_input: str) -> str:
    text = (user_input or "").strip()
    if not text:
        raise ValueError("user_input cannot be empty")
    return text if text.lower().startswith("user:") else f"user: {text}"


def ask_stream(
    user_input: str,
    model: Optional[str] = None,
    smooth: bool = True,
) -> Iterator[dict]:
    """Stream ask entrypoint for backend integration."""
    normalized_input = _normalize_user_input(user_input)
    runtime = get_runtime()
    yield from runtime.run_stream(
        request=AgentRequest(
            user_input=normalized_input,
            model=model,
            smooth=smooth,
        )
    )


def ask_with_metrics(
    user_input: str,
    model: Optional[str] = None,
) -> tuple[str, dict]:
    """Non-streaming ask entrypoint for fallback-style frontend calls."""
    normalized_input = _normalize_user_input(user_input)
    runtime = get_runtime()
    response = runtime.run_once(
        request=AgentRequest(
            user_input=normalized_input,
            model=model,
            smooth=True,
        )
    )
    return response.content, response.metrics


def _build_handler():
    class OrchestratorHandler(BaseHTTPRequestHandler):
        def _send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _read_json_payload(self) -> dict:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            return json.loads(raw_body.decode("utf-8") or "{}")

        def _start_json_response(self, status_code: int = 200) -> None:
            self.send_response(status_code)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

        def _write_json_response(self, payload: dict) -> None:
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            self.wfile.flush()

        def _start_stream_response(self, status_code: int = 200) -> None:
            self.send_response(status_code)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

        def _write_ndjson_event(self, payload: dict) -> None:
            line = json.dumps(payload, ensure_ascii=False) + "\n"
            self.wfile.write(line.encode("utf-8"))
            self.wfile.flush()

        def do_OPTIONS(self):
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/frontend-config":
                debug_requested = _is_debug_requested_from_query(parsed)
                query = parse_qs(parsed.query, keep_blank_values=True)
                requested_session_id = (query.get("session_id", [""])[0] or "").strip()
                session_id = (
                    welcome_assets.normalize_session_id(requested_session_id)
                    or welcome_assets.create_welcome_session_id()
                )
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                payload = _build_frontend_config_payload(
                    debug_requested=debug_requested,
                    session_id=session_id,
                )
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                return

            if path != "/health":
                self.send_response(404)
                self._send_cors_headers()
                self.end_headers()
                return

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/search/chat":
                try:
                    payload = self._read_json_payload()
                    result = SearchProvider.web_search(
                        messages=payload.get("messages", []),
                        user_input=payload.get("user_input"),
                        web_top_k=payload.get("web_top_k"),
                    )

                    self._start_json_response()
                    self._write_json_response(
                        {
                            "ok": True,
                            "provider": "baidu-qianfan-web-search",
                            "result": result,
                        }
                    )
                except Exception as exc:
                    self._start_json_response()
                    self._write_json_response(
                        {
                            "ok": False,
                            "code": "SEARCH_REQUEST_FAILED",
                            "message": str(exc),
                        }
                    )
                return

            if path == "/api/chat":
                try:
                    payload = self._read_json_payload()
                    user_input = payload.get("user_input", "")
                    model = payload.get("model")
                    debug_requested = _is_global_debug_enabled(
                        debug_requested=(
                            _is_debug_requested_from_query(parsed)
                            or _parse_debug_flag(payload.get("debug"))
                        )
                    )

                    if debug_requested:
                        debug_trace_events: list[dict] = []
                        content = ""
                        metrics = {}
                        debug_request = {
                            "path": path,
                            "model": model,
                            "smooth": True,
                            "user_input": user_input,
                        }
                        _debug_print("chat.request", debug_request)
                        for event in ask_stream(user_input=user_input, model=model, smooth=True):
                            debug_trace_events.append(event)
                            _debug_print("chat.event", event)
                            if event.get("type") == "done":
                                content = event.get("content", "")
                                metrics = event.get("metrics", {})
                    else:
                        content, metrics = ask_with_metrics(user_input=user_input, model=model)

                    self._start_json_response()
                    response_payload = {
                        "ok": True,
                        "content": content,
                        "metrics": metrics,
                    }
                    if debug_requested:
                        response_payload["debug"] = {
                            "enabled": True,
                            "request": debug_request,
                            "events": debug_trace_events,
                        }
                    self._write_json_response(response_payload)
                except Exception as exc:
                    self._start_json_response()
                    self._write_json_response(
                        {
                            "ok": False,
                            "code": "CHAT_REQUEST_FAILED",
                            "message": str(exc),
                        }
                    )
                return

            if path != "/api/chat/stream":
                self.send_response(404)
                self._send_cors_headers()
                self.end_headers()
                return

            response_started = False
            debug_requested = False

            try:
                payload = self._read_json_payload()
                user_input = payload.get("user_input", "")
                model = payload.get("model")
                smooth = payload.get("smooth", True)
                debug_requested = _is_global_debug_enabled(
                    debug_requested=(
                        _is_debug_requested_from_query(parsed)
                        or _parse_debug_flag(payload.get("debug"))
                    )
                )

                self._start_stream_response()
                response_started = True

                if debug_requested:
                    debug_request = {
                        "path": path,
                        "model": model,
                        "smooth": smooth,
                        "user_input": user_input,
                    }
                    _debug_print("stream.request", debug_request)
                    self._write_ndjson_event(
                        {
                            "type": "debug",
                            "stage": "request",
                            "payload": debug_request,
                        }
                    )

                for event in ask_stream(user_input=user_input, model=model, smooth=smooth):
                    if debug_requested:
                        _debug_print("stream.event", event)
                    self._write_ndjson_event(event)
            except Exception as exc:
                if not response_started:
                    self._start_stream_response()
                if debug_requested:
                    _debug_print("stream.error", {"message": str(exc)})
                self._write_ndjson_event(
                    {
                        "type": "error",
                        "code": "STREAM_REQUEST_FAILED",
                        "message": str(exc),
                    }
                )

        def log_message(self, format, *args):
            return

    return OrchestratorHandler


def ensure_stream_server_running(
    host: str = STREAM_SERVER_HOST,
    port: int = STREAM_SERVER_PORT,
) -> tuple[str, int]:
    global _STREAM_SERVER, _STREAM_SERVER_THREAD
    requested_host = _normalize_bind_host(host)
    requested_port = int(port)

    if _STREAM_SERVER is not None and _STREAM_SERVER_THREAD is not None and _STREAM_SERVER_THREAD.is_alive():
        bound_address = _get_bound_server_address()
        if bound_address == (requested_host, requested_port):
            return bound_address
        _stop_stream_server()

    handler = _build_handler()
    _STREAM_SERVER = ThreadingHTTPServer((requested_host, requested_port), handler)
    _STREAM_SERVER_THREAD = threading.Thread(
        target=_STREAM_SERVER.serve_forever,
        name="orchestrator-stream-server",
        daemon=True,
    )
    _STREAM_SERVER_THREAD.start()
    return _get_bound_server_address() or (requested_host, requested_port)


def run_stream_server_forever(
    host: str = STREAM_SERVER_HOST,
    port: int = STREAM_SERVER_PORT,
) -> tuple[str, int]:
    requested_host = _normalize_bind_host(host)
    requested_port = int(port)
    handler = _build_handler()
    server = ThreadingHTTPServer((requested_host, requested_port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return requested_host, requested_port


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the xiexin orchestrator server or a smoke stream.")
    parser.add_argument("--serve", action="store_true", help="Start the HTTP server and block.")
    parser.add_argument("--host", default=STREAM_SERVER_HOST)
    parser.add_argument("--port", type=int, default=STREAM_SERVER_PORT)
    parser.add_argument("sample", nargs="?", default="你好，做个自我介绍")
    args = parser.parse_args()

    if args.serve:
        print(f"serving orchestrator on http://{args.host}:{args.port}")
        run_stream_server_forever(host=args.host, port=args.port)
    else:
        for event in ask_stream(args.sample):
            print(event)


if __name__ == "__main__":
    main()
