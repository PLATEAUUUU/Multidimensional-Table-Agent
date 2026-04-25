from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.agents.graph import build_interview_graph
from app.agents.state import build_initial_state
from app.config import get_settings
from app.core.observer import AgentObserver, TraceContextMiddleware, configure_logging
from app.tools.mcp.feishu_tool import FeishuTool


settings = get_settings()
configure_logging(settings.log_level)

observer = AgentObserver()
feishu_tool = FeishuTool(settings=settings)
interview_graph = build_interview_graph(settings=settings, observer=observer, feishu_tool=feishu_tool)

app = FastAPI(title=settings.app_name)
app.add_middleware(TraceContextMiddleware, observer=observer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("app.main")


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get(f"{settings.api_prefix}/sessions/{{session_id}}")
async def get_session(session_id: str, request: Request) -> dict[str, Any]:
    trace_id = getattr(request.state, "trace_id", observer.new_trace_id())
    initial_state = build_initial_state(session_id=session_id, candidate_id="placeholder-candidate", trace_id=trace_id)
    await feishu_tool.atomic_sync_session(session_id=session_id, state_payload=initial_state)
    return initial_state


@app.post(f"{settings.api_prefix}/sessions/{{session_id}}/invoke")
async def invoke_session(session_id: str, request: Request) -> dict[str, Any]:
    """
    Placeholder graph entrypoint.

    Concrete business flow execution should be added after tool and prompt
    implementations are finalized.
    """

    trace_id = getattr(request.state, "trace_id", observer.new_trace_id())
    state = build_initial_state(session_id=session_id, candidate_id="placeholder-candidate", trace_id=trace_id)
    await feishu_tool.atomic_sync_session(session_id=session_id, state_payload=state)
    logger.info("invoke_session session_id=%s trace_id=%s", session_id, trace_id)
    return {
        "session_id": session_id,
        "trace_id": trace_id,
        "status": "scaffold_ready",
        "graph_compiled": interview_graph is not None,
    }


@app.websocket("/ws/interview/{session_id}")
async def interview_updates(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    trace_id = observer.new_trace_id()
    state = build_initial_state(session_id=session_id, candidate_id="placeholder-candidate", trace_id=trace_id)
    await websocket.send_json({"type": "session_state", "payload": state})

    try:
        while True:
            incoming = await websocket.receive_json()
            if incoming.get("type") == "ping":
                await websocket.send_json({"type": "pong", "trace_id": trace_id})
                continue
            await asyncio.sleep(0)
            await websocket.send_json(
                {
                    "type": "session_state",
                    "payload": state,
                }
            )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected session_id=%s", session_id)
