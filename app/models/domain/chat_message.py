"""
聊天消息领域模型定义

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """聊天消息实体"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    # 内部持久化主键，便于后续映射外部存储记录
    id: str | None = Field(default=None, description="内部主键")
    message_id: str = Field(..., description="消息业务 ID")
    session_id: str = Field(..., description="所属会话 ID")
    role: Literal["AGENT", "CANDIDATE"] = Field(..., description="消息发送方角色")
    content: str = Field(..., description="消息正文")
    created_at: str = Field(..., description="消息创建时间，ISO 8601 字符串")

