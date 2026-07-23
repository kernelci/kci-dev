from unittest.mock import Mock

from click.testing import CliRunner

from kcidev.libs import dashboard


def test_dashboard_api_fetch_retries_retryable_status(monkeypatch):
    retry_response = Mock(status_code=504)
    success_response = Mock(status_code=200)
    success_response.json.return_value = {"ok": True}

    get = Mock(side_effect=[retry_response, success_response])
    sleep = Mock()

    monkeypatch.setattr(dashboard.kcidev_session, "get", get)
    monkeypatch.setattr(dashboard.time, "sleep", sleep)

    result = dashboard.dashboard_api_fetch("hardware/", {}, False, max_retries=1)

    assert result == {"ok": True}
    assert get.call_count == 2
    sleep.assert_called_once_with(2)


def test_dashboard_api_defaults_to_production():
    assert dashboard.get_dashboard_api() == "https://dashboard.kernelci.org/api/"
    assert dashboard.get_dashboard_url() == "https://dashboard.kernelci.org"


def test_set_dashboard_api_normalises_trailing_slash(monkeypatch):
    monkeypatch.setattr(dashboard, "_dashboard_api", dashboard.DASHBOARD_API_DEFAULT)

    dashboard.set_dashboard_api("https://internal.example.com/api")

    assert dashboard.get_dashboard_api() == "https://internal.example.com/api/"
    assert dashboard.get_dashboard_url() == "https://internal.example.com"


def test_dashboard_api_fetch_uses_configured_url(monkeypatch):
    monkeypatch.setattr(
        dashboard, "_dashboard_api", "https://internal.example.com/api/"
    )
    response = Mock(status_code=200)
    response.json.return_value = {"ok": True}
    get = Mock(return_value=response)
    monkeypatch.setattr(dashboard.kcidev_session, "get", get)

    dashboard.dashboard_api_fetch("tree", {"origin": "maestro"}, False)

    url = get.call_args[0][0]
    assert url.startswith("https://internal.example.com/api/tree?")


def test_configure_dashboard_api_prefers_instance_over_top_level(monkeypatch):
    monkeypatch.setattr(dashboard, "_dashboard_api", dashboard.DASHBOARD_API_DEFAULT)
    cfg = {
        "dashboard_api": "https://top-level.example.com/api/",
        "internal": {"dashboard_api": "https://instance.example.com/api/"},
    }

    dashboard.configure_dashboard_api(cfg, "internal")

    assert dashboard.get_dashboard_api() == "https://instance.example.com/api/"


def test_configure_dashboard_api_falls_back_to_top_level(monkeypatch):
    monkeypatch.setattr(dashboard, "_dashboard_api", dashboard.DASHBOARD_API_DEFAULT)
    cfg = {
        "dashboard_api": "https://top-level.example.com/api/",
        "internal": {"api": "https://internal.example.com/"},
    }

    dashboard.configure_dashboard_api(cfg, "internal")

    assert dashboard.get_dashboard_api() == "https://top-level.example.com/api/"


def test_configure_dashboard_api_without_config_keeps_default(monkeypatch):
    monkeypatch.setattr(dashboard, "_dashboard_api", dashboard.DASHBOARD_API_DEFAULT)

    dashboard.configure_dashboard_api(None, None)

    assert dashboard.get_dashboard_api() == dashboard.DASHBOARD_API_DEFAULT


def test_cli_sets_dashboard_api_from_settings(tmp_path, monkeypatch):
    from kcidev.main import get_cli

    monkeypatch.setattr(dashboard, "_dashboard_api", dashboard.DASHBOARD_API_DEFAULT)
    settings = tmp_path / "kci-dev.toml"
    settings.write_text(
        'default_instance="internal"\n'
        "[internal]\n"
        'dashboard_api="https://internal.example.com/api/"\n'
    )

    runner = CliRunner()
    result = runner.invoke(
        get_cli(), ["--settings", str(settings), "results", "--help"]
    )

    assert result.exit_code == 0
    assert dashboard.get_dashboard_api() == "https://internal.example.com/api/"


def test_kernelci_client_sets_dashboard_api_from_config(monkeypatch):
    from kcidev.api import KernelCIClient

    monkeypatch.setattr(dashboard, "_dashboard_api", dashboard.DASHBOARD_API_DEFAULT)
    cfg = {
        "default_instance": "internal",
        "internal": {"dashboard_api": "https://internal.example.com/api/"},
    }

    KernelCIClient(cfg=cfg)

    assert dashboard.get_dashboard_api() == "https://internal.example.com/api/"


def test_kernelci_client_dashboard_api_argument_wins(monkeypatch):
    from kcidev.api import KernelCIClient

    monkeypatch.setattr(dashboard, "_dashboard_api", dashboard.DASHBOARD_API_DEFAULT)
    cfg = {
        "default_instance": "internal",
        "internal": {"dashboard_api": "https://instance.example.com/api/"},
    }

    KernelCIClient(cfg=cfg, dashboard_api="https://override.example.com/api/")

    assert dashboard.get_dashboard_api() == "https://override.example.com/api/"
