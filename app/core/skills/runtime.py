"""
skill runtime

职责：
1. 对接 loader 和 registry
2. 生成 skill catalog prompt
3. 应用具体 skill，返回 SkillApplyResult

创建时间：2026/5/2
开发人：zcry
"""
from __future__ import annotations

from pathlib import Path

from app.core.skills.loader import SkillLoader
from app.core.skills.registry import SkillRegistry
from app.models.dto.skill.skill import SkillApplyResult, SkillCatalogItem, SkillEntry


class SkillRuntime:
    """
    skill 运行时

    说明：
    - runtime 负责把可见 skill 转成 prompt，或把具体 skill 应用到一次 agent run
    """

    def __init__(
        self,
        *,
        loader: SkillLoader,
        registry: SkillRegistry,
    ) -> None:
        self.loader = loader
        self.registry = registry

    # ============================================================
    # Bootstrap
    # ============================================================

    def refresh(self, *, strict: bool = False, replace: bool = True) -> list[SkillEntry]:
        """
        从 loader 重新加载所有 skills，并注册进 registry

        说明：
        - strict=False：坏 skill 跳过
        - replace=True：同名 skill 用最新加载结果覆盖
        """
        entries = self.loader.load_all(strict=strict)
        self.registry.register_many(entries, replace=replace)
        return entries

    # ============================================================
    # Query
    # ============================================================

    def resolve_visible_skills(
        self,
        *,
        requester_agent: str | None,
        allowed_skills: list[str] | None,
    ) -> list[SkillEntry]:
        """
        返回当前 agent 最终可见的 skills
        """
        return self.registry.resolve_allowed_skills(
            requester_agent=requester_agent,
            allowed_skills=allowed_skills,
        )

    def build_catalog_items(
        self,
        *,
        requester_agent: str | None,
        allowed_skills: list[str] | None,
    ) -> list[SkillCatalogItem]:
        """
        把当前可见 skills 转成给模型看的轻量 catalog 条目
        """
        visible = self.resolve_visible_skills(
            requester_agent=requester_agent,
            allowed_skills=allowed_skills,
        )
        return [SkillCatalogItem.from_entry(entry) for entry in visible]

    def build_catalog_prompt(
        self,
        *,
        requester_agent: str | None,
        allowed_skills: list[str] | None,
        include_when_to_use: bool = True,
    ) -> str:
        """
        生成 <available_skills> catalog prompt

        风格上参考 OpenClaw：
        - 先给模型一个 skill 目录
        - 让模型决定是否需要读取某个 SKILL.md
        - 不把所有 skill 正文一上来全塞进 prompt
        """
        items = self.build_catalog_items(
            requester_agent=requester_agent,
            allowed_skills=allowed_skills,
        )
        if not items:
            return ""

        lines = [
            "## Skills",
            "Before replying: scan <available_skills> entries.",
            "If exactly one skill clearly applies, read its SKILL.md and follow it.",
            "If none clearly apply, do not read any skill file.",
            "",
            "<available_skills>",
        ]

        for item in items:
            lines.append("  <skill>")
            lines.append(f"    <name>{self._escape_xml(item.name)}</name>")
            lines.append(f"    <description>{self._escape_xml(item.description)}</description>")
            if include_when_to_use and item.when_to_use:
                lines.append(
                    f"    <when_to_use>{self._escape_xml(item.when_to_use)}</when_to_use>"
                )
            lines.append(f"    <location>{self._escape_xml(item.location)}</location>")
            lines.append("  </skill>")

        lines.append("</available_skills>")
        return "\n".join(lines)

    # ============================================================
    # Apply
    # ============================================================

    def apply_skill(
        self,
        skill_name: str,
        *,
        requester_agent: str | None,
        allowed_skills: list[str] | None,
    ) -> SkillApplyResult:
        """
        应用某个 skill

        流程：
        1. 从 registry 校验 skill 是否存在且当前 agent 可见
        2. 从 loader 读取 skill 正文
        3. 组装成 SkillApplyResult，供 BaseAgent 后续注入 prompt
        """
        entry = self.registry.get(
            skill_name,
            requester_agent=requester_agent,
            allowed_skills=allowed_skills,
        )
        skill_body = self.loader.read_skill_body(entry.file_path)

        prompt_injection = self._build_skill_prompt(entry, skill_body)

        return SkillApplyResult(
            skill=entry,
            prompt_injection=prompt_injection,
            allowed_tools_override=entry.allowed_tools or None,
            metadata={
                "scope": entry.scope,
                "owner_agent": entry.owner_agent,
                "file_path": entry.file_path,
                "base_dir": entry.base_dir,
            },
        )

    # ============================================================
    # Helpers
    # ============================================================

    def _build_skill_prompt(self, entry: SkillEntry, skill_body: str) -> str:
        """
        把 skill 条目和 skill 正文拼成真正注入 prompt 的内容
        """
        base_dir = Path(entry.base_dir).as_posix()

        sections = [
            f"## Active Skill: {entry.name}",
            f"Description: {entry.description}",
        ]

        if entry.when_to_use:
            sections.append(f"When to use: {entry.when_to_use}")

        sections.extend(
            [
                f"Base directory for this skill: {base_dir}",
                "",
                skill_body.strip(),
            ]
        )

        return "\n".join(section for section in sections if section is not None).strip()

    def _escape_xml(self, value: str) -> str:
        """
        给 catalog prompt 做最基本的 XML 字符转义
        """
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
