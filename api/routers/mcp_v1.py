"""MCP server router — exposes divergence tools to AI agents via JSON-RPC 2.0."""
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any

logger = logging.getLogger("nansen.mcp_router")

router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Any = None
    method: str
    params: dict = {}


def _ok(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


@router.get("/health")
def mcp_health():
    return {"status": "ok", "protocol": "MCP/1.0", "transport": "HTTP/JSON-RPC"}


@router.post("/")
def mcp_dispatch(req: MCPRequest):
    from nansen_divergence.mcp_tools import (
        TOOL_DEFINITIONS,
        handle_get_divergence_signals,
        handle_get_signal_performance,
    )

    _HANDLERS = {
        "get_divergence_signals": handle_get_divergence_signals,
        "get_signal_performance": handle_get_signal_performance,
    }

    if req.method == "tools/list":
        return JSONResponse(_ok(req.id, {"tools": TOOL_DEFINITIONS}))

    if req.method == "tools/call":
        name = req.params.get("name")
        args = req.params.get("arguments", {})
        handler = _HANDLERS.get(name)
        if handler is None:
            return JSONResponse(
                _err(req.id, -32601, f"Unknown tool: {name}"), status_code=404
            )
        try:
            result = handler(args)
            return JSONResponse(_ok(req.id, {"content": [{"type": "json", "data": result}]}))
        except Exception as exc:
            logger.exception("MCP tool %s failed", name)
            return JSONResponse(
                _err(req.id, -32603, str(exc)), status_code=500
            )

    return JSONResponse(
        _err(req.id, -32601, f"Method not found: {req.method}"), status_code=404
    )
