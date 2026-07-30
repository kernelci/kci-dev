import json
import logging
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


def test_send_patchset_does_not_log_patch_content(monkeypatch, caplog):
    post = Mock(return_value=_response(json_data={"message": "OK", "node": {}}))
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    with caplog.at_level(logging.DEBUG):
        maestro_common.send_patchset(
            "https://pipeline.example.org/",
            "token123",
            "0" * 24,
            patches=["SECRET-PATCH-CONTENT"],
        )
    assert "SECRET-PATCH-CONTENT" not in caplog.text


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


def test_maestro_check_node_available_patchset_root_is_done():
    node = {"name": "patchset", "state": "available", "result": None}
    assert maestro_common.maestro_check_node(node, root_node="patchset") == "DONE"


def test_maestro_check_node_available_checkout_still_done_by_default():
    node = {"name": "checkout", "state": "available", "result": None}
    assert maestro_common.maestro_check_node(node) == "DONE"


def test_maestro_watch_jobs_completes_with_patchset_root(monkeypatch):
    nodes = [
        {
            "name": "patchset",
            "state": "done",
            "result": "pass",
            "kind": "checkout",
            "id": "p1",
            "updated": "now",
        },
        {
            "name": "job1",
            "state": "done",
            "result": "pass",
            "kind": "job",
            "id": "j1",
            "updated": "now",
        },
    ]
    monkeypatch.setattr(
        maestro_common, "maestro_retrieve_treeid_nodes", Mock(return_value=nodes)
    )
    monkeypatch.setattr(
        maestro_common.time,
        "sleep",
        Mock(side_effect=RuntimeError("watch loop did not finish")),
    )
    maestro_common.maestro_watch_jobs(
        "https://api.example.org/",
        "token123",
        "t1",
        ["job1"],
        None,
        root_node="patchset",
    )


def test_maestro_watch_jobs_times_out_waiting_for_test_result(monkeypatch):
    nodes = [
        {
            "name": "checkout",
            "state": "done",
            "result": "pass",
            "kind": "checkout",
            "id": "c1",
            "updated": "now",
        },
        {
            "name": "job1",
            "state": "done",
            "result": "pass",
            "kind": "job",
            "id": "j1",
            "updated": "now",
        },
    ]
    monkeypatch.setattr(
        maestro_common, "maestro_retrieve_treeid_nodes", Mock(return_value=nodes)
    )
    monkeypatch.setattr(maestro_common.time, "sleep", Mock())
    monkeypatch.setattr(
        maestro_common.time, "time", Mock(side_effect=[100, 100, 161, 161, 161])
    )

    with pytest.raises(SystemExit) as exc_info:
        maestro_common.maestro_watch_jobs(
            "https://api.example.org/", "token123", "t1", ["job1"], "missing-test"
        )

    assert exc_info.value.code == 2
