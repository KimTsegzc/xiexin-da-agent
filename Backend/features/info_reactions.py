from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .conversation_context import normalize_session_id


REPO_ROOT = Path(__file__).resolve().parents[2]
_MEMORY_ROOT = REPO_ROOT / "Memory"
_APP_SPACE_ROOT = _MEMORY_ROOT / "app_space" / "info_reactions"
_LIKES_DIR = _APP_SPACE_ROOT / "likes"
_COMMENTS_DIR = _APP_SPACE_ROOT / "comments"
_REACTIONS_LOCK = threading.Lock()
_INFO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_COMMENT_MAX_LENGTH = 600


def normalize_info_id(info_id: str | None) -> str | None:
    candidate = (info_id or "").strip()
    if not candidate:
        return None
    if not _INFO_ID_PATTERN.fullmatch(candidate):
        return None
    return candidate


def normalize_comment_content(content: str | None) -> str:
    text = " ".join((content or "").split())
    if not text:
        raise ValueError("comment content cannot be empty")
    if len(text) > _COMMENT_MAX_LENGTH:
        raise ValueError(f"comment content too long (max {_COMMENT_MAX_LENGTH})")
    return text


def _ensure_layout() -> None:
    _LIKES_DIR.mkdir(parents=True, exist_ok=True)
    _COMMENTS_DIR.mkdir(parents=True, exist_ok=True)


def _likes_file(info_id: str) -> Path:
    return _LIKES_DIR / f"{info_id}.jsonl"


def _comments_file(info_id: str) -> Path:
    return _COMMENTS_DIR / f"{info_id}.jsonl"


def _read_jsonl(target: Path) -> list[dict[str, Any]]:
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for raw in target.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                rows.append(parsed)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return []
    return rows


def _atomic_write_jsonl(target: Path, rows: list[dict[str, Any]]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(item, ensure_ascii=False) for item in rows)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(target.parent),
        delete=False,
    ) as tmp:
        tmp.write(payload)
        tmp_path = tmp.name

    try:
        os.replace(tmp_path, target)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _normalize_user_name(value: str | None) -> str:
    text = " ".join((value or "").split())
    if not text:
        return "匿名"
    if len(text) > 32:
        return text[:32]
    return text


def _validate_session_or_raise(session_id: str | None) -> str:
    normalized = normalize_session_id(session_id)
    if not normalized:
        raise ValueError("invalid session_id")
    return normalized


def add_like(*, info_id: str, session_id: str) -> dict[str, Any]:
    safe_info_id = normalize_info_id(info_id)
    if not safe_info_id:
        raise ValueError("invalid info_id")
    safe_session_id = _validate_session_or_raise(session_id)

    with _REACTIONS_LOCK:
        _ensure_layout()
        rows = _read_jsonl(_likes_file(safe_info_id))
        if not any(item.get("session_id") == safe_session_id for item in rows):
            rows.append(
                {
                    "session_id": safe_session_id,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            _atomic_write_jsonl(_likes_file(safe_info_id), rows)

        return {
            "info_id": safe_info_id,
            "like_count": len(rows),
            "user_has_liked": True,
        }


def remove_like(*, info_id: str, session_id: str) -> dict[str, Any]:
    safe_info_id = normalize_info_id(info_id)
    if not safe_info_id:
        raise ValueError("invalid info_id")
    safe_session_id = _validate_session_or_raise(session_id)

    with _REACTIONS_LOCK:
        _ensure_layout()
        rows = _read_jsonl(_likes_file(safe_info_id))
        next_rows = [item for item in rows if item.get("session_id") != safe_session_id]
        if len(next_rows) != len(rows):
            _atomic_write_jsonl(_likes_file(safe_info_id), next_rows)

        return {
            "info_id": safe_info_id,
            "like_count": len(next_rows),
            "user_has_liked": False,
        }


def add_comment(
    *,
    info_id: str,
    session_id: str,
    content: str,
    user_name: str | None = None,
) -> dict[str, Any]:
    safe_info_id = normalize_info_id(info_id)
    if not safe_info_id:
        raise ValueError("invalid info_id")
    safe_session_id = _validate_session_or_raise(session_id)
    safe_content = normalize_comment_content(content)

    comment = {
        "id": f"cmt-{uuid4().hex[:12]}",
        "session_id": safe_session_id,
        "user_name": _normalize_user_name(user_name),
        "content": safe_content,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    with _REACTIONS_LOCK:
        _ensure_layout()
        rows = _read_jsonl(_comments_file(safe_info_id))
        rows.append(comment)
        _atomic_write_jsonl(_comments_file(safe_info_id), rows)

    return {
        "info_id": safe_info_id,
        "comment": comment,
    }


def get_reactions(*, info_id: str, session_id: str | None = None) -> dict[str, Any]:
    safe_info_id = normalize_info_id(info_id)
    if not safe_info_id:
        raise ValueError("invalid info_id")
    normalized_session = normalize_session_id(session_id)

    with _REACTIONS_LOCK:
        _ensure_layout()
        likes = _read_jsonl(_likes_file(safe_info_id))
        comments = _read_jsonl(_comments_file(safe_info_id))

    comments_sorted = sorted(
        (
            {
                "id": str(item.get("id", "")).strip(),
                "session_id": str(item.get("session_id", "")).strip(),
                "user_name": str(item.get("user_name", "匿名")).strip() or "匿名",
                "content": str(item.get("content", "")).strip(),
                "created_at": str(item.get("created_at", "")).strip(),
            }
            for item in comments
            if str(item.get("content", "")).strip()
        ),
        key=lambda item: item.get("created_at", ""),
    )

    like_sessions = {
        str(item.get("session_id", "")).strip()
        for item in likes
        if str(item.get("session_id", "")).strip()
    }

    return {
        "info_id": safe_info_id,
        "like_count": len(like_sessions),
        "user_has_liked": bool(normalized_session and normalized_session in like_sessions),
        "comments": comments_sorted,
    }