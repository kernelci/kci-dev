import copy
import json
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import git
import pytest
import requests
from click.testing import CliRunner

from kcidev.libs import dashboard, git_repo
from kcidev.main import get_cli
from kcidev.subcommands.results.parser import print_missing_data

API = "https://dashboard.example.org/api/"
CHECKOUT = {
    "tree_name": "mainline",
    "git_repository_url": "https://example.org/linux.git",
    "git_repository_branch": "master",
    "git_commit_hash": "a" * 40,
}
SECOND = {**CHECKOUT, "git_commit_hash": "b" * 40}
CHECKOUT_ARGS = [
    "--giturl",
    CHECKOUT["git_repository_url"],
    "--branch",
    "master",
    "--commit",
    CHECKOUT["git_commit_hash"],
    "--tree",
    "mainline",
]
NO_ISSUES = {
    "builds": "No issues found for this build",
    "boots": "No issues were found for this test",
}


@pytest.fixture
def api(monkeypatch, tmp_path):
    state = {"trees": [CHECKOUT, SECOND], "responses": {}, "calls": []}
    settings = tmp_path / "kci-dev.toml"
    settings.write_text(f'dashboard_api = "{API}"\n', encoding="utf-8")
    monkeypatch.setattr(dashboard, "_dashboard_api", API)

    def get(url, **kwargs):
        assert url.startswith(API)
        parsed = urlparse(url)
        path = parsed.path.removeprefix("/api/")
        state["calls"].append((path, parse_qs(parsed.query)))
        if path in state["responses"]:
            payload = state["responses"][path]
        elif path == "tree":
            payload = state["trees"]
        elif path.startswith("tree/"):
            _, commit, kind = path.split("/")
            payload = {
                kind: [
                    {
                        "id": f"{commit[0]}-{kind}-{label}",
                        "status": status,
                        "log_url": None,
                    }
                    for label, status in (
                        ("pass", "PASS"),
                        ("tracked", "FAIL"),
                        ("missing", "ERROR"),
                    )
                ]
            }
        elif path.endswith("/issues"):
            endpoint, item_id, _ = path.split("/")
            assert not item_id.endswith("pass")
            payload = (
                {"error": NO_ISSUES["builds" if endpoint == "build" else "boots"]}
                if item_id.endswith("missing")
                else [{"id": "maestro:known", "version": 0}]
            )
        else:
            raise AssertionError(f"Unexpected request: {url}")
        if isinstance(payload, Exception):
            raise payload
        response = Mock(status_code=200)
        response.json.return_value = copy.deepcopy(payload)
        return response

    monkeypatch.setattr(dashboard.kcidev_session, "get", get)
    state["invoke"] = lambda args: CliRunner().invoke(
        get_cli(),
        ["--settings", str(settings), "results", "issues", "--missing", *args],
    )
    return state


@pytest.mark.parametrize("kind", ["builds", "boots", None])
@pytest.mark.parametrize("all_checkouts", [False, True])
def test_missing_json_keeps_results_with_their_checkout(api, kind, all_checkouts):
    args = [] if all_checkouts else CHECKOUT_ARGS
    result = api["invoke"](args + ([f"--{kind}"] if kind else []) + ["--json"])
    assert result.exit_code == 0, result.output
    expected = []
    for item_kind in [kind] if kind else ["builds", "boots"]:
        for checkout in [CHECKOUT, SECOND] if all_checkouts else [CHECKOUT]:
            commit = checkout["git_commit_hash"]
            item_id = f"{commit[0]}-{item_kind}-missing"
            endpoint = "build" if item_kind == "builds" else "test"
            expected.append(
                {
                    "type": "build" if item_kind == "builds" else "boot",
                    "tree": "mainline",
                    "giturl": CHECKOUT["git_repository_url"],
                    "branch": "master",
                    "commit": commit,
                    "id": item_id,
                    "status": "ERROR",
                    "dashboard": f"https://dashboard.example.org/{endpoint}/{item_id}",
                }
            )
    assert json.loads(result.output) == expected


@pytest.mark.parametrize("kind", ["builds", "boots"])
@pytest.mark.parametrize("empty_list", [False, True])
def test_missing_accepts_exact_no_issue_errors_and_empty_lists(api, kind, empty_list):
    endpoint = "build" if kind == "builds" else "test"
    api["responses"][f"{endpoint}/a-{kind}-missing/issues"] = (
        [] if empty_list else {"error": NO_ISSUES[kind]}
    )
    result = api["invoke"](CHECKOUT_ARGS + [f"--{kind}", "--json"])
    assert result.exit_code == 0, result.output
    assert [item["id"] for item in json.loads(result.output)] == [f"a-{kind}-missing"]


def test_missing_accepts_legacy_build_no_issue_message(api):
    api["responses"]["build/a-builds-missing/issues"] = {
        "error": "No issues were found for this build"
    }
    result = api["invoke"](CHECKOUT_ARGS + ["--builds", "--json"])
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.output)) == 1


@pytest.mark.parametrize("kind", ["builds", "boots"])
@pytest.mark.parametrize("stage", ["tree", "results", "issues"])
@pytest.mark.parametrize("use_json", [False, True])
@pytest.mark.parametrize(
    "error",
    [{"error": "No issues query is available"}, requests.ConnectionError("offline")],
)
def test_missing_fails_when_evidence_cannot_be_fetched(
    api, kind, stage, use_json, error
):
    endpoint = "build" if kind == "builds" else "test"
    path = {
        "tree": "tree",
        "results": f"tree/{CHECKOUT['git_commit_hash']}/{kind}",
        "issues": f"{endpoint}/a-{kind}-missing/issues",
    }[stage]
    api["responses"][path] = error
    result = api["invoke"]([f"--{kind}"] + (["--json"] if use_json else []))
    assert result.exit_code != 0, result.output
    assert "No issues query is available" in result.output or "offline" in result.output
    assert '"type"' not in result.output


@pytest.mark.parametrize("kind", ["builds", "boots"])
@pytest.mark.parametrize("empty_stage", ["trees", "results", "issues"])
def test_missing_empty_reports_are_json_arrays(api, kind, empty_stage):
    if empty_stage == "trees":
        api["trees"] = []
    else:
        for checkout in api["trees"]:
            commit = checkout["git_commit_hash"]
            if empty_stage == "results":
                api["responses"][f"tree/{commit}/{kind}"] = {kind: []}
            else:
                endpoint = "build" if kind == "builds" else "test"
                api["responses"][f"{endpoint}/{commit[0]}-{kind}-missing/issues"] = [
                    {"id": "maestro:known", "version": 0}
                ]
    result = api["invoke"]([f"--{kind}", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []


@pytest.mark.parametrize(
    "args", [["--new"], ["--builds", "--boots"], ["--branch", "master"]]
)
def test_missing_rejects_ambiguous_scope_before_requests(api, args):
    result = api["invoke"](args)
    assert result.exit_code == 2, result.output
    assert api["calls"] == []


def test_missing_tree_and_arch_filters_apply_to_all_checkout_scan(api):
    api["trees"] = [CHECKOUT, {**SECOND, "tree_name": "stable"}]
    result = api["invoke"](
        ["--tree", "stable", "--arch", "arm64", "--builds", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert [item["commit"] for item in json.loads(result.output)] == [
        SECOND["git_commit_hash"]
    ]
    queries = [query for path, query in api["calls"] if path.endswith("/builds")]
    assert len(queries) == 1
    assert queries[0]["filter_architecture"] == ["arm64"]
    assert queries[0]["filter_tree_name"] == ["stable"]


def test_missing_tag_resolution_does_not_pollute_json(api, monkeypatch):
    monkeypatch.setattr(
        git_repo, "resolve_git_reference", lambda *args: CHECKOUT["git_commit_hash"]
    )
    args = CHECKOUT_ARGS.copy()
    args[args.index("--commit") + 1] = "v6.12"
    result = api["invoke"](args + ["--builds", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["commit"] == CHECKOUT["git_commit_hash"]


def test_missing_latest_selects_one_checkout(api, monkeypatch):
    monkeypatch.setattr(
        git_repo, "get_latest_commit", lambda *args: SECOND["git_commit_hash"]
    )
    args = CHECKOUT_ARGS.copy()
    index = args.index("--commit")
    del args[index : index + 2]
    result = api["invoke"](args + ["--latest", "--boots", "--json"])
    assert result.exit_code == 0, result.output
    assert [item["commit"] for item in json.loads(result.output)] == [
        SECOND["git_commit_hash"]
    ]


def test_missing_git_folder_selects_local_checkout_without_scanning_all(api, tmp_path):
    repo = git.Repo.init(
        tmp_path / "linux", initial_branch="aliceinwire/missing-issues"
    )
    actor = git.Actor("Test User", "test@example.org")
    commit = repo.index.commit("Initial commit", author=actor, committer=actor).hexsha
    repo.create_remote("origin", CHECKOUT["git_repository_url"])
    result = api["invoke"](
        [
            "--git-folder",
            str(repo.working_tree_dir),
            "--tree",
            "mainline",
            "--builds",
            "--json",
        ]
    )
    assert result.exit_code == 0, result.output
    record = json.loads(result.output)[0]
    assert record["commit"] == commit
    assert record["branch"] == "aliceinwire/missing-issues"
    assert record["giturl"] == CHECKOUT["git_repository_url"]
    assert not any(path == "tree" for path, _ in api["calls"])


@pytest.mark.parametrize("payload", [None, {}, {"issues": []}])
def test_missing_rejects_malformed_issue_responses(api, payload):
    api["responses"]["build/a-builds-missing/issues"] = payload
    result = api["invoke"](CHECKOUT_ARGS + ["--builds", "--json"])
    assert result.exit_code != 0
    assert '"type"' not in result.output


@pytest.mark.parametrize("use_json", [False, True])
def test_missing_does_not_publish_a_partial_report_after_later_failure(api, use_json):
    api["responses"]["build/b-builds-missing/issues"] = {
        "error": "Database unavailable"
    }
    result = api["invoke"](["--builds"] + (["--json"] if use_json else []))
    assert result.exit_code != 0
    assert "Database unavailable" in result.output
    assert "a-builds-missing" not in result.output


@pytest.mark.parametrize("status", ["FAIL", "MISS", "SKIP", None])
def test_missing_preserves_nonpassing_status(api, status):
    api["responses"][f"tree/{CHECKOUT['git_commit_hash']}/boots"] = {
        "boots": [{"id": "a-boots-missing", "status": status, "log_url": None}]
    }
    result = api["invoke"](CHECKOUT_ARGS + ["--boots", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["status"] == status


def test_missing_text_keeps_each_commits_ids_and_omits_raw_data(capsys):
    print_missing_data(
        "boots",
        [
            ["mainline/master", "commit-a", [{"boot-a": "FAIL"}]],
            ["mainline/master", "commit-b", [{"boot-b": "ERROR"}]],
            ["stable/master", "commit-c", [{"boot-c": "MISS"}]],
        ],
    )
    output = capsys.readouterr().out
    first, second = output.split("Commit:commit-b")
    assert "/test/boot-a" in first
    assert "/test/boot-b" not in first
    assert "/test/boot-c" not in first
    second, third = second.split("Commit:commit-c")
    assert "/test/boot-b" in second
    assert "/test/boot-a" not in second
    assert "/test/boot-c" not in second
    assert "/test/boot-c" in third
    assert "[['mainline/master'" not in output
