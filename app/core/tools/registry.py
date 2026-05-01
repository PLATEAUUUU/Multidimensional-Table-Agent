"""
tool 注册中心做白名单校验

创建时间：2026/4/29
开发人：zcry
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.core.tools.errors import ToolUnavailableError
from app.tools.base import BaseTool


ToolScope = Literal["system", "internal"]


@dataclass(frozen=True, slots=True)
class ToolRegistration:
    """
    单个工具的注册记录

    字段说明：
    - tool: 工具实例
    - scope: system / internal
    - owner_agent: 仅 internal 工具需要，表示归属哪个 agent/subagent
    - module_path: 工具实现的 Python 模块路径，方便排查来源
    """

    tool: BaseTool[Any]
    scope: ToolScope
    owner_agent: str | None
    module_path: str

    @property
    def name(self) -> str:
        return self.tool.name


class ToolRegistry:
    """
    工具注册中心

    核心职责：
    1. 注册工具实例
    2. 根据工具目录结构区分 system / internal 工具
    3. 按 agent_name + allowed_tools 白名单解析可见工具
    4. 阻止未授权 agent 调用 private/internal 工具

    目录约定：
    - app.tools.system.xxx               -> 公共工具
    - app.tools.internal.<agent>.xxx     -> 私有工具，仅 <agent> 可见
    """

    SYSTEM_PREFIX = "app.tools.system."
    INTERNAL_PREFIX = "app.tools.internal."

    def __init__(self) -> None:
        self._tools_by_name: dict[str, ToolRegistration] = {}

    # ============================================================
    # Register
    # ============================================================

    def register(
        self,
        tool: BaseTool[Any],
        *,
        scope: ToolScope | None = None,
        owner_agent: str | None = None,
        replace: bool = False,
    ) -> None:
        """
        注册单个工具

        优先级：
        1. 如果显式传入 scope / owner_agent，则使用显式值
        2. 否则从模块路径自动推断

        replace=False 时，如果出现同名工具，直接报错，避免无意覆盖
        """
        inferred_scope, inferred_owner, module_path = self._infer_registration(tool)

        final_scope = scope or inferred_scope
        final_owner = owner_agent if owner_agent is not None else inferred_owner

        if final_scope == "internal" and not final_owner:
            raise ValueError(
                f"Internal tool '{tool.name}' 必须绑定 owner_agent"
            )

        existing = self._tools_by_name.get(tool.name)
        if existing is not None and not replace:
            raise ValueError(
                f"Tool '{tool.name}' 已经注册，来源={existing.module_path}"
            )

        self._tools_by_name[tool.name] = ToolRegistration(
            tool=tool,
            scope=final_scope,
            owner_agent=final_owner,
            module_path=module_path,
        )

    def register_many(
        self,
        tools: list[BaseTool[Any]],
        *,
        replace: bool = False,
    ) -> None:
        """批量注册工具"""
        for tool in tools:
            self.register(tool, replace=replace)

    # ============================================================
    # Lookup
    # ============================================================

    def get_registration(self, tool_name: str) -> ToolRegistration:
        """获取原始注册记录；工具不存在时抛错"""
        registration = self._tools_by_name.get(tool_name)
        if registration is None:
            raise ToolUnavailableError(
                f"Tool '{tool_name}' is not registered",
                tool_name=tool_name,
            )
        return registration

    def get(
        self,
        tool_name: str,
        *,
        requester_agent: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> BaseTool[Any]:
        """
        获取某个调用方可见的工具实例

        校验顺序：
        1. 是否已注册
        2. 是否在 allowed_tools 白名单中
        3. 如果是 internal 工具，requester_agent 是否匹配 owner_agent
        """
        registration = self.get_registration(tool_name)
        self._assert_visible(
            registration,
            requester_agent=requester_agent,
            allowed_tools=allowed_tools,
        )
        return registration.tool

    def resolve_allowed_tools(
        self,
        *,
        requester_agent: str | None,
        allowed_tools: list[str] | None,
    ) -> list[BaseTool[Any]]:
        """
        解析某个 agent 当前真正可用的工具列表

        规则：
        - 如果 allowed_tools 为 None：返回该 agent 当前可见的所有工具
        - 如果 allowed_tools 非空：只返回名单中且当前 agent 有权限访问的工具
        """
        registrations = self.list_visible_registrations(requester_agent=requester_agent)

        if allowed_tools is None:
            return [registration.tool for registration in registrations]

        allow_set = {name.strip() for name in allowed_tools if name and name.strip()}
        return [
            registration.tool
            for registration in registrations
            if registration.name in allow_set
        ]

    # ============================================================
    # List
    # ============================================================

    def list_all_registrations(self) -> list[ToolRegistration]:
        """列出所有已注册工具"""
        return list(self._tools_by_name.values())

    def list_visible_registrations(
        self,
        *,
        requester_agent: str | None,
    ) -> list[ToolRegistration]:
        """
        列出某个 agent 当前理论上可见的工具

        说明：
        - system 工具对所有 agent 可见
        - internal 工具只对 owner_agent 可见
        """
        visible: list[ToolRegistration] = []

        for registration in self._tools_by_name.values():
            if registration.scope == "system":
                visible.append(registration)
                continue

            if registration.scope == "internal" and requester_agent == registration.owner_agent:
                visible.append(registration)

        return visible

    def list_tool_names(
        self,
        *,
        requester_agent: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> list[str]:
        """返回当前 agent 最终可用的工具名称列表"""
        return [
            tool.name
            for tool in self.resolve_allowed_tools(
                requester_agent=requester_agent,
                allowed_tools=allowed_tools,
            )
        ]

    # ============================================================
    # Visibility
    # ============================================================

    def is_visible(
        self,
        tool_name: str,
        *,
        requester_agent: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> bool:
        """判断某个工具对当前 agent 是否可见且可调用"""
        try:
            registration = self.get_registration(tool_name)
            self._assert_visible(
                registration,
                requester_agent=requester_agent,
                allowed_tools=allowed_tools,
            )
            return True
        except ToolUnavailableError:
            return False

    def _assert_visible(
        self,
        registration: ToolRegistration,
        *,
        requester_agent: str | None,
        allowed_tools: list[str] | None,
    ) -> None:
        """
        统一执行可见性校验
        抛出 ToolUnavailableError，而不是返回 False
        """
        tool_name = registration.name

        if allowed_tools is not None:
            allow_set = {name.strip() for name in allowed_tools if name and name.strip()}
            if tool_name not in allow_set:
                raise ToolUnavailableError(
                    f"Tool '{tool_name}' is not allowed for agent '{requester_agent or 'unknown'}'",
                    tool_name=tool_name,
                    details={
                        "requester_agent": requester_agent,
                        "allowed_tools": sorted(allow_set),
                    },
                )

        if registration.scope == "system":
            return

        if registration.scope == "internal":
            if not requester_agent:
                raise ToolUnavailableError(
                    f"Internal tool '{tool_name}' requires requester_agent",
                    tool_name=tool_name,
                    details={
                        "scope": registration.scope,
                        "owner_agent": registration.owner_agent,
                    },
                )

            if requester_agent != registration.owner_agent:
                raise ToolUnavailableError(
                    f"Internal tool '{tool_name}' is private to agent '{registration.owner_agent}'",
                    tool_name=tool_name,
                    details={
                        "scope": registration.scope,
                        "owner_agent": registration.owner_agent,
                        "requester_agent": requester_agent,
                    },
                )

            return

        raise ToolUnavailableError(
            f"Tool '{tool_name}' has unsupported scope '{registration.scope}'",
            tool_name=tool_name,
        )

    # ============================================================
    # Infer from module path
    # ============================================================

    def _infer_registration(
        self,
        tool: BaseTool[Any],
    ) -> tuple[ToolScope, str | None, str]:
        """
        从工具类模块路径推断注册信息
        """
        module_path = tool.__class__.__module__

        if module_path.startswith(self.SYSTEM_PREFIX):
            return "system", None, module_path

        if module_path.startswith(self.INTERNAL_PREFIX):
            suffix = module_path[len(self.INTERNAL_PREFIX):]
            owner_agent = suffix.split(".", 1)[0].strip()
            if not owner_agent:
                raise ValueError(
                    f"无法从模块路径推断 internal 工具 owner_agent: {module_path}"
                )
            return "internal", owner_agent, module_path

        raise ValueError(
            f"Tool '{tool.name}' 的模块路径不符合约定：{module_path}。"
            "请将工具放在 app.tools.system.* 或 app.tools.internal.<agent>.* 下，"
            "或在 register(...) 时显式传 scope / owner_agent。"
        )
