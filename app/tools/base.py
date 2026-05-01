"""
tool 基类

创建时间：2026/4/29
开发人：zcry
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.tools.errors import ToolInputError, ToolUnavailableError


class ToolInput(BaseModel):
    """
    所有工具输入模型的基类

    约定：
    - 默认禁止额外字段，避免模型随意透传脏参数
    - 每个具体工具都应该定义自己的 InputModel 并继承它
    """

    model_config = ConfigDict(extra="forbid")


InputT = TypeVar("InputT", bound=ToolInput)


class BaseTool(ABC, Generic[InputT]):
    """
    工具基类。

    职责边界：
    1. 声明工具元信息（name / description / input_model）
    2. 提供基础输入校验能力
    3. 提供基础可用性检查能力
    4. 定义统一的异步执行接口 ainvoke(...)
    """

    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    input_model: ClassVar[type[InputT]]

    def __init__(self) -> None:
        self._validate_tool_definition()
        self.logger = logging.getLogger(f"tool.{self.name}")

    def _validate_tool_definition(self) -> None:
        """
        校验子类是否正确声明了工具定义

        这个检查尽量在实例化时就失败，避免等到 runtime 调用阶段才暴露定义错误
        """
        if not self.name or not isinstance(self.name, str):
            raise ValueError(f"{self.__class__.__name__} 必须定义 name: str")

        if not self.description or not isinstance(self.description, str):
            raise ValueError(f"{self.__class__.__name__} 必须定义 description: str")

        input_model = getattr(self.__class__, "input_model", None)
        if input_model is None:
            raise ValueError(f"{self.__class__.__name__} 必须定义 input_model")

        if not isinstance(input_model, type):
            raise ValueError(f"{self.__class__.__name__}.input_model 必须是一个类")

        if not issubclass(input_model, ToolInput):
            raise ValueError(
                f"{self.__class__.__name__}.input_model 必须继承 ToolInput"
            )

    def is_available(self) -> bool:
        """
        当前工具是否可用

        默认返回 True
        具体工具如果依赖环境变量、外部客户端、配置开关，可以重写这个方法
        """
        return True

    def availability_reason(self) -> str | None:
        """
        当前工具不可用时的原因说明

        默认无说明
        具体工具可以重写，配合 ensure_available() 给出更明确的错误信息
        """
        return None

    def ensure_available(self) -> None:
        """
        在执行前检查工具是否可用

        如果工具不可用，抛出 ToolUnavailableError
        """
        if self.is_available():
            return

        reason = self.availability_reason() or f"Tool '{self.name}' is unavailable"
        raise ToolUnavailableError(
            reason,
            tool_name=self.name,
        )

    def validate_input(
        self,
        raw_args: Mapping[str, Any] | BaseModel,
    ) -> InputT:
        """
        用工具自带的 input_model 校验输入
        """
        input_model = self.__class__.input_model

        if isinstance(raw_args, input_model):
            return raw_args

        if isinstance(raw_args, BaseModel):
            raise ToolInputError(
                f"Tool '{self.name}' received unexpected input model '{raw_args.__class__.__name__}'",
                tool_name=self.name,
                details={
                    "expected_input_model": input_model.__name__,
                    "actual_input_model": raw_args.__class__.__name__,
                },
            )

        try:
            return input_model.model_validate(dict(raw_args))
        except ValidationError as exc:
            raise ToolInputError(
                f"Tool '{self.name}' input validation failed",
                tool_name=self.name,
                details={"errors": exc.errors()},
                cause=exc,
            ) from exc

    @abstractmethod
    async def ainvoke(self, input_data: InputT) -> dict[str, Any]:
        """
        执行一次工具调用

        约定：
        - 入参必须是已经通过 input_model 校验后的结构化对象
        - 返回值必须是 dict[str, Any]
        - 如果执行失败，抛出异常，由 runtime.py 统一归一化和包装
        """

