"""Payload-free JSON events for MCP usage and latency analytics."""

import json
import logging
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import anyio
from mcp.types import CallToolRequest

logger = logging.getLogger("kcidev.mcp.analytics")


def log_event(event, **fields):
    logger.info(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                **fields,
            }
        )
    )


@contextmanager
def analytics_logging(path=None):
    """Configure only our analytics logger; keep stdout free for MCP."""
    handler = (
        logging.FileHandler(path, encoding="utf-8")
        if path is not None
        else logging.StreamHandler()
    )
    previous = logger.handlers[:], logger.level, logger.propagate
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        yield
    finally:
        logger.handlers, logger.level, logger.propagate = previous
        handler.close()


def instrument_tools(server, instance):
    # Wrap the protocol handler so schema errors and unknown tools count too.
    # FastMCP converts tool exceptions to isError results inside this handler.
    handlers = server._mcp_server.request_handlers
    call_tool = handlers[CallToolRequest]

    async def logged_call(request):
        started = time.perf_counter()
        call_id = uuid.uuid4().hex
        outcome = "error"
        try:
            result = await call_tool(request)
            outcome = "error" if result.root.isError else "success"
            return result
        except anyio.get_cancelled_exc_class():
            outcome = "cancelled"
            raise
        finally:
            log_event(
                "tool_call",
                call_id=call_id,
                tool=request.params.name,
                instance=instance,
                outcome=outcome,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
            )

    handlers[CallToolRequest] = logged_call
