from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterator, Optional
from urllib.parse import urlparse

from Gateway.Back import LLMProvider
from Gateway.Back.llm_provider import get_model_list
from Gateway.Back.settings import get_settings


STREAM_SERVER_HOST = "0.0.0.0"
STREAM_SERVER_PORT = 8766

_STREAM_SERVER = None
_STREAM_SERVER_THREAD = None


def _build_frontend_config_payload() -> dict:
	settings = get_settings()
	return {
		"availableModels": get_model_list(),
		"defaultModel": settings.model,
		"requestOptions": {
			"temperature": settings.temperature,
			"top_p": settings.top_p,
			"max_tokens": settings.max_tokens,
		},
	}


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
	yield from LLMProvider.stream(
		user_input=normalized_input,
		model=model,
		smooth=smooth,
	)


def ask_with_metrics(
	user_input: str,
	model: Optional[str] = None,
) -> tuple[str, dict]:
	"""Non-streaming ask entrypoint for fallback-style frontend calls."""
	normalized_input = _normalize_user_input(user_input)
	return LLMProvider.with_metrics(
		user_input=normalized_input,
		model=model,
	)


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
			path = urlparse(self.path).path
			if path == "/api/frontend-config":
				self.send_response(200)
				self._send_cors_headers()
				self.send_header("Content-Type", "application/json; charset=utf-8")
				self.end_headers()
				self.wfile.write(json.dumps(_build_frontend_config_payload(), ensure_ascii=False).encode("utf-8"))
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
			path = urlparse(self.path).path
			if path == "/api/chat":
				try:
					payload = self._read_json_payload()
					user_input = payload.get("user_input", "")
					model = payload.get("model")
					content, metrics = ask_with_metrics(user_input=user_input, model=model)

					self._start_json_response()
					self._write_json_response(
						{
							"ok": True,
							"content": content,
							"metrics": metrics,
						}
					)
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

			try:
				payload = self._read_json_payload()
				user_input = payload.get("user_input", "")
				model = payload.get("model")
				smooth = payload.get("smooth", True)

				self._start_stream_response()
				response_started = True

				for event in ask_stream(user_input=user_input, model=model, smooth=smooth):
					self._write_ndjson_event(event)
			except Exception as exc:
				if not response_started:
					self._start_stream_response()
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


if __name__ == "__main__":
	import argparse

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
