"""
Skill DTO 定义

职责：
1. 定义 skill frontmatter 结构
2. 定义 skill 注册条目 SkillEntry
3. 定义给模型看的 skill catalog 条目
4. 定义 skill 应用结果 SkillApplyResult

创建时间：2026/5/2
开发人：zcry
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SkillScope = Literal["system", "internal"]
SkillSource = Literal["filesystem"]


class SkillFrontmatter(BaseModel):
    """
    从 SKILL.md frontmatter 解析出的结构
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    name: str = Field(..., description="skill 名称")
    description: str = Field(..., description="skill 描述")
    when_to_use: str | None = Field(default=None, description="建议使用场景")
    allowed_tools: list[str] = Field(default_factory=list, description="skill 允许使用的工具")
    user_invocable: bool = Field(default=True, description="是否允许用户显式调用")
    disable_model_invocation: bool = Field(
        default=False,
        description="是否禁止模型自主触发该 skill",
    )

    @field_validator("name", "description", "when_to_use", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> Any:
        if value is None:
            return value
        text = str(value).strip()
        return text or None

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def normalize_allowed_tools(cls, value: Any) -> list[str]:
        if value is None:
            return []

        if isinstance(value, str):
            items = [part.strip() for part in value.split(",")]
        elif isinstance(value, list):
            items = [str(item).strip() for item in value]
        else:
            raise TypeError("allowed_tools must be a list[str] or comma-separated string")

        deduped: list[str] = []
        seen: set[str] = set()
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    @model_validator(mode="after")
    def validate_required_fields(self) -> "SkillFrontmatter":
        if not self.name:
            raise ValueError("skill frontmatter.name 不能为空")
        if not self.description:
            raise ValueError("skill frontmatter.description 不能为空")
        return self


class SkillEntry(BaseModel):
    """
    skill 注册条目

    说明：
    - 这是 loader / registry 的核心数据结构
    - 表示一个已经被发现并解析好的 skill
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    name: str = Field(..., description="skill 名称")
    description: str = Field(..., description="skill 描述")
    when_to_use: str | None = Field(default=None, description="建议使用场景")
    allowed_tools: list[str] = Field(default_factory=list, description="skill 允许使用的工具")
    user_invocable: bool = Field(default=True, description="是否允许用户显式调用")
    disable_model_invocation: bool = Field(
        default=False,
        description="是否禁止模型自主触发该 skill",
    )

    file_path: str = Field(..., description="SKILL.md 文件路径")
    base_dir: str = Field(..., description="skill 根目录")
    scope: SkillScope = Field(..., description="skill 作用域")
    source: SkillSource = Field(default="filesystem", description="skill 来源")
    owner_agent: str | None = Field(default=None, description="internal skill 所属 agent")

    @field_validator("name", "description", "when_to_use", "file_path", "base_dir", mode="before")
    @classmethod
    def normalize_entry_text(cls, value: Any) -> Any:
        if value is None:
            return value
        text = str(value).strip()
        return text or None

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def normalize_entry_allowed_tools(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            items = [str(item).strip() for item in value]
        else:
            raise TypeError("allowed_tools must be a list[str]")

        deduped: list[str] = []
        seen: set[str] = set()
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    @model_validator(mode="after")
    def validate_scope(self) -> "SkillEntry":
        if self.scope == "internal" and not self.owner_agent:
            raise ValueError("internal skill 必须提供 owner_agent")
        if self.scope == "system" and self.owner_agent is not None:
            raise ValueError("system skill 不应设置 owner_agent")
        return self

    @classmethod
    def from_frontmatter(
        cls,
        *,
        frontmatter: SkillFrontmatter,
        file_path: str,
        base_dir: str,
        scope: SkillScope,
        owner_agent: str | None = None,
        source: SkillSource = "filesystem",
    ) -> "SkillEntry":
        """
        从解析后的 frontmatter 构造 SkillEntry
        """
        return cls(
            name=frontmatter.name,
            description=frontmatter.description,
            when_to_use=frontmatter.when_to_use,
            allowed_tools=frontmatter.allowed_tools,
            user_invocable=frontmatter.user_invocable,
            disable_model_invocation=frontmatter.disable_model_invocation,
            file_path=file_path,
            base_dir=base_dir,
            scope=scope,
            source=source,
            owner_agent=owner_agent,
        )


class SkillCatalogItem(BaseModel):
    """
    给模型看的 skill catalog 条目

    说明：
    - 这是 runtime 生成 <available_skills> 时最适合使用的轻量结构
    - 不直接暴露所有内部字段
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    name: str = Field(..., description="skill 名称")
    description: str = Field(..., description="skill 描述")
    when_to_use: str | None = Field(default=None, description="建议使用场景")
    location: str = Field(..., description="SKILL.md 位置")

    @classmethod
    def from_entry(cls, entry: SkillEntry) -> "SkillCatalogItem":
        return cls(
            name=entry.name,
            description=entry.description,
            when_to_use=entry.when_to_use,
            location=entry.file_path,
        )


class SkillApplyResult(BaseModel):
    """
    一次 skill 应用后的结果

    说明：
    - runtime 选中某个 skill 后，返回这个结构
    - BaseAgent 后续只需要消费这个结果，不需要关心 loader/registry 细节
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    skill: SkillEntry = Field(..., description="已应用的 skill")
    prompt_injection: str = Field(..., description="需要注入到本次 agent prompt 的 skill 内容")
    allowed_tools_override: list[str] | None = Field(
        default=None,
        description="skill 生效后覆盖的允许工具列表",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元信息")
