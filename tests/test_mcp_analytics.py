import json
import logging
import os
import threading
from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip("mcp")

import anyio
from click.testing import CliRunner
from mcp.shared.memory import (
    create_connected_server_and_client_session as client_session,
)

from kcidev.mcp import create_server
from kcidev.mcp.analytics import analytics_logging, log_event, logger
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


@pytest.mark.skipif(os.name == "nt", reason="Unix rename-based log rotation")
def test_logging_reopens_rotated_file(tmp_path):
    path = tmp_path / "analytics.jsonl"
    rotated = tmp_path / "analytics.jsonl.1"
    with analytics_logging(path):
        log_event("before_rotation")
        path.rename(rotated)
        path.touch()
        log_event("after_rotation")
    assert json.loads(rotated.read_text())["event"] == "before_rotation"
    assert json.loads(path.read_text())["event"] == "after_rotation"


@pytest.mark.parametrize("fails", [False, True])
def test_logging_restores_level_and_handlers(tmp_path, fails):
    previous = logger.handlers[:], logger.level, logger.propagate
    handler = logging.FileHandler(tmp_path / "restored.log")
    try:
        logger.handlers = [handler]
        logger.setLevel(logging.WARNING)
        logger.propagate = False
        try:
            with analytics_logging(tmp_path / "analytics.jsonl"):
                log_event("inside")
                if fails:
                    raise RuntimeError("test cleanup")
        except RuntimeError:
            assert fails
        assert logger.handlers == [handler]
        assert logger.level == logging.WARNING
        assert logger.propagate is False
        log_event("must_not_be_logged")
        logger.warning("restored warning")
        assert (tmp_path / "restored.log").read_text() == "restored warning\n"
    finally:
        logger.handlers, level, logger.propagate = previous
        logger.setLevel(level)
        handler.close()


def test_default_logging_uses_stderr(capsys):
    with analytics_logging():
        log_event("server_start")
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["event"] == "server_start"


@pytest.mark.skipif(os.name == "nt", reason="Unix rename-based log rotation")
@pytest.mark.parametrize("outcome", ["success", "error", "cancelled"])
def test_reopen_failure_preserves_tool_outcome(tmp_path, capsys, outcome):
    from mcp.types import CallToolRequest, CallToolRequestParams

    server = create_server()

    @server.tool()
    async def example():
        if outcome == "cancelled":
            await anyio.sleep_forever()
        if outcome == "error":
            raise ValueError("private tool exception")
        return "private tool result"

    async def run():
        handler = server._mcp_server.request_handlers[CallToolRequest]
        request = CallToolRequest(
            method="tools/call", params=CallToolRequestParams(name="example")
        )
        if outcome == "cancelled":
            with anyio.move_on_after(0.05) as scope:
                await handler(request)
            assert scope.cancelled_caught
        else:
            result = await handler(request)
            assert result.root.isError is (outcome == "error")
            expected = (
                "private tool result"
                if outcome == "success"
                else "private tool exception"
            )
            assert expected in result.root.content[0].text

    path = tmp_path / "analytics.jsonl"
    with analytics_logging(path):
        path.rename(tmp_path / "rotated.jsonl")
        # A directory at the replacement path makes the real reopen fail.
        path.mkdir()
        anyio.run(run)

    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "kci-dev: cannot write MCP analytics log\n"


@pytest.mark.skipif(os.name == "nt", reason="Unix rename-based log rotation")
def test_logging_recovers_after_reopen_failure(tmp_path, capsys):
    path = tmp_path / "analytics.jsonl"
    rotated = tmp_path / "analytics.jsonl.1"
    with analytics_logging(path):
        log_event("before_rotation")
        path.rename(rotated)
        path.mkdir()
        log_event("cannot_be_written")
        path.rmdir()
        log_event("recovered")

    assert json.loads(rotated.read_text())["event"] == "before_rotation"
    assert json.loads(path.read_text())["event"] == "recovered"
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "kci-dev: cannot write MCP analytics log\n"


@pytest.mark.parametrize("use_file", [False, True])
def test_write_failure_reports_safe_diagnostic(tmp_path, monkeypatch, capsys, use_file):
    path = tmp_path / "analytics.jsonl" if use_file else None
    with analytics_logging(path):
        with monkeypatch.context() as patch:
            stream = Mock()
            stream.write.side_effect = OSError("private write failure")
            patch.setattr(logger.handlers[0], "stream", stream)
            log_event("tool_call", tool="private tool name")
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "kci-dev: cannot write MCP analytics log\n"


@pytest.mark.parametrize("failure", ["broken_pipe", "closed_stream"])
def test_logging_tolerates_diagnostic_failure(tmp_path, monkeypatch, failure):
    if failure == "broken_pipe":
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        stream = os.fdopen(write_fd, "w", buffering=1)
    else:
        stream = (tmp_path / "stderr").open("w")
        stream.close()
    try:
        with monkeypatch.context() as patch:
            patch.setattr("sys.stderr", stream)
            with analytics_logging():
                log_event("tool_call", tool="private tool name")
    finally:
        try:
            stream.close()
        except OSError:
            pass


@pytest.mark.parametrize("tool_fails", [False, True])
def test_logging_tolerates_close_failure(tmp_path, monkeypatch, capsys, tool_fails):
    previous = logger.handlers[:], logger.level, logger.propagate
    original_error = RuntimeError("private tool error")
    try:
        with analytics_logging(tmp_path / "analytics.jsonl"):
            stream = logger.handlers[0].stream
            # Exercise the real FileHandler.close() flush and cleanup path.
            monkeypatch.setattr(
                stream, "flush", Mock(side_effect=OSError("private close failure"))
            )
            if tool_fails:
                raise original_error
    except RuntimeError as exc:
        assert tool_fails
        assert exc is original_error
    else:
        assert not tool_fails
    assert stream.closed
    assert (logger.handlers, logger.level, logger.propagate) == previous
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "kci-dev: cannot write MCP analytics log\n"


@pytest.mark.parametrize("transport", ["stdio", "http"])
@pytest.mark.parametrize("server_fails", [False, True])
def test_cli_lifecycle_logging(tmp_path, monkeypatch, transport, server_fails):
    server = Mock()
    monkeypatch.setattr("kcidev.mcp.create_server", Mock(return_value=server))
    failure = RuntimeError("private server failure") if server_fails else None
    run_stdio = AsyncMock(side_effect=failure)
    server.run.side_effect = failure
    monkeypatch.setattr(mcp, "_run_stdio", run_stdio)
    path = tmp_path / "analytics.jsonl"
    result = CliRunner().invoke(
        mcp.mcp,
        ["--transport", transport, "--log-file", str(path)],
        obj={},
    )
    if server_fails:
        assert result.exit_code == 1
        assert result.exception is failure
    else:
        assert result.exit_code == 0, result.output
    if transport == "stdio":
        run_stdio.assert_awaited_once_with(server)
        server.run.assert_not_called()
    else:
        server.run.assert_called_once_with(transport="streamable-http")
        run_stdio.assert_not_awaited()
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
            await handler(
                CallToolRequest(
                    method="tools/call", params=CallToolRequestParams(name="waiting")
                )
            )
        assert scope.cancel_called

    with analytics_logging(path):
        anyio.run(run)
    event = json.loads(path.read_text())
    assert event["outcome"] == "cancelled"
    assert event["tool"] == "waiting"


@pytest.mark.parametrize("logging_fails", [False, True])
def test_protocol_cancellation_of_registered_blocking_tool(
    tmp_path, monkeypatch, capsys, logging_fails
):
    from mcp.shared.exceptions import McpError
    from mcp.types import (
        CancelledNotification,
        CancelledNotificationParams,
        ClientNotification,
    )

    server = create_server({"test": {"api": "https://api.example.org/"}}, "test")
    release = threading.Event()
    path = tmp_path / "analytics.jsonl"

    async def run():
        started = anyio.Event()
        cancelled = anyio.Event()
        logged = anyio.Event()
        request_ids = []

        def get_node(client, node_id):
            request_ids.append(server.get_context().request_context.request_id)
            anyio.from_thread.run_sync(started.set)
            assert release.wait(timeout=10), "worker was never released"
            return {"id": node_id}

        def record(event, **fields):
            log_event(event, **fields)
            logged.set()

        monkeypatch.setattr("kcidev.api.KernelCIClient.get_node", get_node)
        monkeypatch.setattr("kcidev.mcp.analytics.log_event", record)

        with anyio.fail_after(10):
            async with client_session(server._mcp_server) as session:

                async def call():
                    with pytest.raises(McpError, match="cancelled"):
                        await session.call_tool("get_node", {"node_id": "private-node"})
                    cancelled.set()

                async with anyio.create_task_group() as tasks:
                    tasks.start_soon(call)
                    try:
                        await started.wait()
                        await session.send_notification(
                            ClientNotification(
                                CancelledNotification(
                                    method="notifications/cancelled",
                                    params=CancelledNotificationParams(
                                        requestId=request_ids[0]
                                    ),
                                )
                            )
                        )
                        # The protocol response confirms cancellation reached
                        # the server while the registered tool is still blocked.
                        await cancelled.wait()
                        assert not logged.is_set()
                    finally:
                        release.set()
                    await logged.wait()

    with analytics_logging(path):
        if logging_fails:
            monkeypatch.setattr(
                logger.handlers[0],
                "reopenIfNeeded",
                Mock(side_effect=OSError("private reopen failure")),
            )
        anyio.run(run)
    if logging_fails:
        output = capsys.readouterr()
        assert output.out == ""
        assert output.err == "kci-dev: cannot write MCP analytics log\n"
        assert path.read_text() == ""
        return
    event = json.loads(path.read_text())
    assert event["outcome"] == "cancelled"
    assert event["tool"] == "get_node"
    assert event["instance"] == "test"
    assert "private-node" not in path.read_text()
