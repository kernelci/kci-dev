"""Focused tests for library helpers and command edge cases."""

import gzip
import os
import subprocess
from unittest.mock import Mock

import click
import pytest
from click.testing import CliRunner

from kcidev.libs import files, git_repo, job_filters
from kcidev.libs.common import config_path, load_toml
from kcidev.subcommands import bisect, checkout, commit
from kcidev.subcommands.config import add_config, check_configuration, config
from kcidev.subcommands.mcp import mcp
from kcidev.subcommands.testretry import testretry as retry_command
from kcidev.subcommands.watch import watch


def test_load_toml_reads_explicit_settings(tmp_path):
    settings = tmp_path / "kci-dev.toml"
    settings.write_text(
        '[staging]\napi = "https://api.example.org/"\n'
        'pipeline = "https://pipeline.example.org/"\n'
        'token = "secret"\ndefault_instance = "staging"\n',
        encoding="utf-8",
    )

    assert load_toml(str(settings), "checkout")["staging"]["api"].startswith(
        "https://api"
    )
    assert config_path(str(settings)) == str(settings)


def test_load_toml_missing_required_config_aborts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    with pytest.raises(click.Abort):
        load_toml("missing.toml", "checkout")


def test_config_command_creates_private_example_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    target = tmp_path / "nested" / "kci-dev.toml"
    result = CliRunner().invoke(
        config,
        ["--file-path", str(target)],
        obj={"SETTINGS": str(tmp_path / "missing.toml")},
    )

    assert result.exit_code == 0, result.output
    assert target.exists()
    assert "default_instance" in target.read_text(encoding="utf-8")
    assert oct(target.stat().st_mode & 0o777) == "0o600"


def test_add_config_rejects_directory(tmp_path):
    with pytest.raises(click.Abort):
        add_config(str(tmp_path))


def test_check_configuration_rejects_existing_explicit_file(tmp_path):
    existing = tmp_path / "kci-dev.toml"
    existing.write_text("", encoding="utf-8")

    with pytest.raises(click.Abort):
        check_configuration(str(existing))


def test_bisect_state_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state = dict(bisect.default_state, giturl="https://git.example/linux.git")

    assert bisect.load_state(str(path)) is None
    bisect.save_state(state, str(path))
    assert bisect.load_state(str(path)) == state


def test_bisect_new_state_has_independent_mutable_values():
    state = bisect.new_state()

    state["history"].append({"deadbeef": "bad"})
    state["job_filter"].append("baseline")
    state["platform_filter"].append("qemu-x86")

    assert bisect.default_state["history"] == []
    assert bisect.default_state["job_filter"] == []
    assert bisect.default_state["platform_filter"] == []


def test_bisect_completed_state_exits_immediately(tmp_path, monkeypatch):
    first_bad = "deadbeef"
    state = bisect.new_state()
    state.update(
        {
            "giturl": "https://git.example/linux.git",
            "branch": "main",
            "good": "good",
            "bad": "bad",
            "workdir": str(tmp_path),
            "bisect_init": True,
            "next_commit": None,
            "first_bad": first_bad,
        }
    )
    bisect.save_state(state, str(tmp_path / "state.json"))
    update_tree = Mock()
    bisection_loop = Mock()
    monkeypatch.setattr(bisect, "update_tree", update_tree)
    monkeypatch.setattr(bisect, "bisection_loop", bisection_loop)

    result = CliRunner().invoke(
        bisect.bisect,
        ["--workdir", str(tmp_path)],
        obj={"CFG": {}, "INSTANCE": None},
    )

    assert result.exit_code == 0, result.output
    assert f"Bisection already complete. First bad commit: {first_bad}" in result.output
    update_tree.assert_not_called()
    bisection_loop.assert_not_called()


def _commit_file(repo, name, contents):
    (repo / name).write_text(contents, encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", contents.strip()], cwd=repo, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _init_git_repo(repo):
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.org"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)


def test_git_exec_getcommit_detects_completed_real_bisect(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    good = _commit_file(repo, "one", "one\n")
    first_bad = _commit_file(repo, "two", "two\n")
    bad = _commit_file(repo, "three", "three\n")
    subprocess.run(["git", "bisect", "start", bad, good], cwd=repo, check=True)
    monkeypatch.chdir(repo)

    commit, complete = bisect.git_exec_getcommit(["git", "bisect", "bad"])

    assert complete is True
    assert commit == first_bad


def test_execute_cmdline_raises_click_exception_on_failure():
    with pytest.raises(click.ClickException, match="exit code 7"):
        bisect.execute_cmdline(
            ["sh", "-c", "exit 7"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def test_kcidev_exec_streams_stdout_and_stderr(capsys):
    process = bisect.kcidev_exec(
        [
            "sh",
            "-c",
            "printf 'standard output\\n'; printf 'error output\\n' >&2; exit 7",
        ]
    )

    output = capsys.readouterr().out
    assert "standard output\n" in output
    assert "error output\n" in output
    assert process.returncode == 7


@pytest.mark.parametrize(
    ("returncodes", "expected_result"),
    [([1, 1, 1], "bad"), ([1, 0], "good")],
)
def test_bisection_loop_retries_failures_before_marking_commit(
    tmp_path, monkeypatch, returncodes, expected_result
):
    state = bisect.new_state()
    state.update(
        {
            "giturl": "https://git.example/linux.git",
            "branch": "main",
            "retry_fail": 2,
            "test": "baseline.login",
            "workdir": str(tmp_path),
            "next_commit": "deadbeef",
        }
    )
    executions = [Mock(returncode=code) for code in returncodes]
    kcidev_exec = Mock(side_effect=executions)
    git_exec_getcommit = Mock(return_value=("cafebabe", False))
    monkeypatch.setattr(bisect, "kcidev_exec", kcidev_exec)
    monkeypatch.setattr(bisect, "git_exec_getcommit", git_exec_getcommit)

    result = bisect.bisection_loop(state)

    assert kcidev_exec.call_count == len(returncodes)
    git_exec_getcommit.assert_called_once_with(["git", "bisect", expected_result])
    assert result["history"] == [{"deadbeef": expected_result}]


def test_bisect_rejects_negative_retry_count():
    result = CliRunner().invoke(
        bisect.bisect,
        ["--retry-fail", "-1"],
        obj={"CFG": {}, "INSTANCE": None},
    )

    assert result.exit_code == 2
    assert "not in the range x>=0" in result.output


def test_update_tree_preserves_bisect_commit_when_resuming(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    _init_git_repo(origin)
    good = _commit_file(origin, "one", "one\n")
    _commit_file(origin, "two", "two\n")
    bad = _commit_file(origin, "three", "three\n")
    worktree = tmp_path / "worktree"
    subprocess.run(
        ["git", "clone", "--branch", "main", str(origin), str(worktree)],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "bisect", "start", bad, good], cwd=worktree, check=True)
    saved_next_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    repo = bisect.update_tree(str(worktree), "main", str(origin), reset=False)

    assert repo.head.commit.hexsha == saved_next_commit
    assert saved_next_commit != bad


def test_commit_find_diff_returns_latest_patch(tmp_path):
    subprocess.run(
        ["git", "init", "-b", "master", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.org"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "base.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=tmp_path, check=True)
    (tmp_path / "feature.txt").write_text("feature\n", encoding="utf-8")
    subprocess.run(["git", "add", "feature.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "feature"], cwd=tmp_path, check=True)

    diff = commit.find_diff(str(tmp_path), "feature", "master", "linux")

    assert "feature.txt" in diff
    assert "feature" in diff


def test_checkout_retrieve_tot_commit_success(monkeypatch):
    process = Mock(returncode=0)
    process.communicate.return_value = (b"deadbeef\trefs/heads/main\n", b"")
    popen = Mock(return_value=process)
    monkeypatch.setattr(checkout.subprocess, "Popen", popen)

    assert (
        checkout.retrieve_tot_commit("https://git.example/linux.git", "main")
        == "deadbeef"
    )
    popen.assert_called_once()


def test_checkout_retrieve_tot_commit_failure(monkeypatch):
    process = Mock(returncode=128)
    process.communicate.return_value = (b"", b"fatal")
    monkeypatch.setattr(checkout.subprocess, "Popen", Mock(return_value=process))

    assert checkout.retrieve_tot_commit("https://git.example/linux.git", "main") is None


def test_files_download_logs_to_file_decompresses_and_sanitizes(tmp_path, monkeypatch):
    response = Mock(content=gzip.compress(b"boot log\n"))
    response.raise_for_status.return_value = None
    monkeypatch.setattr(files.kcidev_session, "get", Mock(return_value=response))
    monkeypatch.chdir(tmp_path)

    url = files.download_logs_to_file("https://logs.example/log.gz", "bad/name:log.txt")

    assert url == f"file://{tmp_path / 'badnamelog.txt'}"
    assert (tmp_path / "badnamelog.txt").read_bytes() == b"boot log\n"


def test_git_repo_repository_url_cleaner_removes_credentials_and_normalizes_scheme():
    assert (
        git_repo.repository_url_cleaner(
            "ssh://user:pass@git.example.org:2222/linux.git"
        )
        == "https://git.example.org:2222/linux.git"
    )


def test_job_filters_cover_tree_hardware_and_test_regexes():
    item = {
        "tree_name": "mainline",
        "environment_misc": {"platform": "qemu-arm64"},
        "environment_compatible": ["linux,dummy"],
        "path": "baseline.login",
    }

    assert job_filters.TreeFilter("main.*").matches(item)
    assert job_filters.HardwareRegexFilter("qemu.*").matches(item)
    assert job_filters.HardwareRegexFilter("linux,.*").matches(item)
    assert job_filters.TestRegexFilter("baseline\\..*").matches(item)
    assert not job_filters.TreeFilter("next").matches(item)


def test_testretry_sends_retry_and_prints_message(monkeypatch):
    send = Mock(return_value={"message": "retry queued"})
    monkeypatch.setattr("kcidev.subcommands.testretry.send_jobretry", send)
    result = CliRunner().invoke(
        retry_command,
        ["--nodeid", "node-1"],
        obj={
            "CFG": {"staging": {"pipeline": "https://pipeline/", "token": "secret"}},
            "INSTANCE": "staging",
        },
    )

    assert result.exit_code == 0, result.output
    assert "retry queued" in result.output
    send.assert_called_once_with("https://pipeline/", "node-1", "secret")


def test_mcp_missing_instance_aborts():
    result = CliRunner().invoke(
        mcp,
        [],
        obj={"CFG": {"staging": {"api": "https://api/"}}, "INSTANCE": "missing"},
    )

    assert result.exit_code != 0
    assert (
        "Instance missing not found" in result.output
        or "MCP support is not installed" in result.output
    )


def test_watch_forwards_filters_to_watch_jobs(monkeypatch):
    watch_jobs = Mock(return_value=True)
    monkeypatch.setattr(
        "kcidev.subcommands.watch.maestro_get_node",
        Mock(return_value={"treeid": "tree-1"}),
    )
    monkeypatch.setattr("kcidev.subcommands.watch.maestro_watch_jobs", watch_jobs)
    result = CliRunner().invoke(
        watch,
        ["--nodeid", "node-1", "--job-filter", "baseline", "--test", "login"],
        obj={
            "CFG": {
                "staging": {
                    "pipeline": "https://pipeline/",
                    "api": "https://api/",
                    "token": "secret",
                }
            },
            "INSTANCE": "staging",
        },
    )

    assert result.exit_code == 0, result.output
    watch_jobs.assert_called_once_with(
        "https://api/", "secret", "tree-1", ("baseline",), "login", root_node="checkout"
    )
