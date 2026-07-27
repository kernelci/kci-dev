from unittest.mock import Mock

import pytest

pytest.importorskip("mcp")

import anyio
import requests
from mcp.shared.memory import (
    create_connected_server_and_client_session as client_session,
)

from kcidev.libs import dashboard
from kcidev.mcp import create_server

CFG = {
    "default_instance": "test",
    "test": {
        "api": "https://api.example.org/",
        "pipeline": "https://pipeline.example.org/",
        "token": "secret",
    },
}


def _list_tools(server):
    async def run():
        async with client_session(server._mcp_server) as session:
            result = await session.list_tools()
            return {t.name: t for t in result.tools}

    return anyio.run(run)


def _call_tool(server, name, arguments):
    async def run():
        async with client_session(server._mcp_server) as session:
            return await session.call_tool(name, arguments)

    return anyio.run(run)


def test_dashboard_tools_registered_without_config():
    tools = _list_tools(create_server())
    assert "list_trees" in tools
    assert "get_summary" in tools
    assert "get_build" in tools
    assert "get_node" not in tools
    assert "retry_job" not in tools
    assert "trigger_checkout" not in tools
    assert "trigger_patchset" not in tools


def test_maestro_tools_registered_with_full_config():
    tools = _list_tools(create_server(CFG, "test"))
    assert "get_node" in tools
    assert "list_nodes" in tools
    assert "retry_job" in tools
    assert "trigger_checkout" in tools
    assert "trigger_patchset" in tools


def test_action_tools_not_registered_without_token():
    cfg = {"test": {"api": "https://api.example.org/"}}
    tools = _list_tools(create_server(cfg, "test"))
    assert "get_node" in tools
    assert "retry_job" not in tools
    assert "trigger_checkout" not in tools
    assert "trigger_patchset" not in tools


def test_action_tools_not_registered_without_pipeline_token():
    cfg = {
        "test": {
            "api": "https://api.example.org/",
            "pipeline": "https://pipeline.example.org/",
        }
    }
    tools = _list_tools(create_server(cfg, "test"))
    assert "get_node" in tools
    assert "retry_job" not in tools
    assert "trigger_checkout" not in tools
    assert "trigger_patchset" not in tools


def test_tool_annotations():
    tools = _list_tools(create_server(CFG, "test"))
    assert tools["list_trees"].annotations.readOnlyHint is True
    assert tools["get_node"].annotations.readOnlyHint is True
    assert tools["retry_job"].annotations.readOnlyHint is False
    assert tools["trigger_checkout"].annotations.readOnlyHint is False
    assert tools["trigger_patchset"].annotations.readOnlyHint is False


def test_call_tool_success(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"id": "maestro:b1"}
    monkeypatch.setattr(dashboard.kcidev_session, "get", Mock(return_value=response))

    result = _call_tool(create_server(), "get_build", {"build_id": "maestro:b1"})
    assert result.isError is False
    assert "maestro:b1" in result.content[0].text


def test_call_tool_failure_is_tool_error_not_crash(monkeypatch):
    monkeypatch.setattr(
        dashboard.kcidev_session,
        "get",
        Mock(side_effect=requests.exceptions.ConnectionError("no route")),
    )

    result = _call_tool(create_server(), "get_build", {"build_id": "maestro:b1"})
    assert result.isError is True


def test_get_node_missing_returns_clean_tool_error(monkeypatch):
    from kcidev.libs import maestro_common

    response = Mock(status_code=200)
    response.json.return_value = None
    monkeypatch.setattr(
        maestro_common.kcidev_session, "get", Mock(return_value=response)
    )

    result = _call_tool(create_server(CFG, "test"), "get_node", {"node_id": "0" * 24})
    assert result.isError is True
    assert "not found" in result.content[0].text


def test_server_reports_kcidev_version():
    from kcidev.libs.common import kcidev_version

    assert create_server()._mcp_server.version == kcidev_version


def test_retry_job_calls_pipeline_with_token(monkeypatch):
    from kcidev.libs import maestro_common

    response = Mock(status_code=200)
    response.json.return_value = {"message": "OK"}
    post = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)

    result = _call_tool(create_server(CFG, "test"), "retry_job", {"node_id": "n1"})
    assert result.isError is False
    assert post.call_args[0][0] == "https://pipeline.example.org/api/jobretry"
    assert post.call_args.kwargs["headers"]["Authorization"] == "secret"


def test_retry_job_failure_returns_tool_error(monkeypatch):
    from kcidev.libs import maestro_common

    monkeypatch.setattr(
        maestro_common.kcidev_session,
        "post",
        Mock(side_effect=requests.exceptions.ConnectionError("no route")),
    )
    result = _call_tool(create_server(CFG, "test"), "retry_job", {"node_id": "n1"})
    assert result.isError is True
    assert "retry failed" in result.content[0].text


def test_list_nodes_projects_fields(monkeypatch):
    from kcidev.libs import maestro_common

    response = Mock(status_code=200)
    response.json.return_value = [
        {"id": "n1", "name": "checkout", "state": "done", "commit_message": "huge"}
    ]
    monkeypatch.setattr(
        maestro_common.kcidev_session, "get", Mock(return_value=response)
    )
    result = _call_tool(
        create_server(CFG, "test"),
        "list_nodes",
        {"fields": ["id", "state"]},
    )
    assert result.isError is False
    assert '"commit_message"' not in result.content[0].text
    assert '"n1"' in result.content[0].text
