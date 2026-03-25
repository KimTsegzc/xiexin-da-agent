from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterator, Optional
from urllib.parse import urlparse

from Gateway.Back import LLMProvider


STREAM_SERVER_HOST = "127.0.0.1"
STREAM_SERVER_PORT = 8765

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


def _build_handler():
	class ControllerHandler(BaseHTTPRequestHandler):
		def _send_cors_headers(self) -> None:
			self.send_header("Access-Control-Allow-Origin", "*")
			self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
			self.send_header("Access-Control-Allow-Headers", "Content-Type")

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
			if path != "/api/chat/stream":
				self.send_response(404)
				self._send_cors_headers()
				self.end_headers()
				return

			content_length = int(self.headers.get("Content-Length", "0"))
			raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

			try:
				payload = json.loads(raw_body.decode("utf-8") or "{}")
				user_input = payload.get("user_input", "")
				model = payload.get("model")
				smooth = payload.get("smooth", True)

				self.send_response(200)
				self._send_cors_headers()
				self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
				self.send_header("Cache-Control", "no-cache")
				self.send_header("X-Accel-Buffering", "no")
				self.end_headers()

				for event in ask_stream(user_input=user_input, model=model, smooth=smooth):
					self._write_ndjson_event(event)
			except Exception as exc:
				self.send_response(200)
				self._send_cors_headers()
				self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
				self.end_headers()
				self._write_ndjson_event(
					{
						"type": "error",
						"code": "STREAM_REQUEST_FAILED",
						"message": str(exc),
					}
				)

		def log_message(self, format, *args):
			return

	return ControllerHandler


def ensure_stream_server_running(
	host: str = STREAM_SERVER_HOST,
	port: int = STREAM_SERVER_PORT,
) -> tuple[str, int]:
	global _STREAM_SERVER, _STREAM_SERVER_THREAD

	if _STREAM_SERVER is not None and _STREAM_SERVER_THREAD is not None and _STREAM_SERVER_THREAD.is_alive():
		return host, port

	handler = _build_handler()
	_STREAM_SERVER = ThreadingHTTPServer((host, port), handler)
	_STREAM_SERVER_THREAD = threading.Thread(
		target=_STREAM_SERVER.serve_forever,
		name="controller-stream-server",
		daemon=True,
	)
	_STREAM_SERVER_THREAD.start()
	return host, port


if __name__ == "__main__":
	# Minimal smoke run for controller-level stream integration.
	sample = "你好，做个自我介绍"
	for event in ask_stream(sample):
		print(event)
