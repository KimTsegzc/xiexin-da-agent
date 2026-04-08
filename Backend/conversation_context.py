from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from .settings import Settings, get_settings, load_summary_prompt, load_system_prompt


REPO_ROOT = Path(__file__).resolve().parents[1]
_MEMORY_ROOT = REPO_ROOT / "Memory" / "short_term" / "chat_context"
_HISTORY_DIR = _MEMORY_ROOT / "history"
_SUMMARY_DIR = _MEMORY_ROOT / "summaries"
_MEMORY_LOCK = threading.Lock()
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _preview_text(text: str, limit: int = 160) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)] + "..."


def _log_context(stage: str, payload: dict[str, Any]) -> None:
    print(
        f"[context] {stage}: {json.dumps(payload, ensure_ascii=False)}",
        flush=True,
    )


@dataclass(slots=True)
class SummaryState:
    text: str = ""
    source_message_count: int = 0
    updated_at: str | None = None
    model: str | None = None


@dataclass(slots=True)
class PreparedConversation:
    session_id: str | None
    request_started_at: datetime
    request_time_text: str
    time_period_label: str
    summary: SummaryState = field(default_factory=SummaryState)
    recent_messages: list[dict[str, str]] = field(default_factory=list)
    messages: list[dict[str, str]] = field(default_factory=list)

    def metrics(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "request_time": self.request_time_text,
            "time_period": self.time_period_label,
            "recent_message_count": len(self.recent_messages),
            "summary_applied": bool(self.summary.text),
            "summary_source_message_count": self.summary.source_message_count,
        }


def normalize_session_id(session_id: str | None) -> str | None:
    candidate = (session_id or "").strip()
    if not candidate:
        return None
    if not _SESSION_ID_PATTERN.fullmatch(candidate):
        return None
    return candidate


def _ensure_memory_layout() -> None:
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    _SUMMARY_DIR.mkdir(parents=True, exist_ok=True)


def _history_file(session_id: str) -> Path:
    return _HISTORY_DIR / f"{session_id}.jsonl"


def _summary_file(session_id: str) -> Path:
    return _SUMMARY_DIR / f"{session_id}.json"


def _format_request_time(request_started_at: datetime) -> tuple[str, str]:
    hour = request_started_at.hour
    if 0 <= hour < 6:
        period = "凌晨"
    elif 6 <= hour < 9:
        period = "早上"
    elif 9 <= hour < 12:
        period = "上午"
    elif 12 <= hour < 14:
        period = "中午"
    elif 14 <= hour < 18:
        period = "下午"
    else:
        period = "晚上"
    return request_started_at.strftime("%Y年%m月%d日 %H:%M"), period


def _load_history(session_id: str) -> list[dict[str, str]]:
    _ensure_memory_layout()
    target_file = _history_file(session_id)
    if not target_file.exists():
        return []
    messages: list[dict[str, str]] = []
    try:
        for raw_line in target_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parsed = json.loads(line)
            role = str(parsed.get("role", "")).strip()
            content = str(parsed.get("content", "")).strip()
            if role and content:
                messages.append({"role": role, "content": content})
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return []
    return messages


def _load_summary(session_id: str) -> SummaryState:
    _ensure_memory_layout()
    target_file = _summary_file(session_id)
    if not target_file.exists():
        return SummaryState()
    try:
        payload = json.loads(target_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return SummaryState()
    if not isinstance(payload, dict):
        return SummaryState()
    return SummaryState(
        text=str(payload.get("summary", "")).strip(),
        source_message_count=int(payload.get("source_message_count", 0) or 0),
        updated_at=str(payload.get("updated_at", "")).strip() or None,
        model=str(payload.get("model", "")).strip() or None,
    )


def _build_system_message(request_time_text: str, time_period_label: str) -> str:
    return (
        f"当前系统时间：{request_time_text}\n"
        f"当前时段：{time_period_label}\n"
        "如果对方是在打招呼、寒暄，必须使用和当前时段一致的中文问候，不要把晚上说成早上。\n\n"
        f"{load_system_prompt()}"
    ).strip()


def prepare_conversation(
    *,
    user_input: str,
    session_id: str | None,
    request_started_at: datetime | None,
    settings: Settings | None = None,
) -> PreparedConversation:
    resolved_settings = settings or get_settings()
    resolved_session_id = normalize_session_id(session_id)
    resolved_request_time = request_started_at or datetime.now()
    request_time_text, time_period_label = _format_request_time(resolved_request_time)
    summary = SummaryState()
    recent_messages: list[dict[str, str]] = []

    if resolved_session_id:
        summary = _load_summary(resolved_session_id)
        history = _load_history(resolved_session_id)
        recent_limit = max(0, int(resolved_settings.context_recent_messages))
        recent_messages = history[-recent_limit:] if recent_limit else []

    messages = [{"role": "system", "content": _build_system_message(request_time_text, time_period_label)}]
    if summary.text:
        messages.append(
            {
                "role": "system",
                "content": (
                    "以下是当前会话的滚动摘要，供你延续上下文使用；如果与最新消息冲突，以最新消息为准。\n\n"
                    f"{summary.text[: max(1, int(resolved_settings.context_summary_max_chars))]}"
                ),
            }
        )
    messages.extend(recent_messages)
    messages.append({"role": "user", "content": user_input})
    _log_context(
        "prepared",
        {
            "session_id": resolved_session_id,
            "request_time": request_time_text,
            "time_period": time_period_label,
            "recent_message_count": len(recent_messages),
            "summary_applied": bool(summary.text),
            "summary_preview": _preview_text(summary.text),
            "latest_user_preview": _preview_text(user_input),
        },
    )
    return PreparedConversation(
        session_id=resolved_session_id,
        request_started_at=resolved_request_time,
        request_time_text=request_time_text,
        time_period_label=time_period_label,
        summary=summary,
        recent_messages=recent_messages,
        messages=messages,
    )


def _write_history(session_id: str, messages: list[dict[str, str]], request_started_at: datetime) -> None:
    existing = _load_history(session_id)
    existing.extend(messages)
    payload_lines = [
        json.dumps(
            {
                "role": item["role"],
                "content": item["content"],
                "ts": request_started_at.isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
        )
        for item in existing
    ]
    _history_file(session_id).write_text("\n".join(payload_lines), encoding="utf-8")


def _build_summary_input(
    *,
    previous_summary: str,
    new_messages: list[dict[str, str]],
    request_time_text: str,
    time_period_label: str,
) -> str:
    rendered_messages = "\n".join(f"- {item['role']}: {item['content']}" for item in new_messages)
    return (
        f"当前请求时间：{request_time_text}（{time_period_label}）\n\n"
        "[已有滚动摘要]\n"
        f"{previous_summary or '暂无'}\n\n"
        "[本次需要增量合并的新消息]\n"
        f"{rendered_messages}\n"
    )


def _generate_summary(
    *,
    settings: Settings,
    previous_summary: SummaryState,
    new_messages: list[dict[str, str]],
    request_time_text: str,
    time_period_label: str,
) -> str:
    client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
    completion = client.chat.completions.create(
        model=settings.summary_model,
        messages=[
            {"role": "system", "content": load_summary_prompt()},
            {
                "role": "user",
                "content": _build_summary_input(
                    previous_summary=previous_summary.text,
                    new_messages=new_messages,
                    request_time_text=request_time_text,
                    time_period_label=time_period_label,
                ),
            },
        ],
        temperature=settings.summary_temperature,
        max_tokens=settings.summary_max_tokens,
        extra_body={"enable_search": False},
    )
    content = completion.choices[0].message.content if completion.choices else ""
    return str(content or "").strip()


def finalize_conversation(
    *,
    prepared: PreparedConversation,
    user_input: str,
    assistant_output: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or get_settings()
    if not prepared.session_id:
        _log_context(
            "finalized",
            {
                "session_id": None,
                "persisted": False,
                "summary_updated": False,
                "reason": "missing_session_id",
            },
        )
        return {"persisted": False, "summary_updated": False, "reason": "missing_session_id"}

    normalized_assistant = (assistant_output or "").strip()
    if not normalized_assistant:
        _log_context(
            "finalized",
            {
                "session_id": prepared.session_id,
                "persisted": False,
                "summary_updated": False,
                "reason": "empty_assistant_output",
            },
        )
        return {"persisted": False, "summary_updated": False, "reason": "empty_assistant_output"}

    new_messages = [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": normalized_assistant},
    ]
    history: list[dict[str, str]] = []
    summary_error = None
    summary_updated = False

    with _MEMORY_LOCK:
        _ensure_memory_layout()
        _write_history(prepared.session_id, new_messages, prepared.request_started_at)
        history = _load_history(prepared.session_id)
        threshold = max(1, int(resolved_settings.summary_trigger_messages))
        should_refresh_summary = (
            bool(resolved_settings.summary_enabled)
            and bool(resolved_settings.api_key)
            and len(history) >= prepared.summary.source_message_count + threshold
        )
        if should_refresh_summary:
            try:
                merged_summary = _generate_summary(
                    settings=resolved_settings,
                    previous_summary=prepared.summary,
                    new_messages=history[prepared.summary.source_message_count :],
                    request_time_text=prepared.request_time_text,
                    time_period_label=prepared.time_period_label,
                )
                _summary_file(prepared.session_id).write_text(
                    json.dumps(
                        {
                            "summary": merged_summary,
                            "source_message_count": len(history),
                            "updated_at": datetime.now().isoformat(timespec="seconds"),
                            "model": resolved_settings.summary_model,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                summary_updated = True
            except Exception as exc:
                summary_error = str(exc)

    result = {
        "persisted": True,
        "summary_updated": summary_updated,
        "summary_model": resolved_settings.summary_model if summary_updated else None,
        "history_message_count": len(history),
        "summary_error": summary_error,
    }
    _log_context(
        "finalized",
        {
            "session_id": prepared.session_id,
            "persisted": result["persisted"],
            "summary_updated": result["summary_updated"],
            "summary_model": result["summary_model"],
            "history_message_count": result["history_message_count"],
            "summary_error": result["summary_error"],
            "assistant_preview": _preview_text(normalized_assistant),
        },
    )
    return result