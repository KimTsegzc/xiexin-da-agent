from __future__ import annotations

from typing import Any, Iterator

from .... import LLMProvider
from ....features.conversation_context import finalize_conversation, prepare_conversation
from ....features.shared_uploads import build_attachment_image_data_url, extract_attachment_text
from ....settings import get_settings
from ...contracts import AgentRequest, AgentResponse
from ..base import BaseSkill


def _build_uploaded_content(user_input: str, attachments: list[dict[str, Any]]) -> str | list[dict[str, Any]]:
    prompt_text = (user_input or "").strip()
    if prompt_text.lower().startswith("user:"):
        prompt_text = prompt_text[5:].strip()
    if not prompt_text:
        prompt_text = "请帮我分析这次上传的内容，并直接给出结论。"

    text_sections: list[str] = []
    image_items: list[dict[str, Any]] = []
    binary_notes: list[str] = []

    for attachment in attachments:
        media_type = str(attachment.get("media_type") or "binary").strip().lower()
        display_name = str(attachment.get("name") or attachment.get("original_name") or "未命名文件").strip() or "未命名文件"
        relative_path = str(attachment.get("relative_path") or "").strip()

        if media_type == "image":
            data_url = build_attachment_image_data_url(attachment)
            if data_url:
                image_items.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    }
                )
                continue
            binary_notes.append(f"- 图片：{display_name}（路径：{relative_path or '未知'}，图片过大或无法内联）")
            continue

        if media_type == "text":
            excerpt, truncated = extract_attachment_text(attachment)
            if excerpt:
                suffix = "\n[内容已截断]" if truncated else ""
                text_sections.append(
                    f"文件：{display_name}\n路径：{relative_path or '未知'}\n内容摘录：\n{excerpt}{suffix}"
                )
                continue

        binary_notes.append(f"- 文件：{display_name}（路径：{relative_path or '未知'}，当前只提供文件信息）")

    text_blocks: list[str] = [prompt_text]
    if text_sections:
        text_blocks.append("以下是本次上传的文本文件内容，请结合这些内容回答：\n\n" + "\n\n---\n\n".join(text_sections))
    if image_items:
        text_blocks.append("请同时结合已附带的图片内容理解和作答。")
    if binary_notes:
        text_blocks.append("以下文件已上传到 shared_space，可作为参考：\n" + "\n".join(binary_notes))

    final_text = "\n\n".join(block for block in text_blocks if block).strip()
    if image_items:
        return [{"type": "text", "text": final_text}, *image_items]
    return final_text


def _apply_uploaded_attachments(messages: list[dict[str, Any]], request: AgentRequest) -> list[dict[str, Any]]:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    attachments = metadata.get("attachments") if isinstance(metadata.get("attachments"), list) else []
    if not attachments:
        return messages

    updated_messages = [dict(message) for message in messages]
    if not updated_messages:
        return updated_messages

    updated_messages[-1] = {
        **updated_messages[-1],
        "content": _build_uploaded_content(request.user_input, attachments),
    }
    return updated_messages


class DirectChatSkill(BaseSkill):
    """Compatibility skill that forwards directly to the existing LLM provider."""

    name = "direct_chat"
    display_name = "通用对话"
    description = "通用对话兜底技能，处理闲聊、开放问答以及不属于专门业务技能的问题。"
    routing_hints = (
        "普通闲聊、问候、开放式问答",
        "无法明确归属到某个内部业务技能的问题",
        "外部机构、外部客服电话、泛生活类问题",
    )
    avoid_hints = (
        "明确要求查询分行内部职能分工、岗位负责人与办公号码",
    )
    routing_examples = (
        "hi",
        "客户咨询保险业务找谁",
        "今天几点了",
    )
    manual_relpath = "SKILL.md"

    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        settings = get_settings()
        prepared = prepare_conversation(
            user_input=request.user_input,
            session_id=request.session_id,
            request_started_at=request.request_started_at,
            settings=settings,
        )
        request_messages = _apply_uploaded_attachments(prepared.messages, request)
        for event in LLMProvider.stream_messages(
            messages=request_messages,
            model=request.model,
            smooth=request.smooth,
        ):
            if event.get("type") == "done":
                metrics = dict(event.get("metrics", {}))
                metadata = request.metadata if isinstance(request.metadata, dict) else {}
                attachments = metadata.get("attachments") if isinstance(metadata.get("attachments"), list) else []
                metrics["context"] = {
                    **prepared.metrics(),
                    **finalize_conversation(
                        prepared=prepared,
                        user_input=request.user_input,
                        assistant_output=event.get("content", ""),
                        settings=settings,
                    ),
                }
                metrics["uploads"] = {
                    "attachment_count": len(attachments),
                }
                event = {**event, "metrics": metrics}
            yield event

    def run_once(self, request: AgentRequest) -> AgentResponse:
        settings = get_settings()
        prepared = prepare_conversation(
            user_input=request.user_input,
            session_id=request.session_id,
            request_started_at=request.request_started_at,
            settings=settings,
        )
        request_messages = _apply_uploaded_attachments(prepared.messages, request)
        content, metrics = LLMProvider.with_metrics_messages(
            messages=request_messages,
            model=request.model,
        )
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        attachments = metadata.get("attachments") if isinstance(metadata.get("attachments"), list) else []
        metrics["context"] = {
            **prepared.metrics(),
            **finalize_conversation(
                prepared=prepared,
                user_input=request.user_input,
                assistant_output=content,
                settings=settings,
            ),
        }
        metrics["uploads"] = {
            "attachment_count": len(attachments),
        }
        return AgentResponse(content=content, metrics=metrics)
