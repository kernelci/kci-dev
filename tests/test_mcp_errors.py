import click
import pytest

pytest.importorskip("mcp")

import requests

from kcidev.mcp.errors import ToolExecutionError, tool_errors


def test_tool_errors_passes_through_return_value():
    @tool_errors
    def ok():
        return {"a": 1}

    assert ok() == {"a": 1}


def test_tool_errors_converts_click_abort():
    @tool_errors
    def fail():
        raise click.Abort()

    with pytest.raises(ToolExecutionError):
        fail()


def test_tool_errors_converts_click_exception_with_message():
    @tool_errors
    def fail():
        raise click.ClickException("bad param")

    with pytest.raises(ToolExecutionError, match="bad param"):
        fail()


def test_tool_errors_converts_system_exit():
    @tool_errors
    def fail():
        raise SystemExit(2)

    with pytest.raises(ToolExecutionError):
        fail()


def test_tool_errors_converts_requests_error():
    @tool_errors
    def fail():
        raise requests.exceptions.ConnectionError("boom")

    with pytest.raises(ToolExecutionError, match="boom"):
        fail()


def test_tool_errors_preserves_signature():
    @tool_errors
    def f(x: int, y: str = "a"):
        return x

    import inspect

    assert list(inspect.signature(f).parameters) == ["x", "y"]


def test_tool_errors_converts_kcidev_error():
    from kcidev.api import KciDevError

    @tool_errors
    def fail():
        raise KciDevError("Dashboard build request failed: boom")

    with pytest.raises(ToolExecutionError, match="Dashboard build request failed"):
        fail()


def test_stdio_run_redirects_stdout_only_after_the_transport_takes_it(monkeypatch):
    import contextlib
    import sys
    from unittest.mock import Mock

    import anyio

    from kcidev.subcommands import mcp as mcp_cmd

    seen = {}

    @contextlib.asynccontextmanager
    async def fake_stdio_server():
        seen["at_capture"] = sys.stdout
        yield (None, None)

    monkeypatch.setattr("mcp.server.stdio.stdio_server", fake_stdio_server)

    async def fake_run(read_stream, write_stream, options):
        seen["during_run"] = sys.stdout

    server = Mock()
    server._mcp_server.run = fake_run
    server._mcp_server.create_initialization_options = Mock(return_value={})

    anyio.run(mcp_cmd._run_stdio, server)

    assert seen["at_capture"] is not sys.stderr
    assert seen["during_run"] is sys.stderr
