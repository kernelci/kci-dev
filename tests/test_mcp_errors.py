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


def test_tool_errors_redirects_stdout_to_stderr(capsys):
    @tool_errors
    def noisy():
        print("chatter")
        return 1

    assert noisy() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "chatter" in captured.err


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
