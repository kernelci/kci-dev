import json

import click
import pytest
from click.testing import CliRunner

from kcidev.libs.regression import RegressionReport
from kcidev.main import get_cli


def result(result_id, status, path="suite.case", platform="qemu"):
    return {
        "id": result_id,
        "origin": "maestro",
        "status": status,
        "path": path,
        "environment_misc": {"platform": platform},
        "architecture": "arm64",
        "compiler": "gcc-14",
        "config": "defconfig",
    }


def test_report_classifies_transitions_and_preserves_duplicates():
    base = {
        "tests": [
            result("r1", "PASS"),
            result("r2", "PASS"),
            result("f", "FAIL", "fixed"),
            result("p", "FAIL", "persistent"),
            result("m", "PASS", "missing"),
            result("u", "SKIP", "unstable"),
        ]
    }
    head = {
        "tests": [
            result("r3", "FAIL"),
            result("r4", "FAIL"),
            result("f2", "PASS", "fixed"),
            result("p2", "FAIL", "persistent"),
            result("n", "PASS", "new"),
            result("u2", "PASS", "unstable"),
        ]
    }
    report = RegressionReport.compare("base", "head", base, head)
    assert report.counts == {
        "regression": 2,
        "fixed": 1,
        "unstable": 1,
        "persistent_fail": 1,
        "new": 1,
        "missing": 1,
    }
    regressions = [i for i in report.items if i["category"] == "regression"]
    assert [i["occurrence"] for i in regressions] == [0, 1]
    assert regressions[0]["identity"] == {
        "kind": "test",
        "origin": "maestro",
        "platform": "qemu",
        "architecture": "arm64",
        "compiler": "gcc-14",
        "config": "defconfig",
        "path": "suite.case",
    }


def test_report_preserves_empty_head_result():
    report = RegressionReport.compare("base", "head", {}, {"tests": [{}]})

    assert report.items == [
        {
            "category": "new",
            "identity": {
                "kind": "test",
                "origin": "unknown",
                "platform": "unknown",
                "architecture": "unknown",
                "compiler": "unknown",
                "config": "unknown",
                "path": "unknown",
            },
            "occurrence": 0,
            "base_status": None,
            "head_status": None,
            "base_id": None,
            "head_id": None,
            "known_issues": [],
        }
    ]


def test_report_pairs_duplicate_results_independently_of_api_order():
    base_results = [result("base-pass", "PASS"), result("base-fail", "FAIL")]
    head_results = [result("head-fail", "FAIL"), result("head-pass", "PASS")]

    report = RegressionReport.compare(
        "base", "head", {"tests": base_results}, {"tests": head_results}
    )
    reversed_report = RegressionReport.compare(
        "base",
        "head",
        {"tests": list(reversed(base_results))},
        {"tests": list(reversed(head_results))},
    )

    assert report.to_dict() == reversed_report.to_dict()
    assert report.counts == {
        "regression": 0,
        "fixed": 0,
        "unstable": 0,
        "persistent_fail": 1,
        "new": 0,
        "missing": 0,
    }
    assert report.items[0]["base_id"] == "base-fail"
    assert report.items[0]["head_id"] == "head-fail"


def test_report_marks_unpaired_duplicate_as_missing():
    report = RegressionReport.compare(
        "base",
        "head",
        {
            "tests": [
                result("base-first", "PASS"),
                result("base-second", "PASS"),
            ]
        },
        {"tests": [result("head-only", "PASS")]},
    )

    assert report.counts == {
        "regression": 0,
        "fixed": 0,
        "unstable": 0,
        "persistent_fail": 0,
        "new": 0,
        "missing": 1,
    }
    assert report.items == [
        {
            "category": "missing",
            "identity": {
                "kind": "test",
                "origin": "maestro",
                "platform": "qemu",
                "architecture": "arm64",
                "compiler": "gcc-14",
                "config": "defconfig",
                "path": "suite.case",
            },
            "occurrence": 1,
            "base_status": "PASS",
            "head_status": None,
            "base_id": "base-second",
            "head_id": None,
            "known_issues": [],
        }
    ]


def test_history_categories_only_apply_to_matching_head_status():
    key = ("maestro", "qemu", "arm64", "gcc-14", "defconfig", "suite.case")
    regression_history = {"regression": {key}, "fixed": set(), "unstable": set()}
    assert (
        RegressionReport._classify(
            result("old", "PASS"), result("new", "PASS"), key, regression_history
        )
        is None
    )
    assert (
        RegressionReport._classify(
            result("old", "FAIL"), result("new", "PASS"), key, regression_history
        )
        == "fixed"
    )
    assert (
        RegressionReport._classify(
            result("old", "PASS"), result("new", "FAIL"), key, regression_history
        )
        == "regression"
    )
    assert (
        RegressionReport._classify(
            result("old", "FAIL"), result("new", "FAIL"), key, regression_history
        )
        == "regression"
    )

    fixed_history = {"regression": set(), "fixed": {key}, "unstable": set()}
    assert (
        RegressionReport._classify(
            result("old", "PASS"), result("new", "FAIL"), key, fixed_history
        )
        == "regression"
    )
    assert (
        RegressionReport._classify(
            result("old", "FAIL"), result("new", "FAIL"), key, fixed_history
        )
        == "persistent_fail"
    )
    assert (
        RegressionReport._classify(
            result("old", "PASS"), result("new", "PASS"), key, fixed_history
        )
        == "fixed"
    )

    unstable_history = {"regression": set(), "fixed": set(), "unstable": {key}}
    assert (
        RegressionReport._classify(
            result("old", "PASS"), result("new", "PASS"), key, unstable_history
        )
        == "unstable"
    )


def test_tree_history_uses_report_origin_and_matches_all_result_kinds():
    tree_report = {
        "origin": "maestro",
        "possible_regressions": {
            "qemu": {
                "defconfig": {
                    "arm64/gcc-14": {
                        "build": [{}],
                        "boot": [{}],
                        "suite.case": [{}],
                    }
                }
            }
        },
    }
    base = {
        "builds": [result("build-old", "FAIL", path=None)],
        "boots": [result("boot-old", "FAIL", path="boot")],
        "tests": [result("test-old", "FAIL")],
    }
    head = {
        "builds": [result("build-new", "FAIL", path=None)],
        "boots": [result("boot-new", "FAIL", path="boot")],
        "tests": [result("test-new", "FAIL")],
    }

    report = RegressionReport.compare("base", "head", base, head, tree_report)

    assert report.counts["regression"] == 3
    assert {item["identity"]["kind"] for item in report.items} == {
        "build",
        "boot",
        "test",
    }


def test_compare_json_is_one_document_and_regressions_exit_one(monkeypatch):
    report = RegressionReport("base", "head")
    report.items.append({"category": "regression"})
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.compare_results",
        lambda *args, **kwargs: report.to_dict(),
    )
    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "compare",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--format",
            "json",
            "base",
            "head",
        ],
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout)["counts"]["regression"] == 1


@pytest.mark.parametrize(
    "history",
    [
        [
            {"git_commit_hash": "head-from-history"},
            {"git_commit_hash": "base-from-history"},
        ],
        {
            "commits": [
                {"git_commit_hash": "head-from-history"},
                {"git_commit_hash": "base-from-history"},
            ]
        },
    ],
)
def test_compare_without_commits_resolves_latest_pair(monkeypatch, history):
    monkeypatch.setattr(
        "kcidev.subcommands.results.set_giturl_branch_commit",
        lambda *args, **kwargs: ("resolved-url", "resolved-branch", "latest"),
    )
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.get_commits_history",
        lambda *args, **kwargs: history,
    )
    compared = {}

    def compare(_client, base, head, giturl, branch, origin, **kwargs):
        compared["args"] = (base, head, giturl, branch, origin)
        return _report()

    monkeypatch.setattr("kcidev.api.KernelCIClient.compare_results", compare)

    result = CliRunner().invoke(
        get_cli(),
        ["results", "compare", "--giturl", "url", "--branch", "main"],
    )

    assert result.exit_code == 0
    assert compared["args"] == (
        "base-from-history",
        "head-from-history",
        "resolved-url",
        "resolved-branch",
        "maestro",
    )


@pytest.mark.parametrize("commits", [["only"], ["one", "two", "three"]])
def test_compare_rejects_invalid_positional_commit_counts(commits):
    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "compare",
            "--giturl",
            "url",
            "--branch",
            "main",
            *commits,
        ],
    )

    assert result.exit_code == 2
    assert "provide either zero commits or exactly BASE and HEAD" in result.output


def test_compare_preserves_two_explicit_commits(monkeypatch):
    compared = {}

    def compare(_client, base, head, giturl, branch, origin, **kwargs):
        compared["commits"] = (base, head)
        return _report()

    monkeypatch.setattr("kcidev.api.KernelCIClient.compare_results", compare)
    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "compare",
            "--giturl",
            "url",
            "--branch",
            "main",
            "base-explicit",
            "head-explicit",
        ],
    )

    assert result.exit_code == 0
    assert compared["commits"] == ("base-explicit", "head-explicit")


def test_compare_json_history_failure_is_one_document(monkeypatch):
    monkeypatch.setattr(
        "kcidev.subcommands.results.set_giturl_branch_commit",
        lambda *args, **kwargs: ("url", "main", "latest"),
    )
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.get_commits_history",
        lambda *args, **kwargs: {"commits": [{"git_commit_hash": "only"}]},
    )

    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "compare",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 2
    assert result.stdout.count("\n") == 1
    assert json.loads(result.stdout) == {
        "error": "fewer than two checkouts are available",
        "incomplete": True,
    }


def test_compare_json_history_request_failure_is_one_document(monkeypatch):
    from kcidev.api import KciDevError

    monkeypatch.setattr(
        "kcidev.subcommands.results.set_giturl_branch_commit",
        lambda *args, **kwargs: ("url", "main", "latest"),
    )

    def fail_history(*args, **kwargs):
        raise KciDevError("Dashboard history request failed")

    monkeypatch.setattr("kcidev.api.KernelCIClient.get_commits_history", fail_history)

    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "compare",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 2
    assert result.stdout.count("\n") == 1
    assert json.loads(result.stdout) == {
        "error": "Dashboard history request failed",
        "incomplete": True,
    }


def test_gate_rejects_unknown_fail_on_categories_before_comparison(monkeypatch):
    def unexpected_comparison(*args, **kwargs):
        raise AssertionError("comparison should not run for an invalid policy")

    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.compare_results", unexpected_comparison
    )
    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "gate",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--base",
            "base",
            "--head",
            "head",
            "--fail-on",
            "unknown, regression, typo",
        ],
    )

    assert result.exit_code == 2
    assert "unknown --fail-on categories: typo, unknown" in result.output


def test_gate_handles_abort_while_resolving_latest_checkout(monkeypatch):
    def abort_resolution(*args, **kwargs):
        raise click.Abort()

    monkeypatch.setattr(
        "kcidev.subcommands.results.set_giturl_branch_commit", abort_resolution
    )
    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "gate",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout) == {"error": "", "incomplete": True}


def _report(**counts):
    return {
        "base": "base",
        "head": "head",
        "counts": {
            category: counts.get(category, 0)
            for category in (
                "regression",
                "fixed",
                "unstable",
                "persistent_fail",
                "new",
                "missing",
            )
        },
        "incomplete": counts.get("incomplete", False),
        "items": [],
    }


def test_gate_parses_fail_on_list_and_exits_for_selected_category(monkeypatch):
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.compare_results",
        lambda *args, **kwargs: _report(fixed=1),
    )

    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "gate",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--base",
            "base",
            "--head",
            "head",
            "--fail-on",
            " regression, , fixed,regression ",
        ],
    )

    assert result.exit_code == 1
    assert "fixed: 1" in result.stdout


def test_gate_exits_zero_when_policy_has_no_violations(monkeypatch):
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.compare_results",
        lambda *args, **kwargs: _report(fixed=1),
    )

    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "gate",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--base",
            "base",
            "--head",
            "head",
            "--fail-on",
            "regression",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["counts"]["fixed"] == 1


def test_gate_exits_two_for_incomplete_report_before_policy(monkeypatch):
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.compare_results",
        lambda *args, **kwargs: _report(regression=1, incomplete=True),
    )

    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "gate",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--base",
            "base",
            "--head",
            "head",
        ],
    )

    assert result.exit_code == 2


def test_gate_requires_base_and_head_together():
    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "gate",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--base",
            "base",
        ],
    )

    assert result.exit_code == 2
    assert "provide both --base and --head, or neither" in result.output


def test_gate_resolves_latest_pair_from_history_dictionary(monkeypatch):
    monkeypatch.setattr(
        "kcidev.subcommands.results.set_giturl_branch_commit",
        lambda *args, **kwargs: ("resolved-url", "resolved-branch", "latest"),
    )
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.get_commits_history",
        lambda *args, **kwargs: {
            "commits": [
                {"git_commit_hash": "head-from-history"},
                {"git_commit_hash": "base-from-history"},
            ]
        },
    )
    compared = {}

    def compare(_client, base, head, giturl, branch, origin):
        compared["args"] = (base, head, giturl, branch, origin)
        return _report()

    monkeypatch.setattr("kcidev.api.KernelCIClient.compare_results", compare)

    result = CliRunner().invoke(
        get_cli(),
        ["results", "gate", "--giturl", "url", "--branch", "main"],
    )

    assert result.exit_code == 0
    assert compared["args"] == (
        "base-from-history",
        "head-from-history",
        "resolved-url",
        "resolved-branch",
        "maestro",
    )


def test_gate_accepts_list_history(monkeypatch):
    monkeypatch.setattr(
        "kcidev.subcommands.results.set_giturl_branch_commit",
        lambda *args, **kwargs: ("url", "main", "latest"),
    )
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.get_commits_history",
        lambda *args, **kwargs: [
            {"git_commit_hash": "head"},
            {"git_commit_hash": "base"},
        ],
    )
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.compare_results",
        lambda *args, **kwargs: _report(),
    )

    result = CliRunner().invoke(
        get_cli(),
        ["results", "gate", "--giturl", "url", "--branch", "main"],
    )

    assert result.exit_code == 0


def test_gate_exits_two_when_history_has_fewer_than_two_commits(monkeypatch):
    monkeypatch.setattr(
        "kcidev.subcommands.results.set_giturl_branch_commit",
        lambda *args, **kwargs: ("url", "main", "latest"),
    )
    monkeypatch.setattr(
        "kcidev.api.KernelCIClient.get_commits_history",
        lambda *args, **kwargs: {"commits": [{"git_commit_hash": "only"}]},
    )

    result = CliRunner().invoke(
        get_cli(),
        [
            "results",
            "gate",
            "--giturl",
            "url",
            "--branch",
            "main",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout) == {
        "error": "fewer than two checkouts are available",
        "incomplete": True,
    }
