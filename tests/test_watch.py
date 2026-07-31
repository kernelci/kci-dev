from unittest.mock import Mock

from click.testing import CliRunner

from kcidev.subcommands import watch as watch_module
from kcidev.subcommands.watch import watch


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


def _invoke_watch(monkeypatch, node):
    monkeypatch.setattr(watch_module, "maestro_get_node", Mock(return_value=node))
    watch_jobs = Mock()
    monkeypatch.setattr(watch_module, "maestro_watch_jobs", watch_jobs)
    runner = CliRunner()
    result = runner.invoke(
        watch,
        ["--nodeid", "0" * 24, "--job-filter", "job1"],
        obj=_cli_obj(),
    )
    return result, watch_jobs


def test_watch_uses_patchset_root_for_patchset_node(monkeypatch):
    node = {"name": "patchset", "treeid": "t1"}
    result, watch_jobs = _invoke_watch(monkeypatch, node)
    assert result.exit_code == 0
    watch_jobs.assert_called_once_with(
        "https://api.example.org/",
        "token123",
        "t1",
        ("job1",),
        None,
        root_node="patchset",
    )


def test_watch_uses_checkout_root_by_default(monkeypatch):
    node = {"name": "checkout", "treeid": "t1"}
    result, watch_jobs = _invoke_watch(monkeypatch, node)
    assert result.exit_code == 0
    watch_jobs.assert_called_once_with(
        "https://api.example.org/",
        "token123",
        "t1",
        ("job1",),
        None,
        root_node="checkout",
    )


def test_watch_requires_job_filter(monkeypatch):
    get_node = Mock()
    watch_jobs = Mock()
    monkeypatch.setattr(watch_module, "maestro_get_node", get_node)
    monkeypatch.setattr(watch_module, "maestro_watch_jobs", watch_jobs)

    result = CliRunner().invoke(
        watch,
        ["--nodeid", "0" * 24],
        obj=_cli_obj(),
    )

    assert result.exit_code == 2
    assert "Missing option '--job-filter'" in result.output
    get_node.assert_not_called()
    watch_jobs.assert_not_called()
