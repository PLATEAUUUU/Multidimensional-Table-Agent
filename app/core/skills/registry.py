"""
按 system/internal 注册和过滤 skills

创建时间：2026/5/2
开发人：zcry
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.dto.skill.skill import SkillEntry, SkillScope


class SkillRegistryError(Exception):
    """skill 注册中心基类异常"""


class SkillUnavailableError(SkillRegistryError):
    """skill 不存在或当前 agent 无权访问"""


@dataclass(frozen=True, slots=True)
class SkillRegistration:
    """
    单个 skill 的注册记录

    字段说明：
    - entry: 解析完成的 skill 条目
    - scope: system / internal
    - owner_agent: internal skill 的归属 agent
    """

    entry: SkillEntry
    scope: SkillScope
    owner_agent: str | None

    @property
    def name(self) -> str:
        return self.entry.name


class SkillRegistry:
    """
    skill 注册中心

    核心职责：
    1. 注册 SkillEntry
    2. 区分 system / internal skills
    3. 按 requester_agent + allowed_skills 解析最终可见 skills
    4. 阻止未授权 agent 访问 internal skill
    """

    def __init__(self) -> None:
        self._skills_by_name: dict[str, SkillRegistration] = {}

    # ============================================================
    # Register
    # ============================================================

    def register(
        self,
        entry: SkillEntry,
        *,
        replace: bool = False,
    ) -> None:
        """
        注册单个 skill
        replace=False 时，如果出现同名 skill，直接报错，避免无意覆盖
        """
        existing = self._skills_by_name.get(entry.name)
        if existing is not None and not replace:
            raise ValueError(
                f"Skill '{entry.name}' 已经注册，来源={existing.entry.file_path}"
            )

        if entry.scope == "internal" and not entry.owner_agent:
            raise ValueError(
                f"Internal skill '{entry.name}' 必须绑定 owner_agent"
            )

        if entry.scope == "system" and entry.owner_agent is not None:
            raise ValueError(
                f"System skill '{entry.name}' 不应设置 owner_agent"
            )

        self._skills_by_name[entry.name] = SkillRegistration(
            entry=entry,
            scope=entry.scope,
            owner_agent=entry.owner_agent,
        )

    def register_many(
        self,
        entries: list[SkillEntry],
        *,
        replace: bool = False,
    ) -> None:
        """批量注册 skills"""
        for entry in entries:
            self.register(entry, replace=replace)

    # ============================================================
    # Lookup
    # ============================================================

    def get_registration(self, skill_name: str) -> SkillRegistration:
        """获取原始注册记录；skill 不存在时抛错"""
        registration = self._skills_by_name.get(skill_name)
        if registration is None:
            raise SkillUnavailableError(
                f"Skill '{skill_name}' is not registered"
            )
        return registration

    def get(
        self,
        skill_name: str,
        *,
        requester_agent: str | None = None,
        allowed_skills: list[str] | None = None,
    ) -> SkillEntry:
        """
        获取某个调用方可见的 skill

        校验顺序：
        1. 是否已注册
        2. 是否在 allowed_skills 白名单中
        3. 如果是 internal skill，requester_agent 是否匹配 owner_agent
        """
        registration = self.get_registration(skill_name)
        self._assert_visible(
            registration,
            requester_agent=requester_agent,
            allowed_skills=allowed_skills,
        )
        return registration.entry

    def resolve_allowed_skills(
        self,
        *,
        requester_agent: str | None,
        allowed_skills: list[str] | None,
    ) -> list[SkillEntry]:
        """
        解析某个 agent 当前真正可用的 skill 列表

        规则：
        - 如果 allowed_skills 为 None：返回该 agent 当前可见的所有 skills
        - 如果 allowed_skills 非空：只返回名单中且当前 agent 有权限访问的 skills
        """
        registrations = self.list_visible_registrations(requester_agent=requester_agent)

        if allowed_skills is None:
            return [registration.entry for registration in registrations]

        allow_set = {name.strip() for name in allowed_skills if name and name.strip()}
        return [
            registration.entry
            for registration in registrations
            if registration.name in allow_set
        ]

    # ============================================================
    # List
    # ============================================================

    def list_all_registrations(self) -> list[SkillRegistration]:
        """列出所有已注册 skills。"""
        return list(self._skills_by_name.values())

    def list_visible_registrations(
        self,
        *,
        requester_agent: str | None,
    ) -> list[SkillRegistration]:
        """
        列出某个 agent 当前理论上可见的 skills

        说明：
        - system skill 对所有 agent 可见
        - internal skill 只对 owner_agent 可见
        """
        visible: list[SkillRegistration] = []

        for registration in self._skills_by_name.values():
            if registration.scope == "system":
                visible.append(registration)
                continue

            if registration.scope == "internal" and requester_agent == registration.owner_agent:
                visible.append(registration)

        return visible

    def list_skill_names(
        self,
        *,
        requester_agent: str | None = None,
        allowed_skills: list[str] | None = None,
    ) -> list[str]:
        """返回当前 agent 最终可用的 skill 名称列表"""
        return [
            entry.name
            for entry in self.resolve_allowed_skills(
                requester_agent=requester_agent,
                allowed_skills=allowed_skills,
            )
        ]

    # ============================================================
    # Visibility
    # ============================================================

    def is_visible(
        self,
        skill_name: str,
        *,
        requester_agent: str | None = None,
        allowed_skills: list[str] | None = None,
    ) -> bool:
        """判断某个 skill 对当前 agent 是否可见且可调用"""
        try:
            registration = self.get_registration(skill_name)
            self._assert_visible(
                registration,
                requester_agent=requester_agent,
                allowed_skills=allowed_skills,
            )
            return True
        except SkillUnavailableError:
            return False

    def _assert_visible(
        self,
        registration: SkillRegistration,
        *,
        requester_agent: str | None,
        allowed_skills: list[str] | None,
    ) -> None:
        """
        统一执行可见性校验

        抛出 SkillUnavailableError，而不是返回 False，
        这样 BaseAgent / SkillRuntime 更容易统一收口。
        """
        skill_name = registration.name

        if allowed_skills is not None:
            allow_set = {name.strip() for name in allowed_skills if name and name.strip()}
            if skill_name not in allow_set:
                raise SkillUnavailableError(
                    f"Skill '{skill_name}' is not allowed for agent '{requester_agent or 'unknown'}'"
                )

        if registration.scope == "system":
            return

        if registration.scope == "internal":
            if not requester_agent:
                raise SkillUnavailableError(
                    f"Internal skill '{skill_name}' requires requester_agent"
                )

            if requester_agent != registration.owner_agent:
                raise SkillUnavailableError(
                    f"Internal skill '{skill_name}' is private to agent '{registration.owner_agent}'"
                )

            return

        raise SkillUnavailableError(
            f"Skill '{skill_name}' has unsupported scope '{registration.scope}'"
        )
