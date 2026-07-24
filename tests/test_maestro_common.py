import json
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


def _response(status_code=200, json_data=None):
    response = Mock(status_code=status_code)
    response.json.return_value = json_data
    return response


def test_send_patchset_posts_inline_patches(monkeypatch):
    result_json = {"message": "OK", "node": {"id": "n1", "treeid": "t1"}}
    post = Mock(return_value=_response(json_data=result_json))
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    result = maestro_common.send_patchset(
        "https://pipeline.example.org/",
        "token123",
        "0" * 24,
        patches=["patch zero content", "patch one content"],
        job_filter=["baseline-x86"],
    )
    assert result == result_json
    args, kwargs = post.call_args
    assert args[0] == "https://pipeline.example.org/api/patchset"
    assert kwargs["headers"]["Authorization"] == "token123"
    payload = json.loads(kwargs["data"])
    assert payload["nodeid"] == "0" * 24
    assert payload["patch"] == ["patch zero content", "patch one content"]
    assert payload["jobfilter"] == ["baseline-x86"]
    assert "patchurl" not in payload


def test_send_patchset_posts_patch_urls(monkeypatch):
    post = Mock(return_value=_response(json_data={"message": "OK", "node": {}}))
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    maestro_common.send_patchset(
        "https://pipeline.example.org/",
        "token123",
        "0" * 24,
        patchurls=["https://patchwork.kernel.org/series/1/mbox/"],
        platform_filter=["qemu-x86"],
    )
    _, kwargs = post.call_args
    payload = json.loads(kwargs["data"])
    assert payload["patchurl"] == ["https://patchwork.kernel.org/series/1/mbox/"]
    assert payload["platformfilter"] == ["qemu-x86"]
    assert "patch" not in payload
    assert "jobfilter" not in payload


def test_send_patchset_error_returns_none(monkeypatch):
    post = Mock(return_value=_response(status_code=500, json_data={"message": "boom"}))
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    result = maestro_common.send_patchset(
        "https://pipeline.example.org/",
        "token123",
        "0" * 24,
        patches=["patch content"],
    )
    assert result is None
