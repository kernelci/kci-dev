import importlib
import json

import click
from click.testing import CliRunner

from kcidev.subcommands.maestro.validate.helper import validation_rows_to_json

COMMIT = "a" * 40


def _stdout(result):
    return getattr(result, "stdout", result.output)


def _build_row(
    maestro_count=1,
    dashboard_count=1,
    summary_flag="✅",
    missing_ids=None,
    status_mismatch_ids=None,
):
    return [
        "mainline/master",
        COMMIT,
        maestro_count,
        dashboard_count,
        summary_flag,
        missing_ids or [],
        status_mismatch_ids or [],
    ]


def _patch_builds_command(monkeypatch, stats):
    builds_module = importlib.import_module(
        "kcidev.subcommands.maestro.validate.builds"
    )
    monkeypatch.setattr(
        builds_module,
        "set_giturl_branch_commit",
        lambda origin, giturl, branch, commit, latest, git_folder: (
            giturl,
            branch,
            commit,
        ),
    )
    monkeypatch.setattr(
        builds_module,
        "get_tree_name",
        lambda origin, giturl, branch: "mainline",
    )
    monkeypatch.setattr(
        builds_module,
        "get_build_stats",
        lambda ctx, giturl, branch, commit, tree_name, verbose, arch, raise_errors=False: stats,
    )
    return builds_module.builds


def _patch_boots_command(monkeypatch, stats):
    boots_module = importlib.import_module("kcidev.subcommands.maestro.validate.boots")
    monkeypatch.setattr(
        boots_module,
        "set_giturl_branch_commit",
        lambda origin, giturl, branch, commit, latest, git_folder: (
            giturl,
            branch,
            commit,
        ),
    )
    monkeypatch.setattr(
        boots_module,
        "get_tree_name",
        lambda origin, giturl, branch: "mainline",
    )
    monkeypatch.setattr(
        boots_module,
        "get_boot_stats",
        lambda ctx, giturl, branch, commit, tree_name, verbose, arch, raise_errors=False: stats,
    )
    return boots_module.boots


def _json_args():
    return [
        "--giturl",
        "https://example.com/linux.git",
        "--branch",
        "master",
        "--commit",
        COMMIT,
        "--days",
        "1",
        "--json",
    ]


def test_builds_json_emits_valid_json(monkeypatch):
    command = _patch_builds_command(monkeypatch, _build_row())
    result = CliRunner().invoke(command, _json_args())

    assert result.exit_code == 0
    report = json.loads(_stdout(result))
    assert report["kind"] == "builds"
    assert report["history"] is False
    assert report["summary"]["ok"] is True
    assert report["results"][0]["commit"] == COMMIT


def test_boots_json_emits_valid_json(monkeypatch):
    command = _patch_boots_command(monkeypatch, _build_row())
    result = CliRunner().invoke(command, _json_args())

    assert result.exit_code == 0
    report = json.loads(_stdout(result))
    assert report["kind"] == "boots"
    assert report["history"] is False
    assert report["summary"]["ok"] is True
    assert report["results"][0]["tree_branch"] == "mainline/master"


def test_json_mode_does_not_write_progress_to_stdout(monkeypatch):
    command = _patch_builds_command(monkeypatch, _build_row())
    result = CliRunner().invoke(command, _json_args())

    assert result.exit_code == 0
    assert "Fetching build information" not in _stdout(result)
    json.loads(_stdout(result))


def test_json_mode_redirects_internal_stdout(monkeypatch):
    builds_module = importlib.import_module(
        "kcidev.subcommands.maestro.validate.builds"
    )
    monkeypatch.setattr(
        builds_module,
        "set_giturl_branch_commit",
        lambda origin, giturl, branch, commit, latest, git_folder: (
            giturl,
            branch,
            commit,
        ),
    )
    monkeypatch.setattr(
        builds_module,
        "get_tree_name",
        lambda origin, giturl, branch: "mainline",
    )

    def get_stats(*args, **kwargs):
        print("internal progress")
        return _build_row()

    monkeypatch.setattr(builds_module, "get_build_stats", get_stats)

    result = CliRunner().invoke(builds_module.builds, _json_args())

    assert result.exit_code == 0
    assert "internal progress" not in _stdout(result)
    json.loads(_stdout(result))


def test_missing_ids_make_summary_not_ok():
    report = validation_rows_to_json(
        "builds",
        [_build_row(2, 1, "❌", missing_ids=["b-1"])],
        False,
        "maestro",
        1,
        None,
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed"] == 1
    assert report["summary"]["missing"] == 1
    assert report["results"][0]["ok"] is False


def test_status_mismatches_make_summary_not_ok():
    report = validation_rows_to_json(
        "boots",
        [_build_row(status_mismatch_ids=["job-1"])],
        False,
        "maestro",
        1,
        None,
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["failed"] == 1
    assert report["summary"]["status_mismatches"] == 1
    assert report["results"][0]["ok"] is False


def test_build_history_count_mismatch_make_summary_not_ok():
    report = validation_rows_to_json(
        "builds",
        [_build_row(2, 1, "❌")],
        True,
        "maestro",
        1,
        None,
    )

    assert report["history"] is True
    assert report["summary"]["ok"] is False
    assert report["summary"]["failed"] == 1
    assert report["results"][0]["ok"] is False


def test_json_mismatches_still_exit_zero(monkeypatch):
    command = _patch_builds_command(
        monkeypatch, _build_row(2, 1, "❌", missing_ids=["b-1"])
    )
    result = CliRunner().invoke(command, _json_args())

    assert result.exit_code == 0
    assert json.loads(_stdout(result))["summary"]["ok"] is False


def test_json_runtime_failures_exit_nonzero(monkeypatch):
    builds_module = importlib.import_module(
        "kcidev.subcommands.maestro.validate.builds"
    )
    monkeypatch.setattr(
        builds_module,
        "set_giturl_branch_commit",
        lambda origin, giturl, branch, commit, latest, git_folder: (
            giturl,
            branch,
            commit,
        ),
    )
    monkeypatch.setattr(
        builds_module,
        "get_tree_name",
        lambda origin, giturl, branch: "mainline",
    )

    def fail(*args, **kwargs):
        raise click.ClickException("API unavailable")

    monkeypatch.setattr(builds_module, "get_build_stats", fail)

    result = CliRunner().invoke(builds_module.builds, _json_args())

    assert result.exit_code != 0


def test_fail_on_mismatch_no_mismatches_exits_zero(monkeypatch):
    command = _patch_builds_command(monkeypatch, _build_row())
    args = _json_args()[:-1] + ["--fail-on-mismatch"]

    result = CliRunner().invoke(command, args)

    assert result.exit_code == 0


def test_fail_on_mismatch_missing_ids_exit_one(monkeypatch):
    command = _patch_builds_command(
        monkeypatch, _build_row(2, 1, "❌", missing_ids=["b-1"])
    )
    args = _json_args()[:-1] + ["--fail-on-mismatch"]

    result = CliRunner().invoke(command, args)

    assert result.exit_code == 1


def test_fail_on_mismatch_status_mismatches_exit_one(monkeypatch):
    command = _patch_boots_command(
        monkeypatch, _build_row(status_mismatch_ids=["job-1"])
    )
    args = _json_args()[:-1] + ["--fail-on-mismatch"]

    result = CliRunner().invoke(command, args)

    assert result.exit_code == 1


def test_fail_on_mismatch_build_history_count_mismatch_exit_one(monkeypatch):
    builds_module = importlib.import_module(
        "kcidev.subcommands.maestro.validate.builds"
    )
    monkeypatch.setattr(
        builds_module,
        "get_tree_name",
        lambda origin, giturl, branch: "mainline",
    )
    monkeypatch.setattr(
        builds_module,
        "get_builds_history_stats",
        lambda ctx, giturl, branch, tree_name, arch, days, verbose, raise_errors=False: [
            _build_row(2, 1, "❌")
        ],
    )
    args = [
        "--giturl",
        "https://example.com/linux.git",
        "--branch",
        "master",
        "--days",
        "1",
        "--history",
        "--fail-on-mismatch",
    ]

    result = CliRunner().invoke(builds_module.builds, args)

    assert result.exit_code == 1


def test_mismatch_without_fail_on_mismatch_still_exits_zero(monkeypatch):
    command = _patch_builds_command(
        monkeypatch, _build_row(2, 1, "❌", missing_ids=["b-1"])
    )
    args = _json_args()[:-1]

    result = CliRunner().invoke(command, args)

    assert result.exit_code == 0
