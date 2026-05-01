from __future__ import annotations

import asyncio
import unittest
from typing import Any
from unittest.mock import MagicMock

from pydantic import BaseModel

from app.core.observer import AgentObserver
from app.core.tools.errors import (
    ToolExecutionError,
    ToolInputError,
    ToolOutputValidationError,
    ToolTimeoutError,
    ToolUnavailableError,
    normalize_tool_error,
)
from app.core.tools.registry import ToolRegistry
from app.core.tools.result import ToolCallContext
from app.core.tools.runtime import ToolRuntime
from app.tools.base import BaseTool, ToolInput


class EchoToolInput(ToolInput):
    text: str


class OtherToolInput(ToolInput):
    value: int


class PublicEchoTool(BaseTool[EchoToolInput]):
    __module__ = "app.tools.system.fake.echo"

    name = "public_echo"
    description = "Return the provided text."
    input_model = EchoToolInput

    async def ainvoke(self, input_data: EchoToolInput) -> dict[str, Any]:
        return {"echo": input_data.text}


class PrivateEchoTool(BaseTool[EchoToolInput]):
    __module__ = "app.tools.internal.hr_agent.echo"

    name = "private_echo"
    description = "Private tool for hr_agent."
    input_model = EchoToolInput

    async def ainvoke(self, input_data: EchoToolInput) -> dict[str, Any]:
        return {"echo": input_data.text}


class FailingTool(BaseTool[EchoToolInput]):
    __module__ = "app.tools.system.fake.failing"

    name = "failing_tool"
    description = "Always fails."
    input_model = EchoToolInput

    async def ainvoke(self, input_data: EchoToolInput) -> dict[str, Any]:
        raise RuntimeError("boom")


class TimeoutThenSuccessTool(BaseTool[EchoToolInput]):
    __module__ = "app.tools.system.fake.retry"

    name = "timeout_then_success"
    description = "Fails once with timeout, then succeeds."
    input_model = EchoToolInput

    def __init__(self) -> None:
        self.calls = 0
        super().__init__()

    async def ainvoke(self, input_data: EchoToolInput) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            raise asyncio.TimeoutError()
        return {"echo": input_data.text, "attempt": self.calls}


class InvalidOutputTool(BaseTool[EchoToolInput]):
    __module__ = "app.tools.system.fake.invalid_output"

    name = "invalid_output"
    description = "Returns a non-dict output."
    input_model = EchoToolInput

    async def ainvoke(self, input_data: EchoToolInput) -> dict[str, Any]:
        return "bad-output"  # type: ignore[return-value]


class UnavailableTool(BaseTool[EchoToolInput]):
    __module__ = "app.tools.system.fake.unavailable"

    name = "unavailable_tool"
    description = "Always unavailable."
    input_model = EchoToolInput

    def is_available(self) -> bool:
        return False

    def availability_reason(self) -> str | None:
        return "missing config"

    async def ainvoke(self, input_data: EchoToolInput) -> dict[str, Any]:
        return {"ok": True}


class BaseToolTests(unittest.TestCase):
    def test_validate_input_returns_typed_model(self) -> None:
        tool = PublicEchoTool()

        parsed = tool.validate_input({"text": "hello"})

        self.assertIsInstance(parsed, EchoToolInput)
        self.assertEqual(parsed.text, "hello")

    def test_validate_input_rejects_wrong_pydantic_model(self) -> None:
        tool = PublicEchoTool()

        with self.assertRaises(ToolInputError) as ctx:
            tool.validate_input(OtherToolInput(value=1))

        self.assertEqual(ctx.exception.error_code, "tool_input_invalid")
        self.assertEqual(ctx.exception.tool_name, tool.name)

    def test_ensure_available_raises_unavailable_error(self) -> None:
        tool = UnavailableTool()

        with self.assertRaises(ToolUnavailableError) as ctx:
            tool.ensure_available()

        self.assertEqual(str(ctx.exception), "missing config")
        self.assertEqual(ctx.exception.tool_name, tool.name)


class ToolErrorTests(unittest.TestCase):
    def test_normalize_tool_error_maps_timeout(self) -> None:
        err = normalize_tool_error(asyncio.TimeoutError(), tool_name="demo")

        self.assertIsInstance(err, ToolTimeoutError)
        self.assertEqual(err.tool_name, "demo")
        self.assertEqual(err.error_code, "tool_timeout")

    def test_normalize_tool_error_maps_runtime_error(self) -> None:
        err = normalize_tool_error(RuntimeError("boom"), tool_name="demo")

        self.assertIsInstance(err, ToolExecutionError)
        self.assertEqual(err.tool_name, "demo")
        self.assertEqual(err.error_code, "tool_execution_failed")


class ToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.public_tool = PublicEchoTool()
        self.private_tool = PrivateEchoTool()
        self.registry.register_many([self.public_tool, self.private_tool])

    def test_get_allows_public_tool_with_whitelist(self) -> None:
        tool = self.registry.get(
            "public_echo",
            requester_agent="hr_agent",
            allowed_tools=["public_echo"],
        )

        self.assertIs(tool, self.public_tool)

    def test_get_blocks_private_tool_for_other_agent(self) -> None:
        with self.assertRaises(ToolUnavailableError) as ctx:
            self.registry.get(
                "private_echo",
                requester_agent="tech_agent",
                allowed_tools=["private_echo"],
            )

        self.assertIn("private to agent 'hr_agent'", str(ctx.exception))

    def test_resolve_allowed_tools_filters_by_scope_and_whitelist(self) -> None:
        tools = self.registry.resolve_allowed_tools(
            requester_agent="hr_agent",
            allowed_tools=["private_echo"],
        )

        self.assertEqual([tool.name for tool in tools], ["private_echo"])

    def test_is_visible_false_when_not_whitelisted(self) -> None:
        visible = self.registry.is_visible(
            "public_echo",
            requester_agent="hr_agent",
            allowed_tools=["private_echo"],
        )

        self.assertFalse(visible)


class ToolRuntimeAsyncTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.observer = AgentObserver()
        self.observer.record_tool_call = MagicMock()
        self.observer.record_tool_result = MagicMock()
        self.records: list[Any] = []
        self.runtime = ToolRuntime(
            observer=self.observer,
            record_sink=self.records.append,
            default_max_attempts=2,
        )

    def _context(self, tool_name: str) -> ToolCallContext:
        return ToolCallContext(
            trace_id="trace-1",
            run_id="run-1",
            tool_name=tool_name,
            agent_name="hr_agent",
            tool_call_id="call-1",
        )

    async def test_invoke_success_returns_ok_result_and_emits_record(self) -> None:
        tool = PublicEchoTool()

        result = await self.runtime.invoke(
            tool,
            {"text": "hello"},
            self._context(tool.name),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data, {"echo": "hello"})
        self.assertEqual(result.tool_name, tool.name)
        self.assertEqual(len(self.records), 1)
        self.assertTrue(self.records[0].success)
        self.observer.record_tool_call.assert_called_once()
        self.observer.record_tool_result.assert_called_once()

    async def test_invoke_input_validation_failure_returns_failed_result(self) -> None:
        tool = PublicEchoTool()

        result = await self.runtime.invoke(
            tool,
            {"missing_text": "hello"},
            self._context(tool.name),
        )

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.error_code, "tool_input_invalid")
        self.assertGreaterEqual(len(result.error.suggest), 1)
        self.assertEqual(len(self.records), 1)

    async def test_invoke_execution_failure_returns_failed_result(self) -> None:
        tool = FailingTool()

        result = await self.runtime.invoke(
            tool,
            {"text": "hello"},
            self._context(tool.name),
            max_attempts=1,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error.error_code, "tool_execution_failed")
        self.assertIn("boom", result.error.error_message)

    async def test_invoke_invalid_output_returns_output_validation_error(self) -> None:
        tool = InvalidOutputTool()

        result = await self.runtime.invoke(
            tool,
            {"text": "hello"},
            self._context(tool.name),
            max_attempts=1,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error.error_code, "tool_output_invalid")
        self.assertIn("actual_type", result.error.details)

    async def test_invoke_retries_timeout_and_then_succeeds(self) -> None:
        tool = TimeoutThenSuccessTool()

        result = await self.runtime.invoke(
            tool,
            {"text": "retry"},
            self._context(tool.name),
            max_attempts=2,
        )

        self.assertTrue(result.success)
        self.assertEqual(tool.calls, 2)
        self.assertEqual(result.metadata["attempt"], 2)


if __name__ == "__main__":
    unittest.main()
