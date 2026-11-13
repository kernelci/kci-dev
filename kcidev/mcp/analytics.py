"""Payload-free JSON events for MCP usage and latency analytics."""

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from logging.handlers import WatchedFileHandler

import anyio
from mcp.types import CallToolRequest

logger = logging.getLogger("kcidev.mcp.analytics")


def _report_io_failure():
    # Avoid logging recursively or exposing the record, path or exception text.
    try:
        sys.stderr.write("kci-dev: cannot write MCP analytics log\n")
    except (OSError, ValueError):
        pass


class _SafeLoggingErrors:
    def handleError(self, record):
        _report_io_failure()


class _AnalyticsFileHandler(_SafeLoggingErrors, WatchedFileHandler):
    pass


class _AnalyticsStreamHandler(_SafeLoggingErrors, logging.StreamHandler):
    pass


def log_event(event, **fields):
    try:
        logger.info(
            json.dumps(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": event,
                    **fields,
                }
            )
        )
    except OSError:
        # WatchedFileHandler can raise before StreamHandler.emit handles errors.
        _report_io_failure()


@contextmanager
def analytics_logging(path=None):
    """Configure only our analytics logger; keep stdout free for MCP."""
    handler = (
        _AnalyticsFileHandler(path, encoding="utf-8")
        if path is not None
        else _AnalyticsStreamHandler()
    )
    previous = logger.handlers[:], logger.level, logger.propagate
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        yield
    finally:
        logger.handlers, previous_level, logger.propagate = previous
        logger.setLevel(previous_level)
        try:
            handler.close()
        except OSError:
            _report_io_failure()


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
            # tool_offload shields its worker until completion. Observe any
            # cancellation that arrived while the blocking tool was running.
            await anyio.lowlevel.checkpoint_if_cancelled()
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
