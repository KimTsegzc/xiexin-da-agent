from __future__ import annotations

import argparse
import json
import random
import re
import threading
import time
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_WELCOME = "你好，我是鑫哥~"

_MEMORY_ROOT = REPO_ROOT / "Memory"
_APP_SPACE_DIR = _MEMORY_ROOT / "app_space"
_USER_SPECIFIC_DIR = _MEMORY_ROOT / "user_specific"
_SHARED_SPACE_DIR = _MEMORY_ROOT / "shared_space"
_USER_WELCOME_CACHE_DIR = _USER_SPECIFIC_DIR / "welcome_cache"
_SAYINGS_FILE = _APP_SPACE_DIR / "xiexin_sayings.json"
_WELCOME_HISTORY_MAX_ITEMS = 10
_MEMORY_LOCK = threading.Lock()
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _ensure_memory_layout() -> None:
    _APP_SPACE_DIR.mkdir(parents=True, exist_ok=True)
    _USER_SPECIFIC_DIR.mkdir(parents=True, exist_ok=True)
    _USER_WELCOME_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _SHARED_SPACE_DIR.mkdir(parents=True, exist_ok=True)


def normalize_session_id(session_id: str | None) -> str | None:
    candidate = (session_id or "").strip()
    if not candidate:
        return None
    if not _SESSION_ID_PATTERN.fullmatch(candidate):
        return None
    return candidate


def create_welcome_session_id() -> str:
    return uuid.uuid4().hex


def _session_welcome_file(session_id: str) -> Path:
    return _USER_WELCOME_CACHE_DIR / f"{session_id}.jsonl"


def _normalize_welcome_text(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return _DEFAULT_WELCOME
    return cleaned[:42]


def normalize_welcome_text(text: str) -> str:
    return _normalize_welcome_text(text)


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    deduped: list[str] = []
    for item in items:
        normalized = _normalize_welcome_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _read_sayings() -> list[str]:
    if not _SAYINGS_FILE.exists():
        return []
    try:
        payload = json.loads(_SAYINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    sayings = payload.get("sayings") if isinstance(payload, dict) else None
    if not isinstance(sayings, list):
        return []
    return _dedupe_keep_order([str(item) for item in sayings])


def _read_user_specific_welcome_memory(
    session_id: str,
    limit: int = _WELCOME_HISTORY_MAX_ITEMS,
) -> list[str]:
    _ensure_memory_layout()
    target_file = _session_welcome_file(session_id)
    target_file.touch(exist_ok=True)
    items: list[str] = []
    try:
        for raw_line in target_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                text = str(parsed.get("text", "")).strip()
            except Exception:
                text = line
            if text:
                items.append(text)
    except OSError:
        return []
    deduped = _dedupe_keep_order(items)
    return deduped[-max(1, int(limit)) :]


def get_user_specific_welcome_memory(
    session_id: str,
    limit: int = _WELCOME_HISTORY_MAX_ITEMS,
) -> list[str]:
    return _read_user_specific_welcome_memory(session_id=session_id, limit=limit)


def record_welcome_word(session_id: str, text: str) -> list[str]:
    normalized = _normalize_welcome_text(text)
    if not normalized:
        return _read_user_specific_welcome_memory(session_id=session_id, limit=_WELCOME_HISTORY_MAX_ITEMS)

    with _MEMORY_LOCK:
        items = _read_user_specific_welcome_memory(session_id=session_id, limit=_WELCOME_HISTORY_MAX_ITEMS)
        items = [item for item in items if item != normalized]
        items.append(normalized)
        items = items[-_WELCOME_HISTORY_MAX_ITEMS:]

        _ensure_memory_layout()
        target_file = _session_welcome_file(session_id)
        payload_lines = [
            json.dumps({"text": item, "ts": int(time.time())}, ensure_ascii=False)
            for item in items
        ]
        target_file.write_text("\n".join(payload_lines), encoding="utf-8")
        return items


def get_default_welcome() -> str:
    return _DEFAULT_WELCOME


def pick_welcome_text(
    *,
    session_id: str,
    fallback_text: str | None = None,
) -> tuple[str, dict]:
    fallback_welcome = _normalize_welcome_text(fallback_text or _DEFAULT_WELCOME)
    sayings = _read_sayings()
    recent_items = get_user_specific_welcome_memory(session_id=session_id, limit=_WELCOME_HISTORY_MAX_ITEMS)
    candidates = [item for item in sayings if item not in recent_items]

    selected = fallback_welcome
    if candidates:
        selected = random.choice(candidates)
    elif sayings:
        selected = random.choice(sayings)

    updated_memory = record_welcome_word(session_id=session_id, text=selected)
    return selected, {
        "source": "xiexin_sayings.json",
        "normalizedText": selected,
        "recentWindowSize": _WELCOME_HISTORY_MAX_ITEMS,
        "recentHistory": recent_items,
        "candidateCount": len(candidates),
        "totalSayings": len(sayings),
        "updatedUserSpecificMemory": updated_memory,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug local welcome selection.")
    parser.add_argument(
        "--session-id",
        default=None,
        help="Optional welcome session id for isolated user-specific memory.",
    )
    parser.add_argument(
        "--fallback",
        default=None,
        help="Optional fallback text if sayings file is empty.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    resolved_session_id = normalize_session_id(args.session_id) or create_welcome_session_id()
    selected, debug_payload = pick_welcome_text(
        session_id=resolved_session_id,
        fallback_text=args.fallback,
    )
    print(f"[welcome-debug] session_id={resolved_session_id}")
    print("[welcome-debug] selection:")
    print(selected)
    print("[welcome-debug] payload:")
    print(json.dumps(debug_payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
