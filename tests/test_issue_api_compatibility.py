import copy
import json
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import click
import pytest
from click.testing import CliRunner

from kcidev import KciDevError, KernelCIClient
from kcidev.libs import dashboard
from kcidev.subcommands import results
from kcidev.subcommands.results.parser import print_issues

ISSUE_ID = "maestro:issue"
CHECKOUT = {
    "tree_name": "mainline",
    "git_repository_url": "https://example.org/linux.git",
    "git_repository_branch": "master",
    "git_commit_hash": "abc123",
}
FIRST = {**CHECKOUT, "issue_version": 0, "first_seen": "2026-08-01T00:00:00Z"}
EXTRA = {
    "first_incident": FIRST,
    "versions": {
        "0": {"id": ISSUE_ID, "version": 0, "trees": [{"tree_name": "mainline"}]},
        "1": {"id": ISSUE_ID, "version": 1, "trees": [{"tree_name": "mainline"}]},
    },
}
ARGS = [
    "issues",
    "--giturl",
    CHECKOUT["git_repository_url"],
    "--branch",
    "master",
    "--commit",
    "abc123",
    "--tree",
    "mainline",
]
NO_EXTRAS = "No extra details found. Issue id has no incident or doesn't exist."


@pytest.fixture
def api(monkeypatch):
    state = {
        "summary": {
            "summary": {
                "builds": {"issues": [{"id": ISSUE_ID, "version": 0}]},
                "boots": {"issues": [{"id": ISSUE_ID, "version": 0}]},
                "tests": {"issues": [{"id": ISSUE_ID, "version": 1}]},
            }
        },
        "extras": {"issues": {ISSUE_ID: copy.deepcopy(EXTRA)}},
        "listing": {"issues": [{"id": ISSUE_ID, "version": 0}], "extras": {}},
        "builds": [{"id": "build"}],
        "tests": [{"id": "test"}],
        "trees": [CHECKOUT],
    }

    def response(payload):
        result = Mock(status_code=200)
        result.json.return_value = copy.deepcopy(payload)
        return result

    def get(url, **kwargs):
        path = urlparse(url).path
        query = parse_qs(urlparse(url).query)
        if path.endswith("/issue/"):
            return response(state["listing"])
        if path.endswith(f"/issue/{ISSUE_ID}"):
            version = int(query.get("version", [9])[0])
            return response(
                state.get(
                    "detail",
                    {
                        "id": ISSUE_ID,
                        "version": version,
                        "comment": f"Version {version}",
                        "extra": {ISSUE_ID: copy.deepcopy(EXTRA)},
                    },
                )
            )
        for kind in ("builds", "tests"):
            if path.endswith(f"/issue/{ISSUE_ID}/{kind}"):
                return response(state[kind])
        if path.endswith("/tree") or path.endswith("/tree/"):
            return response(state["trees"])
        if "/tree/abc123/" in path:
            return response(state["summary"])
        raise AssertionError(f"Unexpected request: {url}")

    state["get"] = Mock(side_effect=get)
    state["post"] = Mock(side_effect=lambda *a, **k: response(state["extras"]))
    monkeypatch.setattr(dashboard.kcidev_session, "get", state["get"])
    monkeypatch.setattr(dashboard.kcidev_session, "post", state["post"])
    monkeypatch.setattr(
        results, "set_giturl_branch_commit", lambda o, u, b, c, *a, **kw: (u, b, c)
    )
    return state


@pytest.mark.parametrize("version", [None, 0, 2])
@pytest.mark.parametrize("method", ["get_issue", "get_issue_builds", "get_issue_tests"])
def test_library_forwards_issue_versions(api, version, method):
    getattr(KernelCIClient(), method)(ISSUE_ID, version=version)
    query = parse_qs(urlparse(api["get"].call_args.args[0]).query)
    assert query.get("version") == (None if version is None else [str(version)])


@pytest.mark.parametrize("version", [None, 0, 2])
def test_issue_json_keeps_details_and_related_results_on_same_version(api, version):
    args = ["issue", "--id", ISSUE_ID, "--json"]
    if version is not None:
        args += ["--version", str(version)]
    result = CliRunner().invoke(results.results, args)
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    resolved = 9 if version is None else version
    assert data["issue"]["version"] == resolved
    assert data["builds"] == [{"id": "build"}]
    assert data["tests"] == [{"id": "test"}]
    for call in api["get"].call_args_list[1:]:
        assert parse_qs(urlparse(call.args[0]).query)["version"] == [str(resolved)]


@pytest.mark.parametrize("kind", ["builds", "tests"])
def test_issue_json_treats_absent_related_results_as_empty(api, kind):
    api[kind] = {"error": f"No {kind} found for this issue"}
    result = CliRunner().invoke(results.results, ["issue", "--id", ISSUE_ID, "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[kind] == []


@pytest.mark.parametrize("kind", ["builds", "tests"])
def test_issue_does_not_swallow_unrelated_api_errors(api, kind):
    api[kind] = {"error": "Database unavailable"}
    result = CliRunner().invoke(results.results, ["issue", "--id", ISSUE_ID, "--json"])
    assert result.exit_code != 0
    assert "Database unavailable" in result.output


@pytest.mark.parametrize(
    "payload", [{"error": "No issues found"}, {"issues": [], "extras": {}}]
)
def test_empty_issue_listing_is_valid_json(api, payload):
    api["listing"] = payload
    result = CliRunner().invoke(results.results, ["issues", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []
    assert KernelCIClient().get_issue_list()["issues"] == []


@pytest.mark.parametrize("use_json", [False, True])
def test_listing_with_no_extras_still_prints_issues(api, use_json):
    args = ["issues"] + (["--json"] if use_json else [])
    result = CliRunner().invoke(results.results, args)
    assert result.exit_code == 0, result.output
    if use_json:
        assert json.loads(result.output) == [{"id": ISSUE_ID, "version": 0}]
    else:
        assert ISSUE_ID in result.output


@pytest.mark.parametrize("payload", [{"error": NO_EXTRAS}, {"issues": {}}])
def test_empty_extras_are_normalized_for_library_and_checkout(api, payload):
    api["extras"] = payload
    assert KernelCIClient().get_issues_extra([[ISSUE_ID, 0]]) == {"issues": {}}
    result = CliRunner().invoke(results.results, ARGS + ["--json"])
    assert result.exit_code == 0, result.output
    assert [item["version"] for item in json.loads(result.output)] == [0, 1]


def test_empty_extras_request_avoids_invalid_api_call(api):
    assert KernelCIClient().get_issues_extra([]) == {"issues": {}}
    api["post"].assert_not_called()


def test_checkout_preserves_and_deduplicates_versions(api):
    result = CliRunner().invoke(results.results, ARGS + ["--json"])
    assert result.exit_code == 0, result.output
    assert [item["version"] for item in json.loads(result.output)] == [0, 1]
    assert api["post"].call_args.kwargs["json"] == {
        "issues": [[ISSUE_ID, 0], [ISSUE_ID, 1]]
    }
    assert api["get"].call_count == 3


def test_new_issues_match_first_incident_version(api):
    result = CliRunner().invoke(results.results, ARGS + ["--new", "--json"])
    assert result.exit_code == 0, result.output
    assert [item["version"] for item in json.loads(result.output)] == [0]


@pytest.mark.parametrize(
    "extra",
    [
        None,
        {},
        {"first_incident": None, "versions": {"0": EXTRA["versions"]["0"]}},
        {"first_incident": FIRST, "versions": {"0": None}},
        {"first_incident": FIRST, "versions": {"0": {"trees": []}}},
        {
            "first_incident": {**FIRST, "issue_version": None},
            "versions": EXTRA["versions"],
        },
        {
            "first_incident": {**FIRST, "git_commit_hash": "different"},
            "versions": EXTRA["versions"],
        },
    ],
)
def test_missing_or_nonmatching_extras_do_not_claim_new_issues(api, extra):
    api["extras"] = {"issues": {} if extra is None else {ISSUE_ID: extra}}
    result = CliRunner().invoke(results.results, ARGS + ["--new", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []
    assert api["get"].call_count == 1


def test_new_issues_across_checkouts_emit_one_json_document(api):
    api["trees"] = [CHECKOUT, CHECKOUT]
    result = CliRunner().invoke(results.results, ["issues", "--new", "--json"])
    assert result.exit_code == 0, result.output
    assert [item["version"] for item in json.loads(result.output)] == [0]


@pytest.mark.parametrize("resource", ["summary", "extras", "listing"])
def test_checkout_and_listing_errors_fail_instead_of_reporting_no_issues(api, resource):
    api[resource] = {"error": "Database unavailable"}
    args = ["issues", "--json"] if resource == "listing" else ARGS + ["--new", "--json"]
    result = CliRunner().invoke(results.results, args)
    assert result.exit_code != 0
    assert "Database unavailable" in result.output


def test_unrelated_extras_errors_remain_library_errors(api):
    api["extras"] = {"error": "Database unavailable"}
    with pytest.raises(KciDevError, match="Database unavailable"):
        KernelCIClient().get_issues_extra([[ISSUE_ID, 0]])


@pytest.mark.parametrize(
    "payload", [{}, {"issues": {}, "extras": {}}, {"issues": [], "extras": None}]
)
def test_malformed_listings_are_not_silently_successful(payload):
    with pytest.raises(click.ClickException):
        print_issues(payload, True)


@pytest.mark.parametrize("method", ["get_issue", "get_issue_builds", "get_issue_tests"])
@pytest.mark.parametrize("version", [None, 0, 2])
def test_mcp_forwards_issue_versions(api, method, version):
    pytest.importorskip("mcp")
    from kcidev.mcp import tools_dashboard

    getattr(tools_dashboard, method)(ISSUE_ID, version=version)
    query = parse_qs(urlparse(api["get"].call_args.args[0]).query)
    assert query.get("version") == (None if version is None else [str(version)])


def test_mcp_empty_listing(api):
    pytest.importorskip("mcp")
    from kcidev.mcp import tools_dashboard

    api["listing"] = {"error": "No issues found"}
    assert tools_dashboard.list_issues() == {"issues": [], "extras": {}}


@pytest.mark.parametrize("new", [False, True])
def test_checkout_without_issues_avoids_extras_request(api, new):
    api["summary"] = {
        "summary": {kind: {"issues": []} for kind in ("builds", "boots", "tests")}
    }
    result = CliRunner().invoke(
        results.results, ARGS + ["--json"] + (["--new"] if new else [])
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []
    api["post"].assert_not_called()


def test_checkout_human_output_marks_only_first_version_new(api):
    result = CliRunner().invoke(results.results, ARGS)
    assert result.exit_code == 0, result.output
    assert "[NEW] Version 0" in result.output
    assert "[NEW] Version 1" not in result.output
    assert result.output.count("- Version 1") == 1


def test_issue_human_output_supports_missing_extras_and_related_results(api):
    api["detail"] = {"id": ISSUE_ID, "version": 0, "extra": {}}
    api["builds"] = {"error": "No builds found for this issue"}
    api["tests"] = {"error": "No tests found for this issue"}
    result = CliRunner().invoke(
        results.results, ["issue", "--id", ISSUE_ID, "--version", "0"]
    )
    assert result.exit_code == 0, result.output
    assert "version: 0" in result.output
    assert "No associated builds found" in result.output
    assert "No associated tests found" in result.output


def test_unknown_issue_is_not_converted_to_empty_success(api):
    api["detail"] = {"error": "Issue not found"}
    result = CliRunner().invoke(results.results, ["issue", "--id", ISSUE_ID, "--json"])
    assert result.exit_code != 0
    assert "Issue not found" in result.output
    assert api["get"].call_count == 1


def test_empty_listing_human_output(api):
    api["listing"] = {"error": "No issues found"}
    result = CliRunner().invoke(results.results, ["issues"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "No issues found"


@pytest.mark.parametrize("new", [False, True])
@pytest.mark.parametrize("use_json", [False, True])
def test_resolving_a_checkout_tag_keeps_json_clean(api, monkeypatch, new, use_json):
    from kcidev.libs import git_repo

    monkeypatch.setattr(
        results, "set_giturl_branch_commit", git_repo.set_giturl_branch_commit
    )
    monkeypatch.setattr(git_repo, "resolve_git_reference", lambda *args: "abc123")
    args = ARGS.copy()
    args[args.index("--commit") + 1] = "v6.1"
    if new:
        args.append("--new")
    if use_json:
        args.append("--json")
    result = CliRunner().invoke(results.results, args)
    assert result.exit_code == 0, result.output
    if use_json:
        assert len(json.loads(result.output)) == (1 if new else 2)
    else:
        assert "resolved to: abc123" in result.output
