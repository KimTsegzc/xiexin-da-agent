from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ....features.conversation_context import REPO_ROOT, normalize_session_id


_PENDING_ROOT = REPO_ROOT / "Memory" / "user_specific" / "chat_context" / "pending_email_confirmation"


def _ensure_pending_root() -> None:
    _PENDING_ROOT.mkdir(parents=True, exist_ok=True)


def _pending_file(session_id: str) -> Path:
    return _PENDING_ROOT / f"{session_id}.json"


def load_pending_email_confirmation(session_id: str | None) -> dict[str, Any] | None:
    normalized_session_id = normalize_session_id(session_id)
    if not normalized_session_id:
        return None

    _ensure_pending_root()
    target = _pending_file(normalized_session_id)
    if not target.exists():
        return None

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def save_pending_email_confirmation(session_id: str | None, payload: dict[str, Any]) -> bool:
    normalized_session_id = normalize_session_id(session_id)
    if not normalized_session_id:
        return False

    _ensure_pending_root()
    try:
        _pending_file(normalized_session_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        return False
    return True


def clear_pending_email_confirmation(session_id: str | None) -> bool:
    normalized_session_id = normalize_session_id(session_id)
    if not normalized_session_id:
        return False

    _ensure_pending_root()
    target = _pending_file(normalized_session_id)
    if not target.exists():
        return True
    try:
        target.unlink()
    except OSError:
        return False
    return True


def has_pending_email_confirmation(session_id: str | None) -> bool:
    return load_pending_email_confirmation(session_id) is not None