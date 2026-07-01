from unittest.mock import Mock

import pytest

pytest.importorskip("mcp")

import requests

from kcidev.libs import dashboard
from kcidev.mcp import tools_dashboard
from kcidev.mcp.errors import ToolExecutionError


def _mock_get(monkeypatch, payload):
    response = Mock(status_code=200)
    response.json.return_value = payload
    get = Mock(return_value=response)
    monkeypatch.setattr(dashboard.kcidev_session, "get", get)
    return get


def _mock_post(monkeypatch, payload):
    response = Mock(status_code=200)
    response.json.return_value = payload
    post = Mock(return_value=response)
    monkeypatch.setattr(dashboard.kcidev_session, "post", post)
    return post


def test_get_build_fetches_dashboard(monkeypatch):
    get = _mock_get(monkeypatch, {"id": "maestro:abc"})
    result = tools_dashboard.get_build("maestro:abc")
    assert result == {"id": "maestro:abc"}
    assert "build/maestro:abc" in get.call_args[0][0]


def test_list_trees_passes_origin_and_days(monkeypatch):
    get = _mock_get(monkeypatch, [])
    tools_dashboard.list_trees(origin="redhat", days=3)
    url = get.call_args[0][0]
    assert "origin=redhat" in url
    assert "interval_in_days=3" in url


def test_list_builds_passes_filters(monkeypatch):
    get = _mock_get(monkeypatch, [])
    tools_dashboard.list_builds(
        giturl="https://git.example.org/linux.git",
        branch="master",
        commit="deadbeef",
        arch="arm64",
    )
    url = get.call_args[0][0]
    assert "tree/deadbeef/builds" in url
    assert "filter_architecture=arm64" in url


def test_get_hardware_summary_posts(monkeypatch):
    post = _mock_post(monkeypatch, {"summary": {}})
    result = tools_dashboard.get_hardware_summary("foo,bar")
    assert result == {"summary": {}}
    assert "hardware/foo%2Cbar/summary" in post.call_args[0][0]


def test_dashboard_error_becomes_tool_error(monkeypatch):
    get = Mock(side_effect=requests.exceptions.ConnectionError("no route"))
    monkeypatch.setattr(dashboard.kcidev_session, "get", get)
    with pytest.raises(ToolExecutionError):
        tools_dashboard.get_build("maestro:abc")


def test_all_read_only_tools_have_docstrings():
    for tool in tools_dashboard.READ_ONLY_TOOLS:
        assert tool.__doc__, f"{tool.__name__} is missing a docstring"
