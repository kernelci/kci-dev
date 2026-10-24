import json
from unittest.mock import Mock

import pytest

pytest.importorskip("mcp")

import anyio
from click.testing import CliRunner
from mcp.shared.memory import (
    create_connected_server_and_client_session as client_session,
)

from kcidev.mcp import create_server
from kcidev.mcp.analytics import analytics_logging, log_event
from kcidev.subcommands import mcp


def test_tool_analytics_covers_success_failure_and_validation(tmp_path):
    server = create_server()

    @server.tool()
    async def example(value: int):
        if value == 0:
            raise ValueError("private exception text")
        return "private result text"

    path = tmp_path / "analytics.jsonl"

    async def run():
        async with client_session(server._mcp_server) as session:
            for name, arguments, error in [
                ("example", {"value": 1}, False),
                ("example", {"value": 0}, True),
                ("example", {"value": "private argument text"}, True),
                ("missing_tool", {}, True),
            ]:
                result = await session.call_tool(name, arguments)
                assert result.isError is error

    with analytics_logging(path):
        anyio.run(run)

    text = path.read_text()
    assert "private" not in text
    events = [json.loads(line) for line in text.splitlines()]
    assert len(events) == 4
    assert [event["outcome"] for event in events] == [
        "success",
        "error",
        "error",
        "error",
    ]
    assert len({event["call_id"] for event in events}) == 4
    for event in events:
        assert event["event"] == "tool_call"
        assert event["duration_ms"] >= 0
        assert event["timestamp"].endswith("+00:00")
        assert "instance" in event


def test_logging_appends_without_duplicate_handlers(tmp_path):
    path = tmp_path / "analytics.jsonl"
    for _ in range(2):
        with analytics_logging(path):
            log_event("server_start")
    assert len(path.read_text().splitlines()) == 2


def test_default_logging_uses_stderr(capsys):
    with analytics_logging():
        log_event("server_start")
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["event"] == "server_start"


@pytest.mark.parametrize("transport", ["stdio", "http"])
def test_cli_lifecycle_logging(tmp_path, monkeypatch, transport):
    server = Mock()
    monkeypatch.setattr("kcidev.mcp.create_server", Mock(return_value=server))

    async def run_stdio(server):
        pass

    monkeypatch.setattr(mcp, "_run_stdio", run_stdio)
    path = tmp_path / "analytics.jsonl"
    result = CliRunner().invoke(
        mcp.mcp,
        ["--transport", transport, "--log-file", str(path)],
        obj={},
    )
    assert result.exit_code == 0, result.output
    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert [event["event"] for event in events] == ["server_start", "server_stop"]
    assert all(event["transport"] == transport for event in events)


def test_cli_reports_unwritable_log_path(tmp_path):
    result = CliRunner().invoke(
        mcp.mcp, ["--log-file", str(tmp_path / "missing" / "log")], obj={}
    )
    assert result.exit_code == 1
    assert "Cannot open analytics log" in result.output


def test_cancelled_tool_is_logged(tmp_path):
    server = create_server()

    @server.tool()
    async def waiting():
        await anyio.sleep_forever()

    path = tmp_path / "analytics.jsonl"

    async def run():
        from mcp.types import CallToolRequest, CallToolRequestParams

        handler = server._mcp_server.request_handlers[CallToolRequest]
        with anyio.move_on_after(0.05) as scope:
            await handler(CallToolRequest(params=CallToolRequestParams(name="waiting")))
        assert scope.cancel_called

    with analytics_logging(path):
        anyio.run(run)
    event = json.loads(path.read_text())
    assert event["outcome"] == "cancelled"
    assert event["tool"] == "waiting"
