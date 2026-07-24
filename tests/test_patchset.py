from unittest.mock import Mock

import click
import pytest
from click.testing import CliRunner

from kcidev.subcommands import patchset as patchset_module
from kcidev.subcommands.patchset import load_patch_files, patchset


@pytest.fixture
def patch_file(tmp_path):
    path = tmp_path / "0001-test.patch"
    path.write_text("diff --git a/Makefile b/Makefile\n+EXTRAVERSION = -test\n")
    return str(path)


def _cli_obj():
    return {
        "CFG": {
            "test": {
                "pipeline": "https://pipeline.example.org/",
                "api": "https://api.example.org/",
                "token": "token123",
            }
        },
        "INSTANCE": "test",
    }


def test_load_patch_files_returns_contents_in_order(tmp_path):
    first = tmp_path / "first.patch"
    first.write_text("first content")
    second = tmp_path / "second.patch"
    second.write_text("second content")
    assert load_patch_files([str(first), str(second)]) == [
        "first content",
        "second content",
    ]


def test_load_patch_files_rejects_empty_file(tmp_path):
    empty = tmp_path / "empty.patch"
    empty.write_text("")
    with pytest.raises(click.ClickException, match="empty"):
        load_patch_files([str(empty)])


def test_load_patch_files_rejects_binary_file(tmp_path):
    binary = tmp_path / "binary.patch"
    binary.write_bytes(b"diff\x00data")
    with pytest.raises(click.ClickException, match="binary"):
        load_patch_files([str(binary)])


def test_load_patch_files_rejects_invalid_utf8(tmp_path):
    invalid = tmp_path / "invalid.patch"
    invalid.write_bytes(b"diff \x80\x81 data")
    with pytest.raises(click.ClickException, match="UTF-8"):
        load_patch_files([str(invalid)])


def test_load_patch_files_rejects_oversized_file(tmp_path):
    big = tmp_path / "big.patch"
    big.write_bytes(b"a" * (10 * 1024 * 1024 + 1))
    with pytest.raises(click.ClickException, match="large"):
        load_patch_files([str(big)])


def test_load_patch_files_rejects_too_many_files(tmp_path):
    paths = []
    for i in range(33):
        path = tmp_path / f"{i}.patch"
        path.write_text("content")
        paths.append(str(path))
    with pytest.raises(click.ClickException, match="[Tt]oo many"):
        load_patch_files(paths)


def test_patchset_rejects_patch_and_patchurl_together(patch_file):
    runner = CliRunner()
    result = runner.invoke(
        patchset,
        [
            "--nodeid",
            "0" * 24,
            "--patch",
            patch_file,
            "--patchurl",
            "https://patchwork.kernel.org/series/1/mbox/",
        ],
        obj=_cli_obj(),
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_patchset_requires_patch_or_patchurl():
    runner = CliRunner()
    result = runner.invoke(patchset, ["--nodeid", "0" * 24], obj=_cli_obj())
    assert result.exit_code != 0
    assert "--patch or --patchurl" in result.output


def test_patchset_submits_inline_patches(monkeypatch, patch_file):
    send = Mock(return_value={"message": "OK", "node": {"id": "n1", "treeid": "t1"}})
    monkeypatch.setattr(patchset_module, "send_patchset", send)
    runner = CliRunner()
    result = runner.invoke(
        patchset,
        [
            "--nodeid",
            "0" * 24,
            "--patch",
            patch_file,
            "--job-filter",
            "baseline-x86",
        ],
        obj=_cli_obj(),
    )
    assert result.exit_code == 0
    send.assert_called_once_with(
        "https://pipeline.example.org/",
        "token123",
        "0" * 24,
        patches=["diff --git a/Makefile b/Makefile\n+EXTRAVERSION = -test\n"],
        patchurls=None,
        job_filter=["baseline-x86"],
        platform_filter=None,
    )
    assert "OK" in result.output
    assert "t1" in result.output
    assert "n1" in result.output


def test_patchset_submits_patch_urls(monkeypatch):
    send = Mock(return_value={"message": "OK", "node": {"id": "n1", "treeid": "t1"}})
    monkeypatch.setattr(patchset_module, "send_patchset", send)
    runner = CliRunner()
    result = runner.invoke(
        patchset,
        [
            "--nodeid",
            "0" * 24,
            "--patchurl",
            "https://patchwork.kernel.org/series/1/mbox/",
        ],
        obj=_cli_obj(),
    )
    assert result.exit_code == 0
    send.assert_called_once_with(
        "https://pipeline.example.org/",
        "token123",
        "0" * 24,
        patches=None,
        patchurls=["https://patchwork.kernel.org/series/1/mbox/"],
        job_filter=None,
        platform_filter=None,
    )


def test_patchset_failed_submission_exits_64(monkeypatch, patch_file):
    monkeypatch.setattr(patchset_module, "send_patchset", Mock(return_value=None))
    runner = CliRunner()
    result = runner.invoke(
        patchset,
        ["--nodeid", "0" * 24, "--patch", patch_file],
        obj=_cli_obj(),
    )
    assert result.exit_code == 64


def test_patchset_watch_requires_job_filter(patch_file):
    runner = CliRunner()
    result = runner.invoke(
        patchset,
        ["--nodeid", "0" * 24, "--patch", patch_file, "--watch"],
        obj=_cli_obj(),
    )
    assert "job filter" in result.output


def test_patchset_test_requires_watch(patch_file):
    runner = CliRunner()
    result = runner.invoke(
        patchset,
        ["--nodeid", "0" * 24, "--patch", patch_file, "--test", "baseline.login"],
        obj=_cli_obj(),
    )
    assert "watch" in result.output


def test_patchset_watch_calls_watch_jobs(monkeypatch, patch_file):
    send = Mock(return_value={"message": "OK", "node": {"id": "n1", "treeid": "t1"}})
    watch_jobs = Mock()
    monkeypatch.setattr(patchset_module, "send_patchset", send)
    monkeypatch.setattr(patchset_module, "maestro_watch_jobs", watch_jobs)
    runner = CliRunner()
    result = runner.invoke(
        patchset,
        [
            "--nodeid",
            "0" * 24,
            "--patch",
            patch_file,
            "--job-filter",
            "baseline-x86",
            "--watch",
            "--test",
            "baseline.login",
        ],
        obj=_cli_obj(),
    )
    assert result.exit_code == 0
    watch_jobs.assert_called_once_with(
        "https://api.example.org/",
        "token123",
        "t1",
        ("baseline-x86",),
        "baseline.login",
    )
