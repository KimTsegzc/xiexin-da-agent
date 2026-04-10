from __future__ import annotations

import json
import re
from typing import Any, Iterator

from .... import LLMProvider
from ....integrations.email_sender import EmailSender, EmailSenderError
from ....integrations.search_provider import SearchProvider, SearchProviderError
from ...contracts import AgentRequest, AgentResponse
from ..base import BaseSkill


_EMAIL_ADAPTER_MODEL = "qwen-turbo"
_EMAIL_ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://([^/\s]+)", re.IGNORECASE)
_SEARCH_FIRST_HINTS = (
    "最新",
    "今天",
    "昨日",
    "昨天",
    "近况",
    "局势",
    "新闻",
    "行情",
    "汇率",
    "天气",
    "市场",
    "检索",
    "搜索",
)
_MAIL_HISTORY_QUERY_RE = re.compile(r"已发送|发过.*邮件|邮件记录|邮件历史|我刚发了哪些邮件", re.IGNORECASE)


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


def _extract_kv_value(text: str, *keys: str) -> str | None:
    for key in keys:
        pattern = re.compile(
            rf"(?:^|[\n\r\s,;，；]){re.escape(key)}\s*[:：=]\s*(.+?)(?=$|[\n\r])",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            value = match.group(1).strip().strip('"').strip("'")
            if value:
                return value
    return None


def _parse_email_request(request: AgentRequest) -> tuple[str, str, str | None]:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    email_meta = metadata.get("email") if isinstance(metadata.get("email"), dict) else metadata

    subject = str((email_meta.get("subject") or "")).strip() if isinstance(email_meta, dict) else ""
    body = str((email_meta.get("body") or email_meta.get("content") or "")).strip() if isinstance(email_meta, dict) else ""
    receiver = str((email_meta.get("receiver") or email_meta.get("to") or "")).strip() if isinstance(email_meta, dict) else ""

    if subject and body:
        return subject, body, receiver or None

    raw_input = _strip_user_prefix(request.user_input)

    payload = _extract_json_payload(raw_input)
    if payload:
        subject = str(payload.get("subject") or "").strip()
        body = str(payload.get("body") or payload.get("content") or "").strip()
        receiver = str(payload.get("receiver") or payload.get("to") or "").strip()
        if subject and body:
            return subject, body, receiver or None

    subject = _extract_kv_value(raw_input, "subject", "主题") or ""
    body = _extract_kv_value(raw_input, "body", "content", "正文", "内容") or ""
    receiver = _extract_kv_value(raw_input, "receiver", "to", "收件人") or ""
    return subject, body, receiver or None


def _extract_receiver_from_text(text: str) -> str | None:
    match = _EMAIL_ADDRESS_RE.search(text or "")
    if not match:
        return None
    return match.group(0).strip() or None


def _adapt_email_request_with_llm(request: AgentRequest) -> dict[str, str] | None:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    raw_input = _strip_user_prefix(request.user_input)
    system_prompt = (
        "你是邮件参数提取器。"
        "请从用户输入和metadata中提取邮件参数，并只返回JSON对象。"
        "JSON schema: {\"receiver\": string, \"subject\": string, \"body\": string}。"
        "如果缺少subject，请根据正文生成一个简短主题（例如：通知）。"
        "如果缺少body，请根据用户需求补全正文。"
        "当用户要求整理天气、新闻、市场、行情、数据等信息时，请启用联网能力先补充有效内容，再写入body。"
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
            model=_EMAIL_ADAPTER_MODEL,
            enable_search=True,
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
        "或者：给 xx@ccb.com 发会议提醒，说明明早9点五楼会议室。\n"
        "如果你想先查资料再发，也可以说：先整理昨天伊朗局势，再发给 xx@ccb.com。"
    )


def _is_mail_history_query(text: str) -> bool:
    return bool(_MAIL_HISTORY_QUERY_RE.search(text or ""))


def _extract_domains(text: str) -> list[str]:
    domains = []
    for match in _URL_RE.finditer(text or ""):
        domain = (match.group(1) or "").strip().lower()
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def _build_search_context(raw_input: str, *, web_top_k: int = 5) -> tuple[str | None, dict[str, Any]]:
    try:
        response = SearchProvider.web_search(
            messages=[{"role": "user", "content": raw_input}],
            web_top_k=web_top_k,
            timeout=25.0,
        )
    except (SearchProviderError, RuntimeError, ValueError):
        return None, {"provider_used": True, "provider_ok": False, "results_count": 0}

    results = response.get("search_results") if isinstance(response, dict) else None
    if not isinstance(results, list) or not results:
        return None, {"provider_used": True, "provider_ok": True, "results_count": 0}

    lines: list[str] = []
    for item in results[:web_top_k]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        summary = str(item.get("snippet") or item.get("summary") or item.get("content") or "").strip()
        url = str(item.get("url") or item.get("link") or "").strip()
        piece = f"标题：{title or '未命名'}\n摘要：{summary or '无'}"
        if url:
            piece += f"\n来源：{url}"
        lines.append(piece)

    context = "\n\n".join(lines).strip() or None
    return context, {
        "provider_used": True,
        "provider_ok": True,
        "results_count": len(results),
    }


def _needs_search_first(request: AgentRequest, subject: str, body: str) -> bool:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    email_meta = metadata.get("email") if isinstance(metadata.get("email"), dict) else {}

    meta_flag = email_meta.get("search_first")
    if meta_flag is None:
        meta_flag = metadata.get("search_first")
    if isinstance(meta_flag, bool):
        return meta_flag
    if isinstance(meta_flag, str):
        normalized = meta_flag.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False

    raw = _strip_user_prefix(request.user_input)
    if any(hint in raw for hint in _SEARCH_FIRST_HINTS):
        return True

    # 内容过短时优先触发搜索增强，避免"发出去了但信息太空"。
    if len((body or "").strip()) < 60:
        return True

    # 默认开启搜索优先，可通过 metadata.search_first=false 关闭。
    return True


def _enrich_email_with_search(
    *,
    request: AgentRequest,
    receiver: str | None,
    subject: str,
    body: str,
) -> tuple[dict[str, str] | None, dict[str, Any]]:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    raw_input = _strip_user_prefix(request.user_input)
    search_context, search_meta = _build_search_context(raw_input)
    system_prompt = (
        "你是邮件内容增强助手。"
        "请根据用户请求生成可直接发送的邮件正文。"
        "若提供了外部检索摘要，必须优先使用该摘要并保留关键事实。"
        "若没有检索摘要，可自行联网检索并在正文中带上来源链接。"
        "JSON schema: {\"subject\": string, \"body\": string}。"
        "要求：主题简洁；正文结构清晰、可直接发送；至少包含2条具体事实；"
        "如果用户已给出明确正文，仅做轻量补充，不要改写核心意图。"
        "不要使用‘根据最新消息’这类空泛措辞，不要输出占位语。"
        "禁止输出JSON以外的内容。"
    )
    payload = {
        "user_input": raw_input,
        "metadata": metadata,
        "receiver": receiver,
        "subject": subject,
        "body": body,
        "search_context": search_context,
    }
    try:
        response = LLMProvider.with_response_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            model=_EMAIL_ADAPTER_MODEL,
            enable_search=True,
        )
    except Exception:
        return None, {
            **search_meta,
            "model_search_fallback": True,
            "search_domains": [],
        }

    parsed = _extract_json_payload(str(response.get("content", "") or ""))
    if not parsed:
        return None, {
            **search_meta,
            "model_search_fallback": True,
            "search_domains": [],
        }

    enriched_subject = str(parsed.get("subject") or "").strip()
    enriched_body = str(parsed.get("body") or parsed.get("content") or "").strip()
    if not enriched_subject and not enriched_body:
        return None, {
            **search_meta,
            "model_search_fallback": True,
            "search_domains": [],
        }

    domains = _extract_domains(enriched_body)
    # 没有外部搜索上下文且正文里也没有来源链接时，视为低置信度检索结果。
    if search_context is None and not domains:
        return None, {
            **search_meta,
            "model_search_fallback": True,
            "search_domains": [],
            "quality_gate_rejected": True,
        }

    return (
        {
            "subject": enriched_subject,
            "body": enriched_body,
        },
        {
            **search_meta,
            "model_search_fallback": search_context is None,
            "search_domains": domains,
        },
    )


def _explain_email_failure_with_llm(
    *,
    error_text: str,
    receiver: str | None,
    subject: str,
    request: AgentRequest,
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
            model=_EMAIL_ADAPTER_MODEL,
            enable_search=False,
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
        subject, body, receiver = _parse_email_request(request)
        raw_input = _strip_user_prefix(request.user_input)

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

        llm_adapter_used = False
        llm_search_enricher_used = False
        llm_search_meta: dict[str, Any] = {
            "provider_used": False,
            "provider_ok": False,
            "results_count": 0,
            "model_search_fallback": False,
            "search_domains": [],
        }
        if not subject or not body:
            adapted = _adapt_email_request_with_llm(request)
            if adapted:
                llm_adapter_used = True
                if not subject:
                    subject = str(adapted.get("subject") or "").strip()
                if not body:
                    body = str(adapted.get("body") or "").strip()
                if not receiver:
                    receiver = str(adapted.get("receiver") or "").strip() or None

        if subject and body and _needs_search_first(request, subject, body):
            enriched, enrich_meta = _enrich_email_with_search(
                request=request,
                receiver=receiver,
                subject=subject,
                body=body,
            )
            llm_search_meta = {**llm_search_meta, **enrich_meta}
            if enriched:
                llm_search_enricher_used = True
                subject = str(enriched.get("subject") or subject).strip() or subject
                body = str(enriched.get("body") or body).strip() or body

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
                        "llm_adapter_model": _EMAIL_ADAPTER_MODEL,
                        "llm_search_enricher_used": llm_search_enricher_used,
                        "llm_search_enricher_model": _EMAIL_ADAPTER_MODEL,
                        "search_provider_used": llm_search_meta.get("provider_used"),
                        "search_provider_ok": llm_search_meta.get("provider_ok"),
                        "search_results_count": llm_search_meta.get("results_count"),
                        "search_domains": llm_search_meta.get("search_domains"),
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
                        "llm_adapter_model": _EMAIL_ADAPTER_MODEL,
                        "llm_search_enricher_used": llm_search_enricher_used,
                        "llm_search_enricher_model": _EMAIL_ADAPTER_MODEL,
                        "search_provider_used": llm_search_meta.get("provider_used"),
                        "search_provider_ok": llm_search_meta.get("provider_ok"),
                        "search_results_count": llm_search_meta.get("results_count"),
                        "search_domains": llm_search_meta.get("search_domains"),
                        "llm_failure_explainer_used": bool(llm_failure_explanation),
                        "llm_failure_explainer_model": _EMAIL_ADAPTER_MODEL,
                    },
                },
            )

        final_receiver = str(result.get("receiver") or receiver or "")
        final_subject = str(result.get("subject") or subject)
        transport = str(result.get("transport") or "")
        return AgentResponse(
            content=(
                "邮件已发送。\n"
                f"收件人：{final_receiver or '未返回'}\n"
                f"主题：{final_subject}\n"
                f"通道：{transport or 'smtp'}"
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
                    "llm_adapter_model": _EMAIL_ADAPTER_MODEL,
                    "llm_search_enricher_used": llm_search_enricher_used,
                    "llm_search_enricher_model": _EMAIL_ADAPTER_MODEL,
                    "search_provider_used": llm_search_meta.get("provider_used"),
                    "search_provider_ok": llm_search_meta.get("provider_ok"),
                    "search_results_count": llm_search_meta.get("results_count"),
                    "search_domains": llm_search_meta.get("search_domains"),
                },
            },
        )
