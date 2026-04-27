"""
发送聊天消息请求 DTO 定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SendMessageRequest(BaseModel):
    """发送候选人消息请求。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    # 聊天内容至少需要一个字符，避免空消息进入流程。
    content: str = Field(..., min_length=1, description="候选人发送的消息内容。")

