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


def test_config_command_creates_private_example_file(tmp_path):
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


def test_commit_find_diff_returns_latest_patch(tmp_path):
    repo = subprocess.run(
        ["git", "init", str(tmp_path)], check=True, capture_output=True, text=True
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
        "https://api/", "secret", "tree-1", ("baseline",), "login"
    )
