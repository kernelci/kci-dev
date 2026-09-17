#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import functools

import anyio.to_thread


def tool_offload(func):
    """Run a blocking MCP tool in a worker thread.

    FastMCP awaits async tools but calls sync ones inline on the event
    loop, so a tool doing blocking I/O stalls every other request on the
    server until it returns. Registering an async wrapper instead keeps
    the loop free. The worker inherits a copy of the caller's context,
    so tools reading contextvars still see what the caller set.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await anyio.to_thread.run_sync(functools.partial(func, *args, **kwargs))

    return wrapper
