from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


InputT = TypeVar("InputT", bound=ToolInput)


#TODO：
# 定义 ToolInput
# 定义 BaseTool
# 约束每个工具必须有：
# name
# description
# ainvoke(input_data)


class BaseTool(ABC, Generic[InputT]):
    """Base class for all tools with Pydantic-validated inputs."""

    name: str
    description: str

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"tool.{self.name}")

    @abstractmethod
    async def ainvoke(self, input_data: InputT) -> dict[str, Any]:
        """Execute a single tool call."""

