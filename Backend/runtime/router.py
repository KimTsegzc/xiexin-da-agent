from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .. import LLMProvider
from ..settings import get_settings
from .contracts import AgentRequest
from .registry import SkillRegistry
from .skills.skill_send_email import has_pending_email_confirmation
from .skills.base import SkillDescriptor


_ROUTER_PROMPT = (
    "你是智能体技能路由器。你的唯一任务是在已注册技能中选择一个最合适的技能。\n"
    "必须使用 tool calling 调用 select_skill，不能直接输出自然语言答案。\n"
    "如果用户明确要求发送邮件、代发通知邮件、给某个邮箱发主题和正文，优先选择 send_email。\n"
    "如果问题是普通闲聊、开放问答、通用建议，优先选择 direct_chat。\n"
    "只有当用户明确在问行内内部职能分工、哪个部门/岗位/负责人承接、内部接口人、办公号码时，才选择 skill_ccb_get_handler。\n"
    "如果不确定，选择 direct_chat，不要冒进。\n\n"
    "以下是当前可用技能说明：\n"
)


def _normalize_user_input(user_input: str) -> str:
    return (user_input or "").replace("user:", "", 1).strip()


def _build_router_tool(descriptors: tuple[SkillDescriptor, ...]) -> list[dict[str, Any]]:
    skill_names = [descriptor.name for descriptor in descriptors]
    return [
        {
            "type": "function",
            "function": {
                "name": "select_skill",
                "description": "Select exactly one registered skill to handle the current user request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "enum": skill_names,
                            "description": "The registered skill name that should handle this request.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Short reason for the routing decision.",
                        },
                    },
                    "required": ["skill_name", "reason"],
                    "additionalProperties": False,
                },
            },
        }
    ]


def _build_router_messages(
    *,
    user_input: str,
    descriptors: tuple[SkillDescriptor, ...],
) -> list[dict[str, str]]:
    rendered_skills = "\n\n".join(descriptor.render_for_router() for descriptor in descriptors)
    return [
        {
            "role": "system",
            "content": _ROUTER_PROMPT + rendered_skills,
        },
        {
            "role": "user",
            "content": f"用户问题：{_normalize_user_input(user_input)}",
        },
    ]


def _default_skill_name(skills: SkillRegistry) -> str:
    names = tuple(skills.names())
    if "direct_chat" in names:
        return "direct_chat"
    if not names:
        raise ValueError("No skills registered in runtime")
    return names[0]


@dataclass(frozen=True, slots=True)
class RouteDecision:
    skill_name: str
    skill_display_name: str
    source: str
    reason: str
    model: str | None = None
    fallback_used: bool = False
    llm_metrics: dict[str, Any] = field(default_factory=dict)

    def metrics(self) -> dict[str, Any]:
        return {
            "selected_skill": self.skill_name,
            "selected_skill_label": self.skill_display_name,
            "source": self.source,
            "reason": self.reason,
            "model": self.model,
            "fallback_used": self.fallback_used,
            "llm": self.llm_metrics,
        }


_SEND_EMAIL_INTENT_RE = re.compile(
    r"发送?邮件|发邮件|邮件给|收件人|主题|正文|subject\s*[:=]|receiver\s*[:=]|\bto\s*[:=]",
    re.IGNORECASE,
)


def _is_send_email_intent(request: AgentRequest) -> bool:
    if has_pending_email_confirmation(request.session_id):
        return True

    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    email_meta = metadata.get("email") if isinstance(metadata.get("email"), dict) else metadata
    if isinstance(email_meta, dict):
        if any(str(email_meta.get(key) or "").strip() for key in ("receiver", "to", "subject", "body", "content")):
            return True

    normalized = _normalize_user_input(request.user_input)
    return bool(_SEND_EMAIL_INTENT_RE.search(normalized))


def _resolve_skill_display_name(descriptor_map: dict[str, SkillDescriptor], skill_name: str) -> str:
    descriptor = descriptor_map.get(skill_name)
    if descriptor is None:
        return skill_name
    return descriptor.display_name or skill_name


class SkillRouter:
    def select_skill(self, request: AgentRequest, skills: SkillRegistry) -> RouteDecision:
        settings = get_settings()
        default_skill = _default_skill_name(skills)
        descriptors = skills.descriptors()
        descriptor_map = {descriptor.name: descriptor for descriptor in descriptors}
        default_skill_display_name = _resolve_skill_display_name(descriptor_map, default_skill)

        # Deterministic fast-path for action-like email requests to avoid LLM pretending it sent email.
        if "send_email" in set(skills.names()) and _is_send_email_intent(request):
            return RouteDecision(
                skill_name="send_email",
                skill_display_name=_resolve_skill_display_name(descriptor_map, "send_email"),
                source="rule_send_email",
                reason="deterministic_email_intent",
            )

        if len(descriptors) <= 1:
            return RouteDecision(
                skill_name=default_skill,
                skill_display_name=default_skill_display_name,
                source="static",
                reason="only_registered_skill",
            )

        if not settings.skill_routing_enabled or not settings.api_key:
            return self._fallback_decision(
                default_skill=default_skill,
                default_skill_display_name=default_skill_display_name,
                reason="router_disabled_or_missing_api_key",
            )

        try:
            response = LLMProvider.with_response_messages(
                messages=_build_router_messages(user_input=request.user_input, descriptors=descriptors),
                model=settings.skill_router_model,
                enable_search=False,
                tools=_build_router_tool(descriptors),
                tool_choice={"type": "function", "function": {"name": "select_skill"}},
            )
        except Exception as exc:
            return self._fallback_decision(
                default_skill=default_skill,
                default_skill_display_name=default_skill_display_name,
                reason=f"router_exception:{exc}",
            )

        selected_skill, reason = self._extract_tool_selection(response.get("tool_calls", []))
        if not selected_skill or selected_skill not in set(skills.names()):
            return self._fallback_decision(
                default_skill=default_skill,
                default_skill_display_name=default_skill_display_name,
                reason="router_invalid_selection",
                llm_metrics=response.get("metrics", {}),
            )

        return RouteDecision(
            skill_name=selected_skill,
            skill_display_name=_resolve_skill_display_name(descriptor_map, selected_skill),
            source="llm_tool_call",
            reason=reason or "router_selected_skill",
            model=settings.skill_router_model,
            fallback_used=False,
            llm_metrics=response.get("metrics", {}),
        )

    @staticmethod
    def _extract_tool_selection(tool_calls: list[dict[str, Any]]) -> tuple[str | None, str | None]:
        for tool_call in tool_calls or []:
            function = tool_call.get("function", {})
            if function.get("name") != "select_skill":
                continue
            arguments = function.get("arguments")
            if not isinstance(arguments, dict):
                continue
            skill_name = str(arguments.get("skill_name", "") or "").strip()
            reason = str(arguments.get("reason", "") or "").strip()
            return skill_name or None, reason or None
        return None, None

    def _fallback_decision(
        self,
        *,
        default_skill: str,
        default_skill_display_name: str,
        reason: str,
        llm_metrics: dict[str, Any] | None = None,
    ) -> RouteDecision:
        return RouteDecision(
            skill_name=default_skill,
            skill_display_name=default_skill_display_name,
            source="fallback_default",
            reason=reason,
            model=None,
            fallback_used=True,
            llm_metrics=llm_metrics or {},
        )