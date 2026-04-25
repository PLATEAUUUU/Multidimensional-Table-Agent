from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Iterator, Mapping
from copy import deepcopy
from typing import Any

from app.core.observer import AgentObserver
from app.tools.mcp.feishu_tool import FeishuTool

try:
    from langgraph.checkpoint.base import (
        BaseCheckpointSaver,
        ChannelVersions,
        Checkpoint,
        CheckpointMetadata,
        CheckpointTuple,
    )
except Exception:  # pragma: no cover - fallback for scaffold-only environments
    BaseCheckpointSaver = object  # type: ignore[assignment,misc]
    ChannelVersions = dict[str, Any]  # type: ignore[misc,assignment]
    Checkpoint = dict[str, Any]  # type: ignore[misc,assignment]
    CheckpointMetadata = dict[str, Any]  # type: ignore[misc,assignment]
    CheckpointTuple = tuple  # type: ignore[misc,assignment]


class BitableCheckpointer(BaseCheckpointSaver):  # type: ignore[misc]
    """
    In-memory checkpoint saver with Feishu persistence hooks.

    Temporary runtime state lives in memory while durable snapshots are
    delegated to the Feishu tool placeholder.
    """

    def __init__(self, observer: AgentObserver, feishu_tool: FeishuTool) -> None:
        self.observer = observer
        self.feishu_tool = feishu_tool
        self.logger = logging.getLogger(self.__class__.__name__)
        self._store: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _thread_id(config: Mapping[str, Any] | None) -> str:
        configurable = dict((config or {}).get("configurable", {}))
        return str(
            configurable.get("thread_id")
            or configurable.get("session_id")
            or "default-session"
        )

    def get_tuple(self, config: Mapping[str, Any]) -> CheckpointTuple | None:
        thread_id = self._thread_id(config)
        stored = self._store.get(thread_id)
        if not stored:
            return None
        self.logger.info("Loaded checkpoint thread_id=%s", thread_id)
        return (
            {"configurable": {"thread_id": thread_id}},
            deepcopy(stored["checkpoint"]),
            deepcopy(stored["metadata"]),
            None,
            [],
        )

    async def aget_tuple(self, config: Mapping[str, Any]) -> CheckpointTuple | None:
        return self.get_tuple(config)

    def put(
        self,
        config: Mapping[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> Mapping[str, Any]:
        thread_id = self._thread_id(config)
        self._store[thread_id] = {
            "checkpoint": deepcopy(checkpoint),
            "metadata": deepcopy(metadata),
            "new_versions": deepcopy(new_versions),
        }
        self.observer.record_event("checkpoint_saved", {"thread_id": thread_id})
        self.logger.info("Stored checkpoint thread_id=%s", thread_id)
        return {"configurable": {"thread_id": thread_id}}

    async def aput(
        self,
        config: Mapping[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> Mapping[str, Any]:
        result = self.put(config, checkpoint, metadata, new_versions)
        thread_id = self._thread_id(config)
        await self.feishu_tool.atomic_sync_session(
            session_id=thread_id,
            state_payload={
                "checkpoint": json.loads(json.dumps(checkpoint, default=str)),
                "metadata": json.loads(json.dumps(metadata, default=str)),
            },
        )
        return result

    def list(
        self,
        config: Mapping[str, Any] | None,
        *,
        filter: Mapping[str, Any] | None = None,
        before: Mapping[str, Any] | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        del filter, before
        items = list(self._store.items())
        if limit is not None:
            items = items[:limit]
        for thread_id, stored in items:
            yield (
                {"configurable": {"thread_id": thread_id}},
                deepcopy(stored["checkpoint"]),
                deepcopy(stored["metadata"]),
                None,
                [],
            )

    async def alist(
        self,
        config: Mapping[str, Any] | None,
        *,
        filter: Mapping[str, Any] | None = None,
        before: Mapping[str, Any] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    def put_writes(self, config: Mapping[str, Any], writes: list[tuple[str, Any]], task_id: str) -> None:
        thread_id = self._thread_id(config)
        self.logger.info(
            "put_writes thread_id=%s task_id=%s write_count=%s",
            thread_id,
            task_id,
            len(writes),
        )

    async def aput_writes(
        self,
        config: Mapping[str, Any],
        writes: list[tuple[str, Any]],
        task_id: str,
    ) -> None:
        self.put_writes(config, writes, task_id)

    def delete_thread(self, thread_id: str) -> None:
        self._store.pop(thread_id, None)
        self.logger.info("Deleted checkpoint thread_id=%s", thread_id)

    async def adelete_thread(self, thread_id: str) -> None:
        self.delete_thread(thread_id)

    def get_next_version(self, current: Any, channel: str) -> str:
        del channel
        if current is None:
            return "1"
        try:
            return str(int(current) + 1)
        except (TypeError, ValueError):
            return "1"
