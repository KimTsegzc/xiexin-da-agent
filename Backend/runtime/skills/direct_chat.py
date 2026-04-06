from __future__ import annotations

from typing import Iterator

from ... import LLMProvider
from ..contracts import AgentRequest, AgentResponse
from .base import BaseSkill


class DirectChatSkill(BaseSkill):
    """Compatibility skill that forwards directly to the existing LLM provider."""

    name = "direct_chat"

    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        yield from LLMProvider.stream(
            user_input=request.user_input,
            model=request.model,
            smooth=request.smooth,
        )

    def run_once(self, request: AgentRequest) -> AgentResponse:
        content, metrics = LLMProvider.with_metrics(
            user_input=request.user_input,
            model=request.model,
        )
        return AgentResponse(content=content, metrics=metrics)
