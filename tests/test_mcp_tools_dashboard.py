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
    assert len(result["tests"]) == 20


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


def test_list_tests_projects_fields(monkeypatch):
    _mock_get(
        monkeypatch,
        {"tests": [{"id": "t1", "status": "PASS", "log_url": "x", "misc": {}}]},
    )
    result = tools_dashboard.list_tests(
        giturl="https://git.example.org/linux.git",
        branch="master",
        commit="deadbeef",
        fields=["id", "status", "nonexistent"],
    )
    assert result["tests"] == [{"id": "t1", "status": "PASS"}]


SUMMARY_PAYLOAD = {
    "common": {"tree_name": "mainline"},
    "summary": {
        "builds": {
            "status": {"PASS": 10, "FAIL": 1},
            "architectures": {"x86_64": {"PASS": 5}},
            "configs": {"defconfig": {"PASS": 10}},
            "labs": {"lab-1": {}},
            "issues": [],
        },
        "boots": {
            "status": {"pass": 20},
            "failed_platforms": ["board-1"],
            "environment_misc": {"big": "blob"},
        },
    },
    "filters": {"configs": ["defconfig"]},
}


def test_get_summary_compact_by_default(monkeypatch):
    _mock_get(monkeypatch, SUMMARY_PAYLOAD)
    result = tools_dashboard.get_summary(
        giturl="https://git.example.org/linux.git", branch="master", commit="deadbeef"
    )
    assert result["common"] == {"tree_name": "mainline"}
    assert result["summary"]["builds"] == {
        "status": {"PASS": 10, "FAIL": 1},
        "architectures": {"x86_64": {"PASS": 5}},
        "labs": {"lab-1": {}},
        "issues": [],
    }
    assert result["summary"]["boots"] == {
        "status": {"pass": 20},
        "failed_platforms": ["board-1"],
    }
    assert "filters" not in result


def test_get_summary_detail_returns_full_payload(monkeypatch):
    _mock_get(monkeypatch, SUMMARY_PAYLOAD)
    result = tools_dashboard.get_summary(
        giturl="https://git.example.org/linux.git",
        branch="master",
        commit="deadbeef",
        detail=True,
    )
    assert result == SUMMARY_PAYLOAD


def test_get_test_issues_fetches_dashboard(monkeypatch):
    get = _mock_get(monkeypatch, [{"id": "issue1"}])
    result = tools_dashboard.get_test_issues("maestro:t1")
    assert result == [{"id": "issue1"}]
    assert "test/maestro:t1/issues" in get.call_args[0][0]


def test_get_build_issues_fetches_dashboard(monkeypatch):
    get = _mock_get(monkeypatch, [{"id": "issue2"}])
    result = tools_dashboard.get_build_issues("maestro:b1")
    assert result == [{"id": "issue2"}]
    assert "build/maestro:b1/issues" in get.call_args[0][0]


def test_get_log_returns_client_payload(monkeypatch):
    from kcidev.api import KernelCIClient

    monkeypatch.setattr(
        KernelCIClient,
        "get_log",
        lambda self, tid, max_bytes=16384, tail=True: {
            "test_id": tid,
            "truncated": False,
            "text": "log body",
        },
    )
    result = tools_dashboard.get_log("maestro:t1")
    assert result["text"] == "log body"
    assert result["test_id"] == "maestro:t1"


def test_get_test_issues_returns_empty_when_none_are_tracked(monkeypatch):
    _mock_get(monkeypatch, {"error": "No issues were found for this test"})
    assert tools_dashboard.get_test_issues("maestro:t1") == []


def test_get_build_issues_returns_empty_when_none_are_tracked(monkeypatch):
    _mock_get(monkeypatch, {"error": "No issues found for this build"})
    assert tools_dashboard.get_build_issues("maestro:b1") == []


def test_get_test_issues_still_reports_other_errors(monkeypatch):
    _mock_get(monkeypatch, {"error": "Test not found"})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.get_test_issues("maestro:nope")


def test_get_issue_tests_returns_empty_when_none_are_tracked(monkeypatch):
    get = _mock_get(monkeypatch, {"error": "No tests found for this issue"})
    result = tools_dashboard.get_issue_tests("maestro:i1")
    assert result["tests"] == []
    assert result["matched"] == 0
    assert get.called


def test_get_issue_builds_returns_empty_when_none_are_tracked(monkeypatch):
    _mock_get(monkeypatch, {"error": "No builds found for this issue"})
    result = tools_dashboard.get_issue_builds("maestro:i1")
    assert result["builds"] == []
    assert result["matched"] == 0


def test_get_issue_tests_still_reports_other_errors(monkeypatch):
    _mock_get(monkeypatch, {"error": "Issue not found"})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.get_issue_tests("maestro:nope")


def _tree_args(**extra):
    args = {
        "giturl": "https://git.example.org/linux.git",
        "branch": "master",
        "commit": "deadbeef",
    }
    args.update(extra)
    return args


def test_list_tests_accepts_uppercase_status(monkeypatch):
    _mock_get(
        monkeypatch,
        {"tests": [{"id": "p1", "status": "PASS"}, {"id": "f1", "status": "FAIL"}]},
    )
    result = tools_dashboard.list_tests(**_tree_args(status="FAIL"))
    assert result["matched"] == 1
    assert result["tests"] == [{"id": "f1", "status": "FAIL"}]


def test_list_tests_rejects_unknown_status(monkeypatch):
    _mock_get(monkeypatch, {"tests": [{"id": "f1", "status": "FAIL"}]})
    with pytest.raises(ToolExecutionError) as excinfo:
        tools_dashboard.list_tests(**_tree_args(status="borked"))
    assert "borked" in str(excinfo.value)


def test_list_tests_rejects_negative_limit(monkeypatch):
    _mock_get(monkeypatch, {"tests": [{"id": str(i)} for i in range(5)]})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.list_tests(**_tree_args(limit=-1))


def test_list_tests_rejects_negative_offset(monkeypatch):
    _mock_get(monkeypatch, {"tests": [{"id": str(i)} for i in range(5)]})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.list_tests(**_tree_args(offset=-1))


def test_get_issue_rejects_empty_id(monkeypatch):
    get = _mock_get(monkeypatch, {"issues": [{"id": "maestro:one"}]})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.get_issue("")
    get.assert_not_called()


def test_invalid_status_is_rejected_before_any_request(monkeypatch):
    get = _mock_get(monkeypatch, {"tests": []})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.list_tests(**_tree_args(status="borked"))
    get.assert_not_called()


def test_invalid_limit_is_rejected_before_any_request(monkeypatch):
    get = _mock_get(monkeypatch, {"tests": []})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.list_tests(**_tree_args(limit=-1))
    get.assert_not_called()


def test_invalid_offset_is_rejected_before_any_request(monkeypatch):
    get = _mock_get(monkeypatch, {"builds": []})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.list_builds(**_tree_args(offset=-1))
    get.assert_not_called()


def test_issue_tools_validate_before_any_request(monkeypatch):
    get = _mock_get(monkeypatch, {"tests": []})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.get_issue_tests("maestro:i1", status="borked")
    get.assert_not_called()


def test_list_labs_returns_lab_counts(monkeypatch):
    get = _mock_get(
        monkeypatch,
        {
            "n_builds": 100,
            "lab_maps": {
                "lava-collabora": {"builds": 161, "boots": 987, "tests": 100105},
                "opentest-ti": {"builds": 4, "boots": 80, "tests": 0},
            },
        },
    )
    result = tools_dashboard.list_labs(days=3)
    url = get.call_args[0][0]
    assert "metrics/" in url
    assert "start_days_ago=3" in url
    assert result["days"] == 3
    assert result["labs"]["opentest-ti"] == {"builds": 4, "boots": 80, "tests": 0}
    assert "n_builds" not in result


def test_list_labs_without_lab_data_errors(monkeypatch):
    _mock_get(monkeypatch, {"n_builds": 100})
    with pytest.raises(ToolExecutionError, match="lab data"):
        tools_dashboard.list_labs()


def test_list_boots_filters_by_lab(monkeypatch):
    _mock_get(
        monkeypatch,
        {
            "boots": [
                {"id": "b1", "status": "PASS", "lab": "lava-collabora"},
                {"id": "b2", "status": "FAIL", "lab": "opentest-ti"},
                {"id": "b3", "status": "FAIL", "lab": "lava-collabora"},
                {"id": "b4", "status": "PASS", "lab": None},
            ]
        },
    )
    result = tools_dashboard.list_boots(
        giturl="https://git.example.org/linux.git",
        branch="master",
        commit="deadbeef",
        lab="LAVA-Collabora",
    )
    assert result["total"] == 4
    assert result["matched"] == 2
    assert [b["id"] for b in result["boots"]] == ["b1", "b3"]


def test_list_tests_combines_lab_and_status_filters(monkeypatch):
    _mock_get(
        monkeypatch,
        {
            "tests": [
                {"id": "t1", "status": "FAIL", "lab": "lava-collabora"},
                {"id": "t2", "status": "PASS", "lab": "lava-collabora"},
                {"id": "t3", "status": "FAIL", "lab": "maestro"},
            ]
        },
    )
    result = tools_dashboard.list_tests(
        giturl="https://git.example.org/linux.git",
        branch="master",
        commit="deadbeef",
        status="fail",
        lab="lava-collabora",
    )
    assert result["total"] == 3
    assert result["matched"] == 1
    assert [t["id"] for t in result["tests"]] == ["t1"]


def test_list_builds_matches_lab_in_misc(monkeypatch):
    _mock_get(
        monkeypatch,
        {
            "builds": [
                {"id": "b1", "status": "PASS", "misc": {"lab": "maestro"}},
                {"id": "b2", "status": "PASS", "misc": {"runtime": "k8s-all"}},
                {"id": "b3", "status": "PASS", "misc": None},
                {"id": "b4", "status": "PASS"},
            ]
        },
    )
    result = tools_dashboard.list_builds(
        giturl="https://git.example.org/linux.git",
        branch="master",
        commit="deadbeef",
        lab="k8s-all",
    )
    assert result["matched"] == 1
    assert [b["id"] for b in result["builds"]] == ["b2"]


def test_get_summary_keeps_lab_breakdown(monkeypatch):
    _mock_get(monkeypatch, SUMMARY_PAYLOAD)
    result = tools_dashboard.get_summary(
        giturl="https://git.example.org/linux.git", branch="master", commit="deadbeef"
    )
    assert result["summary"]["builds"]["labs"] == {"lab-1": {}}


def test_list_labs_rejects_non_positive_days(monkeypatch):
    get = _mock_get(monkeypatch, {"lab_maps": {}})
    with pytest.raises(ToolExecutionError):
        tools_dashboard.list_labs(days=0)
    get.assert_not_called()


def test_list_labs_rejects_days_above_cap(monkeypatch):
    get = _mock_get(monkeypatch, {"lab_maps": {}})
    with pytest.raises(ToolExecutionError) as excinfo:
        tools_dashboard.list_labs(days=90)
    assert "90" in str(excinfo.value)
    get.assert_not_called()


def test_unmatched_lab_reports_the_labs_that_are_present(monkeypatch):
    _mock_get(
        monkeypatch,
        {
            "tests": [
                {"id": "t1", "status": "PASS", "lab": "lava-collabora"},
                {"id": "t2", "status": "PASS", "lab": "lava-broonie"},
            ]
        },
    )
    result = tools_dashboard.list_tests(**_tree_args(lab="lava-colabora"))
    assert result["matched"] == 0
    assert result["labs_present"] == ["lava-broonie", "lava-collabora"]


def test_matched_lab_omits_the_labs_present_hint(monkeypatch):
    _mock_get(
        monkeypatch,
        {"tests": [{"id": "t1", "status": "PASS", "lab": "lava-collabora"}]},
    )
    result = tools_dashboard.list_tests(**_tree_args(lab="lava-collabora"))
    assert result["matched"] == 1
    assert "labs_present" not in result


def test_labs_present_ignores_the_status_filter(monkeypatch):
    _mock_get(
        monkeypatch,
        {
            "tests": [
                {"id": "p1", "status": "PASS", "lab": "lava-collabora"},
                {"id": "f1", "status": "FAIL", "lab": "lava-broonie"},
            ]
        },
    )

    result = tools_dashboard.list_tests(
        **_tree_args(status="fail", lab="lava-collabora")
    )

    assert result["matched"] == 0
    assert "lava-collabora" in result["labs_present"]
