from __future__ import annotations

from collections.abc import Iterable

from app.skills.base import BaseSkill


class SkillRegistry:
    """Register and resolve skills by name and agent permission."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill

    def bulk_register(self, skills: Iterable[BaseSkill]) -> None:
        for skill in skills:
            self.register(skill)

    def get(self, name: str) -> BaseSkill:
        return self._skills[name]

    def list_for_agent(self, agent_name: str) -> list[BaseSkill]:
        allowed: list[BaseSkill] = []
        for skill in self._skills.values():
            if "*" in skill.allowed_agents or agent_name in skill.allowed_agents:
                allowed.append(skill)
        return allowed

