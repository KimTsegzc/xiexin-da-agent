from __future__ import annotations

import difflib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .... import LLMProvider
from ....integrations.email_sender import EmailSender, EmailSenderError
from ...contracts import AgentRequest, AgentResponse
from ..base import BaseSkill


_EMAIL_ADAPTER_MODEL = "qwen-turbo"
_EMAIL_ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_MAIL_HISTORY_QUERY_RE = re.compile(r"已发送|发过.*邮件|邮件记录|邮件历史|我刚发了哪些邮件", re.IGNORECASE)
_BODY_COMMAND_LIKE_RE = re.compile(
    r"^(发|发送|帮我|请|给|整理|汇总|总结|列举|梳理|分析).*(邮件|发给|报告|整理|汇总|列举|邮箱)?",
    re.IGNORECASE,
)
_RICH_BODY_REQUEST_RE = re.compile(
    r"更新|最新|局势|战局|分析|影响|报告|整理|汇总|总结|梳理|三点|要点|附来源|来源|简报|研判",
    re.IGNORECASE,
)
_CONTACT_FILE = Path(__file__).resolve().parent / "data" / "contacts.json"
_CONTACT_SPLIT_RE = re.compile(r"[\s,，。.:：;；()（）\[\]【】<>《》'\"/\\|]+")


def _resolve_skill_model(request: AgentRequest) -> str:
    selected = str(request.model or "").strip()
    return selected or _EMAIL_ADAPTER_MODEL


def _strip_user_prefix(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.lower().startswith("user:"):
        return stripped[5:].strip()
    return stripped


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_attachment_hints(source: dict[str, Any] | None) -> dict[str, Any]:
    payload = source if isinstance(source, dict) else {}

    attachments_raw = payload.get("attachments")
    attachments: list[dict[str, Any]] = []
    if isinstance(attachments_raw, list):
        for item in attachments_raw:
            if isinstance(item, dict):
                attachments.append(dict(item))

    memory_refs_raw = payload.get("memory_refs") or payload.get("memory_attachments")
    memory_refs: list[str] = []
    if isinstance(memory_refs_raw, list):
        for item in memory_refs_raw:
            text = str(item or "").strip()
            if text:
                memory_refs.append(text)

    return {
        "attachments": attachments,
        "memory_refs": memory_refs,
    }


def _parse_email_request(request: AgentRequest) -> tuple[str, str, str | None, dict[str, Any]]:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    email_meta = metadata.get("email") if isinstance(metadata.get("email"), dict) else metadata

    subject = str((email_meta.get("subject") or "")).strip() if isinstance(email_meta, dict) else ""
    body = str((email_meta.get("body") or email_meta.get("content") or "")).strip() if isinstance(email_meta, dict) else ""
    receiver = str((email_meta.get("receiver") or email_meta.get("to") or "")).strip() if isinstance(email_meta, dict) else ""
    field_sources = {
        "subject": "metadata" if subject else None,
        "body": "metadata" if body else None,
        "receiver": "metadata" if receiver else None,
    }
    attachment_hints = _extract_attachment_hints(email_meta if isinstance(email_meta, dict) else None)

    if subject or body or receiver or attachment_hints["attachments"] or attachment_hints["memory_refs"]:
        return subject, body, receiver or None, {"field_sources": field_sources, **attachment_hints}

    raw_input = _strip_user_prefix(request.user_input)

    payload = _extract_json_payload(raw_input)
    if payload:
        subject = str(payload.get("subject") or "").strip()
        body = str(payload.get("body") or payload.get("content") or "").strip()
        receiver = str(payload.get("receiver") or payload.get("to") or "").strip()
        field_sources = {
            "subject": "json" if subject else None,
            "body": "json" if body else None,
            "receiver": "json" if receiver else None,
        }
        attachment_hints = _extract_attachment_hints(payload)
        return subject, body, receiver or None, {"field_sources": field_sources, **attachment_hints}

    return "", "", None, {"field_sources": field_sources, **attachment_hints}


def _extract_receiver_from_text(text: str) -> str | None:
    match = _EMAIL_ADDRESS_RE.search(text or "")
    if not match:
        return None
    return match.group(0).strip() or None


def _normalize_contact_key(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[\s\-_.·]", "", value)
    return value


def _load_contacts() -> list[dict[str, Any]]:
    if not _CONTACT_FILE.exists():
        return []
    try:
        payload = json.loads(_CONTACT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []

    contacts: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        email = str(item.get("email") or "").strip()
        if not name or not email:
            continue
        aliases_raw = item.get("aliases")
        aliases: list[str] = []
        if isinstance(aliases_raw, list):
            for alias in aliases_raw:
                alias_text = str(alias or "").strip()
                if alias_text:
                    aliases.append(alias_text)
        contacts.append(
            {
                "name": name,
                "email": email,
                "aliases": aliases,
            }
        )
    return contacts


def _build_contact_maps(contacts: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[tuple[str, dict[str, Any]]]]:
    by_key: dict[str, dict[str, Any]] = {}
    keywords: list[tuple[str, dict[str, Any]]] = []
    for contact in contacts:
        names = [str(contact.get("name") or "").strip(), *[str(a).strip() for a in contact.get("aliases") or []]]
        for name in names:
            if not name:
                continue
            key = _normalize_contact_key(name)
            if key:
                by_key[key] = contact
                keywords.append((name, contact))
    # 长词优先，避免 "谢" 覆盖 "谢鑫"。
    keywords.sort(key=lambda item: len(item[0]), reverse=True)
    return by_key, keywords


def _resolve_receiver_from_contacts(receiver: str | None, raw_input: str) -> tuple[str | None, dict[str, Any]]:
    contacts = _load_contacts()
    if not contacts:
        return receiver, {"contact_resolved": False, "contact_match": "none"}

    by_key, keywords = _build_contact_maps(contacts)

    # 1) receiver 已是邮箱，直接通过。
    if receiver and _EMAIL_ADDRESS_RE.fullmatch(receiver.strip()):
        return receiver, {"contact_resolved": False, "contact_match": "already_email"}

    # 2) receiver 作为人名精确匹配。
    receiver_text = str(receiver or "").strip()
    if receiver_text:
        hit = by_key.get(_normalize_contact_key(receiver_text))
        if hit:
            return str(hit.get("email") or "").strip() or receiver, {
                "contact_resolved": True,
                "contact_match": "receiver_exact",
                "contact_name": hit.get("name"),
            }

    # 3) 在用户原文中做姓名/别名命中。
    text = raw_input or ""
    for keyword, hit in keywords:
        if keyword and keyword in text:
            return str(hit.get("email") or "").strip() or receiver, {
                "contact_resolved": True,
                "contact_match": "text_contains",
                "contact_name": hit.get("name"),
            }

    # 4) 轻量模糊匹配（用于“谢新”“龙将”这类轻微输错）。
    tokens = [token for token in _CONTACT_SPLIT_RE.split(text) if token]
    if receiver_text:
        tokens.append(receiver_text)
    candidates = [_normalize_contact_key(token) for token in tokens if token]
    keys = list(by_key.keys())
    for candidate in candidates:
        if not candidate:
            continue
        close = difflib.get_close_matches(candidate, keys, n=1, cutoff=0.82)
        if not close:
            continue
        hit = by_key.get(close[0])
        if hit:
            return str(hit.get("email") or "").strip() or receiver, {
                "contact_resolved": True,
                "contact_match": "fuzzy",
                "contact_name": hit.get("name"),
            }

    return receiver, {"contact_resolved": False, "contact_match": "none"}


def _adapt_email_request_with_llm(request: AgentRequest, model_name: str) -> dict[str, str] | None:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    raw_input = _strip_user_prefix(request.user_input)
    system_prompt = (
        "你是邮件参数提取器。"
        "请从用户输入和metadata中提取邮件参数，并只返回JSON对象。"
        "JSON schema: {\"receiver\": string, \"subject\": string, \"body\": string, \"attachments\": array, \"memory_refs\": array}。"
        "receiver 可以是邮箱，也可以是用户提到的联系人姓名，后端会再做联系人映射。"
        "如果缺少subject，请根据用户意图生成一个简短明确的主题。"
        "如果缺少body，请根据用户需求补全成可直接发送的邮件正文。"
        "如果用户已经明确给出很短的正文，如“你好”“收到请回复”，允许保留短正文。"
        "attachments 和 memory_refs 当前只做保留位，没有内容时返回空数组。"
        "禁止输出除JSON外的任何文字。"
    )
    user_payload = {
        "user_input": raw_input,
        "metadata": metadata,
    }
    try:
        response = LLMProvider.with_response_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            model=model_name,
        )
    except Exception:
        return None

    payload = _extract_json_payload(str(response.get("content", "") or ""))
    if not payload:
        return None

    receiver = str(payload.get("receiver") or payload.get("to") or "").strip()
    subject = str(payload.get("subject") or "").strip()
    body = str(payload.get("body") or payload.get("content") or "").strip()
    if not receiver:
        receiver = _extract_receiver_from_text(raw_input) or ""
    return {
        "receiver": receiver,
        "subject": subject,
        "body": body,
    }


def _build_usage_tip() -> str:
    return (
        "我可以直接帮你发邮件，再补一句就能发出：\n"
        "比如：发给 xiexin1.gd@ccb.com，主题“伊朗局势报告”，正文写昨天三点变化。\n"
        "或者：给 xx@ccb.com 发会议提醒，说明明早9点五楼会议室。"
    )


def _build_missing_receiver_tip() -> str:
    return (
        "我已经进入邮件发送技能了，但还缺明确收件人。\n"
        "你可以直接给邮箱地址，或说联系人姓名，例如：发给谢鑫，整理昨天伊朗局势三点更新并附来源。"
    )


def _normalize_compare_text(text: str) -> str:
    value = (text or "").strip().lower()
    return re.sub(r"[\s\n\r\t，。；;：:、,.!?！？（）()【】\[\]<>《》\-—_]", "", value)


def _sentence_count(text: str) -> int:
    parts = [part.strip() for part in re.split(r"[。！？!?\n]+", text or "") if part.strip()]
    return len(parts)


def _looks_like_subject_echo(body: str, subject: str) -> bool:
    normalized_body = _normalize_compare_text(body)
    normalized_subject = _normalize_compare_text(subject)
    if not normalized_body or not normalized_subject:
        return False
    if normalized_body == normalized_subject:
        return True
    if normalized_body.startswith(normalized_subject) or normalized_subject.startswith(normalized_body):
        return True
    similarity = difflib.SequenceMatcher(None, normalized_body, normalized_subject).ratio()
    return similarity >= 0.88


def _needs_rich_body(raw_input: str) -> bool:
    return bool(_RICH_BODY_REQUEST_RE.search(raw_input or ""))


def _is_low_quality_body(
    body: str,
    raw_input: str,
    *,
    subject: str = "",
    explicit_body: bool = False,
    require_rich_body: bool = False,
) -> bool:
    text = (body or "").strip()
    user_text = (raw_input or "").strip()
    if not text:
        return True
    if len(text) < 24 and not explicit_body:
        return True
    if _looks_like_subject_echo(text, subject):
        return True
    if user_text and text == user_text:
        return True
    if _BODY_COMMAND_LIKE_RE.search(text):
        return True
    if ("发给" in text or "邮箱" in text) and not explicit_body:
        return True
    if require_rich_body and _sentence_count(text) < 3:
        return True
    return False


def _refine_email_body_with_llm(
    *,
    subject: str,
    body: str,
    raw_input: str,
    model_name: str,
    require_rich_body: bool = False,
) -> str | None:
    structure_requirement = (
        "要求：至少3句话；包含背景、要点和结尾。"
        if not require_rich_body
        else "要求：必须写成可直接发送的完整邮件正文，至少4句话，并包含开场说明、3个独立要点和收尾判断；各要点尽量单独成句。"
    )
    source_requirement = "如果用户要求附来源或最新动态，请尽量联网补充可靠信息，并在正文中自然写出来源线索。"
    system_prompt = (
        "你是邮件正文润色助手。"
        "请将用户意图改写成可直接发送的正式中文邮件正文。"
        f"{structure_requirement}"
        f"{source_requirement}"
        "禁止只写一句话摘要，禁止把标题原样重复成正文。"
        "只输出正文，不要标题，不要额外说明。"
    )
    payload = {
        "user_input": raw_input,
        "subject": subject,
        "body": body,
    }
    try:
        response = LLMProvider.with_response_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            model=model_name,
            enable_search=True,
        )
    except Exception:
        return None

    refined = str(response.get("content", "") or "").strip()
    if not refined or _is_low_quality_body(refined, raw_input, subject=subject, require_rich_body=require_rich_body):
        return None
    return refined


def _is_mail_history_query(text: str) -> bool:
    return bool(_MAIL_HISTORY_QUERY_RE.search(text or ""))


def _explain_email_failure_with_llm(
    *,
    error_text: str,
    receiver: str | None,
    subject: str,
    request: AgentRequest,
    model_name: str,
) -> str | None:
    raw_input = _strip_user_prefix(request.user_input)
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    system_prompt = (
        "你是邮件发送失败解释助手。"
        "请根据SMTP错误，给用户一个简洁中文解释。"
        "输出2到4行："
        "第1行写主要原因；"
        "第2到4行给出可执行修复建议。"
        "如果收件人不是完整邮箱（缺少@或域名），必须明确指出并给出示例。"
        "不要输出JSON，不要编造成功发送结果。"
    )
    payload = {
        "error": error_text,
        "receiver": receiver,
        "subject": subject,
        "user_input": raw_input,
        "metadata": metadata,
    }
    try:
        response = LLMProvider.with_response_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            model=model_name,
        )
    except Exception:
        return None

    explanation = str(response.get("content", "") or "").strip()
    return explanation or None


class SendEmailSkill(BaseSkill):
    name = "send_email"
    display_name = "邮件发送"
    description = "发送邮件技能：根据前端指令发送SMTP文本邮件，可指定收件人、主题和正文。"
    routing_hints = (
        "明确要求发送邮件、代发邮件、通知邮件",
        "用户明确给出收件人、主题、正文等字段",
    )
    avoid_hints = (
        "普通闲聊与开放问答",
        "内部职能分工查询",
    )
    routing_examples = (
        "帮我发邮件给xx@xx.com，主题是会议提醒，正文是明早9点开会",
        "发送邮件 {\"receiver\":\"xx@xx.com\",\"subject\":\"测试\",\"body\":\"你好\"}",
    )
    manual_relpath = "SKILL.md"

    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        response = self.run_once(request)
        yield {"type": "pulse", "stage": "accepted", "elapsed_seconds": 0.0}
        yield {"type": "delta", "content": response.content}
        yield {"type": "done", "content": response.content, "metrics": response.metrics}

    def run_once(self, request: AgentRequest) -> AgentResponse:
        subject, body, receiver, compose_hints = _parse_email_request(request)
        raw_input = _strip_user_prefix(request.user_input)
        skill_model = _resolve_skill_model(request)
        field_sources = compose_hints.get("field_sources") if isinstance(compose_hints, dict) else {}
        explicit_body = bool(isinstance(field_sources, dict) and field_sources.get("body") in {"metadata", "json"})
        attachments = compose_hints.get("attachments") if isinstance(compose_hints, dict) else []
        memory_refs = compose_hints.get("memory_refs") if isinstance(compose_hints, dict) else []
        require_rich_body = _needs_rich_body(raw_input)
        body_generated_by_llm = False

        if _is_mail_history_query(raw_input):
            return AgentResponse(
                content=(
                    "我目前只能代你发送邮件，还不能直接读取邮箱‘已发送’列表。\n"
                    "你可以这样说：‘发给谁、主题是什么、要点是什么’，我就能立刻代发。"
                ),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "history_query_not_supported",
                    },
                },
            )

        if not receiver:
            receiver = _extract_receiver_from_text(raw_input)

        receiver, contact_metrics = _resolve_receiver_from_contacts(receiver=receiver, raw_input=raw_input)

        llm_adapter_used = False
        llm_body_refiner_used = False
        if not receiver or not subject or not body:
            adapted = _adapt_email_request_with_llm(request, model_name=skill_model)
            if adapted:
                llm_adapter_used = True
                if not receiver:
                    receiver = str(adapted.get("receiver") or "").strip() or None
                if not subject:
                    subject = str(adapted.get("subject") or "").strip()
                if not body:
                    body = str(adapted.get("body") or "").strip()
                    body_generated_by_llm = bool(body)

        # LLM 可能回填人名而非邮箱，这里再次做联系人查转兜底。
        receiver, post_adapter_contact_metrics = _resolve_receiver_from_contacts(receiver=receiver, raw_input=raw_input)
        if post_adapter_contact_metrics.get("contact_resolved"):
            contact_metrics = post_adapter_contact_metrics

        if not receiver:
            return AgentResponse(
                content=_build_missing_receiver_tip(),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "missing_receiver",
                        "receiver": receiver,
                        "llm_adapter_used": llm_adapter_used,
                        "llm_adapter_model": skill_model,
                        "llm_body_refiner_used": llm_body_refiner_used,
                        "attachment_count": len(attachments),
                        "memory_ref_count": len(memory_refs),
                        "implementation_hint": "大模型互联网搜索",
                        **contact_metrics,
                    },
                },
            )

        body_quality_blocked = False
        should_refine_generated_body = bool(subject and body and body_generated_by_llm and not explicit_body)
        if subject and body and (
            should_refine_generated_body
            or _is_low_quality_body(
                body,
                raw_input,
                subject=subject,
                explicit_body=explicit_body,
                require_rich_body=require_rich_body,
            )
        ):
            refined_body = _refine_email_body_with_llm(
                subject=subject,
                body=body,
                raw_input=raw_input,
                model_name=skill_model,
                require_rich_body=require_rich_body,
            )
            if refined_body:
                body = refined_body
                llm_body_refiner_used = True
            else:
                body_quality_blocked = _is_low_quality_body(
                    body,
                    raw_input,
                    subject=subject,
                    explicit_body=explicit_body,
                    require_rich_body=require_rich_body,
                ) or should_refine_generated_body

        if body_quality_blocked:
            return AgentResponse(
                content=(
                    "我先拦截了这次发送：当前正文看起来还是指令原文，直接发出会是空内容邮件。\n"
                    "请再补一句你希望邮件里出现的要点，或让我继续展开后再发送。"
                ),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "low_quality_body_blocked",
                        "receiver": receiver,
                        "subject": subject,
                        "llm_adapter_used": llm_adapter_used,
                        "llm_adapter_model": skill_model,
                        "llm_body_refiner_used": llm_body_refiner_used,
                        "implementation_hint": "大模型互联网搜索",
                        **contact_metrics,
                    },
                },
            )

        if not subject or not body:
            return AgentResponse(
                content=_build_usage_tip(),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "missing_subject_or_body",
                        "receiver": receiver,
                        "llm_adapter_used": llm_adapter_used,
                        "llm_adapter_model": skill_model,
                        "llm_body_refiner_used": llm_body_refiner_used,
                        "attachment_count": len(attachments),
                        "memory_ref_count": len(memory_refs),
                        "implementation_hint": "大模型互联网搜索",
                        **contact_metrics,
                    },
                },
            )

        try:
            result = EmailSender.send_text(
                subject=subject,
                body=body,
                receiver=receiver,
            )
        except EmailSenderError as exc:
            failure_reason = str(exc)
            llm_failure_explanation = _explain_email_failure_with_llm(
                error_text=failure_reason,
                receiver=receiver,
                subject=subject,
                request=request,
                model_name=skill_model,
            )
            content = f"邮件发送失败：{failure_reason}"
            if llm_failure_explanation:
                content = f"邮件发送失败。\n{llm_failure_explanation}\n\n原始错误：{failure_reason}"
            return AgentResponse(
                content=content,
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": failure_reason,
                        "receiver": receiver,
                        "subject": subject,
                        "llm_adapter_used": llm_adapter_used,
                        "llm_adapter_model": skill_model,
                        "llm_body_refiner_used": llm_body_refiner_used,
                        "attachment_count": len(attachments),
                        "memory_ref_count": len(memory_refs),
                        "implementation_hint": "大模型互联网搜索",
                        **contact_metrics,
                        "llm_failure_explainer_used": bool(llm_failure_explanation),
                        "llm_failure_explainer_model": skill_model,
                    },
                },
            )

        final_receiver = str(result.get("receiver") or receiver or "")
        final_subject = str(result.get("subject") or subject)
        transport = str(result.get("transport") or "")
        sent_at = datetime.now().strftime("%y年%m月%d日，%H:%M:%S")
        return AgentResponse(
            content=(
                "邮件已发送。\n"
                f"收件人：{final_receiver or '未返回'}\n"
                f"主题：{final_subject}\n"
                f"发送时间: {sent_at}"
            ),
            metrics={
                "skill": self.name,
                "send_email": {
                    "ok": True,
                    "receiver": final_receiver,
                    "subject": final_subject,
                    "transport": transport,
                    "smtp_host": result.get("smtp_host"),
                    "smtp_port": result.get("smtp_port"),
                    "llm_adapter_used": llm_adapter_used,
                    "llm_adapter_model": skill_model,
                    "llm_body_refiner_used": llm_body_refiner_used,
                    "attachment_count": len(attachments),
                    "memory_ref_count": len(memory_refs),
                    "implementation_hint": "大模型互联网搜索",
                    **contact_metrics,
                },
            },
        )
