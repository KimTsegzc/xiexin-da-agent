from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from ..contracts import AgentRequest, AgentResponse


class BaseSkill(ABC):
    name: str

    @abstractmethod
    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        raise NotImplementedError

    @abstractmethod
    def run_once(self, request: AgentRequest) -> AgentResponse:
        raise NotImplementedError
