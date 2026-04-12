from __future__ import annotations

import json
import re
from typing import Any, Iterator

from .... import LLMProvider
from ....features.conversation_context import PreparedConversation, finalize_conversation, prepare_conversation
from ....settings import get_settings
from ...contracts import AgentRequest, AgentResponse
from ..base import BaseSkill
from .data import CCBHandlerTable, CCBHandlerTableTool, HandlerRecord
from .prompts import build_lookup_system_prompt, build_lookup_user_prompt


_LEADERSHIP_ROLE_KEYWORDS = ("总经理", "副总经理", "主任", "副主任")


def _extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = (text or "").strip()
    if not stripped:
        return None

    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            payload = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None

    return payload if isinstance(payload, dict) else None


def _build_opening_phrase(record: HandlerRecord, match_reason: str | None) -> str:
    normalized_reason = re.sub(r"\s+", " ", (match_reason or "").strip()).rstrip("。；，")
    if normalized_reason:
        return f"我看了下职能表，按职责描述这事更贴近{record.department}的{record.role_display}，我的判断是：{normalized_reason}"
    return f"我的通讯录不全，这事更像是{record.department}的{record.role_display}在负责，我找人再确认一下~"


def _is_leadership_record(record: HandlerRecord) -> bool:
    role = (record.role or "").strip()
    return any(keyword in role for keyword in _LEADERSHIP_ROLE_KEYWORDS)


def _render_not_found_response() -> str:
    return "\n".join(
        [
            "不好意思，我的通讯录暂时没有收录，我找人问问再告诉你~",
        ]
    )


def _format_record_response(
    table: CCBHandlerTable,
    record: HandlerRecord,
    match_reason: str | None = None,
) -> str:
    chain = table.resolve_chain(record)
    lines: list[str] = []
    if _is_leadership_record(record):
        lines.append("这个事比较综合，可能要找部门领导协调才行。")
    lines.extend(
        [
            _build_opening_phrase(record, match_reason),
            f"职能部门：{record.department}",
            f"岗位：{record.role_display}",
            f"负责人链条：{chain.render()}",
            f"工作职责：{record.role_display}，{record.responsibilities_excerpt()}",
            f"联系方式：{record.office_phone or '未提供'}",
        ]
    )
    return "\n".join(lines)


def _build_lookup_messages(
    request: AgentRequest,
    tool: CCBHandlerTableTool,
) -> tuple[list[dict[str, str]], PreparedConversation, CCBHandlerTable]:
    settings = get_settings()
    prepared = prepare_conversation(
        user_input=request.user_input,
        session_id=request.session_id,
        request_started_at=request.request_started_at,
        settings=settings,
    )
    table = tool.load()
    messages = list(prepared.messages[:-1])
    messages.append({"role": "system", "content": build_lookup_system_prompt(table)})
    messages.append({"role": "user", "content": build_lookup_user_prompt(request.user_input)})
    return messages, prepared, table


class CCBGetHandlerSkill(BaseSkill):
    name = "skill_ccb_get_handler"
    display_name = "职能查询"
    description = "查询广州分行内部职能分工，按工作职责匹配对应部门、岗位负责人链条和办公号码。"
    routing_hints = (
        "询问分行内部哪个部门、岗位或负责人对接某项工作",
        "询问对内对外工作分工、内部协同分工、客户服务由行内哪个岗位承接",
        "询问客户服务相关的投诉、疑难杂症等问题",
    )
    avoid_hints = (
        "行长是谁等涉及高管层问题",
        "某人的领导是谁等涉及人物间关系问题"
    )
    routing_examples = (
        "保险业务找谁对接",
        "客户转账限额找谁合适",
        "卡被锁了找哪个岗位负责",
        "人力部老总是谁",
        "财会现在是谁管？"
    )
    manual_relpath = "SKILL.md"

    def __init__(self) -> None:
        self._table_tool = CCBHandlerTableTool()

    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        settings = get_settings()
        try:
            messages, prepared, table = _build_lookup_messages(request, self._table_tool)
        except (FileNotFoundError, ValueError) as exc:
            fallback = _render_not_found_response()
            yield {"type": "pulse", "stage": "accepted", "elapsed_seconds": 0.0}
            yield {"type": "delta", "content": fallback}
            yield {
                "type": "done",
                "content": fallback,
                "metrics": {
                    "skill": self.name,
                    "lookup_error": str(exc),
                    "context": {
                        "session_id": request.session_id,
                    },
                },
            }
            return

        selected_payload: dict[str, Any] | None = None
        raw_content = ""
        for event in LLMProvider.stream_messages(
            messages=messages,
            model=request.model,
            smooth=request.smooth,
            enable_search=False,
        ):
            if event.get("type") != "done":
                yield event
                continue

            raw_content = event.get("content", "")
            selected_payload = _extract_json_object(raw_content)
            found = bool((selected_payload or {}).get("found"))
            record = table.get_by_sequence(str((selected_payload or {}).get("matched_sequence", ""))) if found else None
            final_content = (
                _format_record_response(table, record, (selected_payload or {}).get("reason"))
                if record
                else _render_not_found_response()
            )
            metrics = dict(event.get("metrics", {}))
            metrics["skill"] = self.name
            metrics["context"] = {
                **prepared.metrics(),
                **table.metrics(),
                **finalize_conversation(
                    prepared=prepared,
                    user_input=request.user_input,
                    assistant_output=final_content,
                    settings=settings,
                ),
            }
            metrics["lookup"] = {
                "raw_model_content_preview": raw_content[:400],
                "selection_parsed": bool(selected_payload),
                "selection_found": bool(record),
                "matched_sequence": record.sequence if record else None,
                "match_reason": (selected_payload or {}).get("reason"),
            }
            yield {"type": "done", "content": final_content, "metrics": metrics}

    def run_once(self, request: AgentRequest) -> AgentResponse:
        settings = get_settings()
        try:
            messages, prepared, table = _build_lookup_messages(request, self._table_tool)
        except (FileNotFoundError, ValueError) as exc:
            return AgentResponse(
                content=_render_not_found_response(),
                metrics={
                    "skill": self.name,
                    "lookup_error": str(exc),
                    "context": {
                        "session_id": request.session_id,
                    },
                },
            )

        raw_content, metrics = LLMProvider.with_metrics_messages(
            messages=messages,
            model=request.model,
            enable_search=False,
        )
        selected_payload = _extract_json_object(raw_content)
        found = bool((selected_payload or {}).get("found"))
        record = table.get_by_sequence(str((selected_payload or {}).get("matched_sequence", ""))) if found else None
        final_content = (
            _format_record_response(table, record, (selected_payload or {}).get("reason"))
            if record
            else _render_not_found_response()
        )
        metrics["skill"] = self.name
        metrics["context"] = {
            **prepared.metrics(),
            **table.metrics(),
            **finalize_conversation(
                prepared=prepared,
                user_input=request.user_input,
                assistant_output=final_content,
                settings=settings,
            ),
        }
        metrics["lookup"] = {
            "raw_model_content_preview": raw_content[:400],
            "selection_parsed": bool(selected_payload),
            "selection_found": bool(record),
            "matched_sequence": record.sequence if record else None,
            "match_reason": (selected_payload or {}).get("reason"),
        }
        return AgentResponse(content=final_content, metrics=metrics)
