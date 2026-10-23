import importlib
import json
from copy import deepcopy
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from kcidev.main import get_cli
from kcidev.subcommands.results.parser import cmd_tree_report, status_mapping

GIT_URL = "https://example.test/linux.git"
ARGS = ["results", "tree-report", "--giturl", GIT_URL, "--branch", "master"]


def _report(category="possible_regressions"):
    history = {
        "board": {
            "defconfig": {
                "arm64/gcc": {
                    "boot": [
                        {"id": "latest", "status": "FAIL"},
                        {"id": "older", "status": "ERROR"},
                        {"id": "oldest", "status": "PASS"},
                    ]
                }
            }
        }
    }
    return {
        "dashboard_url": "https://dashboard.example.test/tree/demo",
        "commit_hash": "a" * 40,
        "origin": "maestro",
        "checkout_start_time": "2026-10-22T00:00:00Z",
        "build_status_summary": {},
        "boot_status_summary": {},
        "test_status_summary": {},
        "possible_regressions": history if category == "possible_regressions" else {},
        "fixed_regressions": history if category == "fixed_regressions" else {},
        "unstable_tests": history if category == "unstable_tests" else {},
        "issues": {"builds": []},
    }


@pytest.fixture
def invoke(monkeypatch):
    main = importlib.import_module("kcidev.main")
    results = importlib.import_module("kcidev.subcommands.results")
    monkeypatch.setattr(main, "load_toml", lambda *args: None)

    def forbid_network(*args, **kwargs):
        pytest.fail("Tree-report rendering tests must not make network requests")

    monkeypatch.setattr("requests.sessions.Session.request", forbid_network)

    def run(data, extra):
        fetch = Mock(return_value=data)
        monkeypatch.setattr(results, "dashboard_fetch_tree_report", fetch)
        result = CliRunner().invoke(get_cli(), ARGS + extra)
        if result.exit_code == 0:
            fetch.assert_called_once_with(
                "maestro", "master", GIT_URL, "--json" in extra, (), 3, 24, 0
            )
        return result

    return run


@pytest.mark.parametrize(
    "status,emoji,text",
    [
        ("PASS", "✅", "PASS"),
        ("FAIL", "❌", "FAIL"),
        ("ERROR", "⚠️", "OTHER"),
        ("SKIP", "⚠️", "OTHER"),
        ("MISS", "⚠️", "OTHER"),
        ("DONE", "⚠️", "OTHER"),
        ("NULL", "⚠️", "OTHER"),
        (None, "⚠️", "OTHER"),
    ],
)
@pytest.mark.parametrize("no_emoji", [False, True])
def test_status_symbols(status, emoji, text, no_emoji):
    if no_emoji:
        assert status_mapping(status, no_emoji=True) == text
        assert status_mapping(status, no_emoji=True).isascii()
    else:
        assert status_mapping(status) == emoji


@pytest.mark.parametrize(
    "category", ["possible_regressions", "fixed_regressions", "unstable_tests"]
)
@pytest.mark.parametrize("no_emoji", [False, True])
def test_cli_history_symbols_preserve_order_and_data(invoke, category, no_emoji):
    data = _report(category)
    original = deepcopy(data)
    result = invoke(data, ["--no-emoji"] if no_emoji else [])

    assert result.exit_code == 0, result.output
    history = [
        line.strip() for line in result.output.splitlines() if "history:" in line
    ]
    expected = "history:PASS > OTHER > FAIL" if no_emoji else "history:✅ > ⚠️ > ❌"
    assert history == [expected]
    if no_emoji:
        assert all(line.isascii() for line in history)
    assert data == original


@pytest.mark.parametrize("no_emoji", [False, True])
def test_cli_json_preserves_raw_response(invoke, no_emoji):
    data = _report()
    extra = ["--json", "--no-emoji"] if no_emoji else ["--json"]
    result = invoke(data, extra)

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == data
    assert "history:" not in result.output


def test_direct_renderer_keeps_default_symbols(capsys):
    cmd_tree_report(_report(), False)
    assert "history:✅ > ⚠️ > ❌" in capsys.readouterr().out


def test_tree_report_help_describes_no_emoji():
    command = importlib.import_module("kcidev.subcommands.results").tree_report
    result = CliRunner().invoke(command, ["--help"])
    assert result.exit_code == 0
    assert "--no-emoji" in result.output
    assert "ASCII labels" in result.output
