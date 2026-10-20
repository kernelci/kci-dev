import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from kcidev import KciDevError, KernelCIClient
from kcidev.libs import dashboard
from kcidev.subcommands.results import issues


@pytest.fixture
def fetch(monkeypatch):
    response = {
        "issues": [{"id": "maestro:issue", "comment": "Build failure"}],
        "extras": {"maestro:issue": {"tree_name": "mainline"}},
    }
    fetch = Mock(return_value=response)
    monkeypatch.setattr(dashboard, "dashboard_api_fetch", fetch)
    return fetch


@pytest.mark.parametrize("use_json", [False, True])
@pytest.mark.parametrize(
    "start,end,expected_start,expected_end",
    [
        ("2026-08-01", "2026-08-08", 1785542400, 1786147200),
        (
            "2026-08-01T09:00:00+09:00",
            "2026-08-07T20:00:00-04:00",
            1785542400,
            1786147200,
        ),
        (
            "2026-08-01T00:00:00.123456Z",
            "2026-08-01T00:00:00.654321Z",
            1785542400.123456,
            1785542400.654321,
        ),
        (
            "2026-08-01T09:00:00+09:00",
            "2026-08-01T00:00:00Z",
            1785542400,
            1785542400,
        ),
    ],
)
def test_cli_exact_issue_range(
    fetch, use_json, start, end, expected_start, expected_end
):
    args = ["--origin", "test", "--start-date", start, "--end-date", end]
    if use_json:
        args.append("--json")
    result = CliRunner().invoke(issues, args)

    assert result.exit_code == 0, result.output
    endpoint, params, json_mode = fetch.call_args.args
    assert endpoint == "issue/"
    assert params["filter_origin"] == "test"
    assert float(params["startTimestampInSeconds"]) == expected_start
    assert float(params["endTimestampInSeconds"]) == expected_end
    assert "interval_in_days" not in params
    assert json_mode is use_json
    if use_json:
        assert json.loads(result.output)[0]["id"] == "maestro:issue"
    else:
        assert "Build failure" in result.output


@pytest.mark.parametrize(
    "args,message",
    [
        (["--start-date", "2026-08-01"], "must be used together"),
        (["--end-date", "2026-08-08"], "must be used together"),
        (["--start-date", "invalid", "--end-date", "2026-08-08"], "--start-date"),
        (["--start-date", "2026-08-01", "--end-date", "2026-02-30"], "--end-date"),
        (["--start-date", "20260801", "--end-date", "2026-08-08"], "YYYY-MM-DD"),
        (["--start-date", "", "--end-date", "2026-08-08"], "YYYY-MM-DD"),
        (
            ["--start-date", "2026-08-01T00:00:00", "--end-date", "2026-08-08"],
            "timezone",
        ),
        (["--start-date", "2026-08-08", "--end-date", "2026-08-01"], "later than"),
        (
            [
                "--start-date",
                "2026-08-01T00:00:00Z",
                "--end-date",
                "2026-08-01T01:00:00+09:00",
            ],
            "later than",
        ),
        (
            ["--start-date", "2026-08-01", "--end-date", "2026-08-08", "--days", "5"],
            "--days",
        ),
    ],
)
def test_cli_rejects_invalid_ranges_without_request(fetch, args, message):
    result = CliRunner().invoke(issues, args)
    assert result.exit_code == 2, result.output
    assert message in result.output
    fetch.assert_not_called()


@pytest.mark.parametrize(
    "mode",
    [
        ["--new"],
        ["--missing"],
        ["--giturl", "mainline"],
        ["--arch", "arm64"],
        ["--latest"],
    ],
)
def test_cli_rejects_ranges_in_modes_that_cannot_apply_them(fetch, mode):
    result = CliRunner().invoke(
        issues, ["--start-date", "2026-08-01", "--end-date", "2026-08-08", *mode]
    )
    assert result.exit_code == 2, result.output
    assert "unfiltered issue listing" in result.output
    fetch.assert_not_called()


@pytest.fixture
def frozen_now(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is timezone.utc
            return datetime(2026, 8, 8, 12, 30, tzinfo=tz)

    monkeypatch.setattr(dashboard, "datetime", FixedDatetime)


@pytest.mark.parametrize(
    "args,days", [([], 5), (["--days", "2"], 2), (["--days", "0"], 0)]
)
def test_cli_preserves_days_window(fetch, frozen_now, args, days):
    result = CliRunner().invoke(issues, args)
    assert result.exit_code == 0, result.output
    params = fetch.call_args.args[1]
    assert float(params["endTimestampInSeconds"]) == 1786192200
    assert float(params["startTimestampInSeconds"]) == 1786192200 - days * 86400


def test_client_supports_exact_ranges(fetch):
    data = KernelCIClient().get_issue_list(
        start_date="2026-08-01", end_date="2026-08-08"
    )
    assert data["issues"][0]["id"] == "maestro:issue"
    params = fetch.call_args.args[1]
    assert "filter_origin" not in params
    assert float(params["startTimestampInSeconds"]) == 1785542400
    assert float(params["endTimestampInSeconds"]) == 1786147200


@pytest.mark.parametrize("kwargs,days", [({}, 7), ({"days": 3}, 3)])
def test_client_preserves_days_window(fetch, frozen_now, kwargs, days):
    KernelCIClient().get_issue_list(**kwargs)
    params = fetch.call_args.args[1]
    assert float(params["endTimestampInSeconds"]) == 1786192200
    assert float(params["startTimestampInSeconds"]) == 1786192200 - days * 86400


@pytest.mark.parametrize(
    "kwargs",
    [
        {"start_date": "2026-08-01"},
        {"start_date": "2026-08-01", "end_date": "invalid"},
        {"start_date": "2026-08-08", "end_date": "2026-08-01"},
        {"start_date": "2026-08-01", "end_date": "2026-08-08", "days": 7},
    ],
)
def test_client_reports_range_errors(fetch, kwargs):
    with pytest.raises(KciDevError):
        KernelCIClient().get_issue_list(**kwargs)
    fetch.assert_not_called()


def test_issue_range_help():
    result = CliRunner().invoke(issues, ["--help"])
    assert result.exit_code == 0
    assert "--start-date" in result.output
    assert "--end-date" in result.output
    assert "UTC midnight" in result.output
