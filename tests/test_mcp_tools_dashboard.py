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


def test_list_tests_filters_status_and_paginates(monkeypatch):
    tests = [{"id": f"t{i}", "status": "PASS"} for i in range(50)] + [
        {"id": f"f{i}", "status": "FAIL"} for i in range(30)
    ]
    _mock_get(monkeypatch, {"tests": tests})
    result = tools_dashboard.list_tests(
        giturl="https://git.example.org/linux.git",
        branch="master",
        commit="deadbeef",
        status="fail",
        limit=10,
        offset=5,
    )
    assert result["total"] == 80
    assert result["matched"] == 30
    assert len(result["tests"]) == 10
    assert all(t["status"] == "FAIL" for t in result["tests"])
    assert result["tests"][0]["id"] == "f5"


def test_list_tests_default_limit_bounds_response(monkeypatch):
    _mock_get(
        monkeypatch, {"tests": [{"id": str(i), "status": "PASS"} for i in range(300)]}
    )
    result = tools_dashboard.list_tests(
        giturl="https://git.example.org/linux.git", branch="master", commit="deadbeef"
    )
    assert result["total"] == 300
    assert result["matched"] == 300
    assert len(result["tests"]) == 100


def test_get_issue_builds_wraps_bare_list(monkeypatch):
    _mock_get(
        monkeypatch, [{"id": "b1", "status": "FAIL"}, {"id": "b2", "status": "PASS"}]
    )
    result = tools_dashboard.get_issue_builds("maestro:abc", status="fail")
    assert result["total"] == 2
    assert result["matched"] == 1
    assert result["builds"] == [{"id": "b1", "status": "FAIL"}]


def test_list_commits_fetches_history(monkeypatch):
    get = _mock_get(monkeypatch, [])
    tools_dashboard.list_commits(
        giturl="https://git.example.org/linux.git", branch="master", commit="deadbeef"
    )
    assert "tree/deadbeef/commits" in get.call_args[0][0]


def test_list_commits_normalises_builds_status_keys(monkeypatch):
    _mock_get(
        monkeypatch,
        [
            {
                "git_commit_hash": "deadbeef",
                "builds": {"PASS": 31, "FAIL": 1},
                "boots": {"pass": 23, "fail": 0},
                "tests": {"pass": 100, "fail": 2},
            }
        ],
    )
    result = tools_dashboard.list_commits(
        giturl="https://git.example.org/linux.git", branch="master", commit="deadbeef"
    )
    assert result[0]["builds"] == {"pass": 31, "fail": 1}
    assert result[0]["boots"] == {"pass": 23, "fail": 0}


def test_list_commits_not_found_includes_guidance(monkeypatch):
    _mock_get(monkeypatch, {"error": "History of tree commits not found"})
    with pytest.raises(ToolExecutionError, match="list_trees"):
        tools_dashboard.list_commits(
            giturl="https://git.example.org/linux.git",
            branch="master",
            commit="deadbeef",
        )
