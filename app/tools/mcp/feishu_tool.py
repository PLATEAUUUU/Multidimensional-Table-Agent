from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import Field

from app.config import AppSettings
from app.tools.base import BaseTool, ToolInput


class FeishuSessionInput(ToolInput):
    session_id: str = Field(..., description="Interview session id.")


class FeishuSessionWriteInput(FeishuSessionInput):
    state_payload: dict[str, Any] = Field(..., description="Serialized session state payload.")


class FeishuTool(BaseTool[FeishuSessionInput]):
    """
    Feishu bitable adapter placeholder.

    All persistent state should be synchronized through this class before
    transitions between graph nodes.
    """

    name = "feishu_bitable"
    description = "Placeholder wrapper for Feishu bitable session storage."

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.base_url = settings.feishu_base_url.rstrip("/")

    async def ainvoke(self, input_data: FeishuSessionInput) -> dict[str, Any]:
        return await self.read_session_state(input_data.session_id)

    async def read_session_state(self, session_id: str) -> dict[str, Any]:
        self.logger.info(
            "read_session_state session_id=%s table=%s",
            session_id,
            self.settings.feishu_table_session,
        )
        return {
            "session_id": session_id,
            "state_payload": None,
            "status": "placeholder",
        }

    async def write_session_state(self, session_id: str, state_payload: dict[str, Any]) -> dict[str, Any]:
        self.logger.info(
            "write_session_state session_id=%s table=%s payload_keys=%s",
            session_id,
            self.settings.feishu_table_session,
            list(state_payload.keys()),
        )
        return {
            "session_id": session_id,
            "record_id": None,
            "status": "pending_feishu_implementation",
        }

    async def atomic_sync_session(self, session_id: str, state_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Placeholder for FEISHU_TABLE_SESSION atomic synchronization.

        Replace this with an idempotent read-modify-write sequence once
        Feishu API details and record schema are finalized.
        """

        serialized_payload = json.dumps(state_payload, ensure_ascii=True)
        self.logger.debug("atomic_sync_session payload=%s", serialized_payload)
        return await self.write_session_state(session_id, state_payload)

    async def get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

