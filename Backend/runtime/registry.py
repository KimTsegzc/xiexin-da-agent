from __future__ import annotations

from collections.abc import Iterable

from .skills.base import BaseSkill


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise KeyError(f"Skill {name!r} is not registered") from exc

    def names(self) -> Iterable[str]:
        return self._skills.keys()


class ToolRegistry:
    """Placeholder for upcoming tool runtime registration."""

    def __init__(self) -> None:
        self._tools: dict[str, object] = {}

    def register(self, name: str, tool: object) -> None:
        self._tools[name] = tool

    def get(self, name: str) -> object:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool {name!r} is not registered") from exc
