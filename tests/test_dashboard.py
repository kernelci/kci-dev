from unittest.mock import Mock

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
