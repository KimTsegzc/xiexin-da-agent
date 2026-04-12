from __future__ import annotations

import base64
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
_MEMORY_ROOT = REPO_ROOT / "Memory"
_SHARED_SPACE_ROOT = _MEMORY_ROOT / "shared_space"
_UPLOADS_ROOT = _SHARED_SPACE_ROOT / "uploads"
_MAX_INLINE_IMAGE_BYTES = 6 * 1024 * 1024
_MAX_TEXT_CHARS = 12000
_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".jsonl",
    ".csv",
    ".tsv",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".xml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".toml",
    ".log",
    ".sql",
}


def _ensure_upload_layout() -> None:
    _SHARED_SPACE_ROOT.mkdir(parents=True, exist_ok=True)
    _UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)


def _sanitize_filename(filename: str | None) -> str:
    original = Path(str(filename or "upload")).name.strip() or "upload"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", original).strip("._")
    if not cleaned:
        cleaned = "upload"
    return cleaned[:120]


def _detect_media_type(content_type: str | None, target_path: Path) -> str:
    mime = str(content_type or "").strip().lower()
    if mime.startswith("image/"):
        return "image"
    if target_path.suffix.lower() in _TEXT_EXTENSIONS:
        return "text"
    if mime.startswith("text/") or mime in {"application/json", "application/xml"}:
        return "text"
    return "binary"


def store_uploaded_file(*, filename: str, content: bytes, content_type: str | None, session_id: str | None) -> dict[str, Any]:
    _ensure_upload_layout()
    safe_name = _sanitize_filename(filename)
    day_segment = datetime.now().strftime("%Y%m%d")
    session_segment = str(session_id or "shared").strip() or "shared"
    attachment_id = uuid4().hex[:12]
    target_dir = _UPLOADS_ROOT / session_segment / day_segment
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{attachment_id}_{safe_name}"
    target_path.write_bytes(content)

    resolved_content_type = str(content_type or mimetypes.guess_type(target_path.name)[0] or "application/octet-stream")
    media_type = _detect_media_type(resolved_content_type, target_path)
    return {
        "id": attachment_id,
        "name": safe_name,
        "original_name": Path(str(filename or safe_name)).name,
        "relative_path": target_path.relative_to(REPO_ROOT).as_posix(),
        "content_type": resolved_content_type,
        "size_bytes": len(content),
        "media_type": media_type,
        "storage_scope": "shared_space",
    }


def resolve_attachment_path(attachment: dict[str, Any]) -> Path | None:
    relative_path = str(attachment.get("relative_path") or "").strip()
    if not relative_path:
        return None
    candidate = (REPO_ROOT / relative_path).resolve()
    allowed_root = _SHARED_SPACE_ROOT.resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError:
        return None
    return candidate if candidate.exists() else None


def extract_attachment_text(attachment: dict[str, Any], max_chars: int = _MAX_TEXT_CHARS) -> tuple[str, bool]:
    target_path = resolve_attachment_path(attachment)
    if target_path is None:
        return "", False
    try:
        raw_text = target_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            raw_text = target_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            return "", False
    except OSError:
        return "", False
    text = raw_text.strip()
    if not text:
        return "", False
    truncated = len(text) > max_chars
    return text[:max_chars], truncated


def build_attachment_image_data_url(attachment: dict[str, Any]) -> str | None:
    target_path = resolve_attachment_path(attachment)
    if target_path is None:
        return None
    try:
        raw = target_path.read_bytes()
    except OSError:
        return None
    if not raw or len(raw) > _MAX_INLINE_IMAGE_BYTES:
        return None
    mime = str(attachment.get("content_type") or mimetypes.guess_type(target_path.name)[0] or "image/png")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"