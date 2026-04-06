from __future__ import annotations

from typing import Iterator

from .contracts import AgentRequest, AgentResponse
from .registry import SkillRegistry, ToolRegistry
from .skills import DirectChatSkill


class AgentRuntime:
    """Stable scheduling shell for skill-tool architecture evolution."""

    def __init__(self) -> None:
        self.skills = SkillRegistry()
        self.tools = ToolRegistry()
        self._bootstrap_defaults()

    def _bootstrap_defaults(self) -> None:
        self.skills.register(DirectChatSkill())

    def _select_skill_name(self, request: AgentRequest) -> str:
        # Placeholder for future planner/policy routing.
        return "direct_chat"

    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        skill_name = self._select_skill_name(request)
        skill = self.skills.get(skill_name)
        yield from skill.run_stream(request)

    def run_once(self, request: AgentRequest) -> AgentResponse:
        skill_name = self._select_skill_name(request)
        skill = self.skills.get(skill_name)
        return skill.run_once(request)


_RUNTIME: AgentRuntime | None = None


def get_runtime() -> AgentRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = AgentRuntime()
    return _RUNTIME
