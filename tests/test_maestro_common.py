from unittest.mock import Mock

import click
import pytest

from kcidev.libs import maestro_common


def test_maestro_get_node_missing_raises_clean_error(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = None
    monkeypatch.setattr(
        maestro_common.kcidev_session, "get", Mock(return_value=response)
    )
    with pytest.raises(click.ClickException, match="not found"):
        maestro_common.maestro_get_node("https://api.example.org/", "0" * 24)
