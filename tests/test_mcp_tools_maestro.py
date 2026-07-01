from unittest.mock import Mock

import pytest

pytest.importorskip("mcp")

from kcidev.mcp import tools_maestro
from kcidev.mcp.errors import ToolExecutionError


def test_retry_job_returns_result(monkeypatch):
    send = Mock(return_value={"message": "OK"})
    monkeypatch.setattr(tools_maestro, "send_jobretry", send)
    result = tools_maestro._retry_job("https://pipeline/", "tok", "node1")
    assert result == {"message": "OK"}
    send.assert_called_once_with("https://pipeline/", "node1", "tok")


def test_retry_job_failure_raises(monkeypatch):
    monkeypatch.setattr(tools_maestro, "send_jobretry", Mock(return_value=None))
    with pytest.raises(ToolExecutionError, match="node1"):
        tools_maestro._retry_job("https://pipeline/", "tok", "node1")


def test_trigger_checkout_passes_kwargs(monkeypatch):
    send = Mock(return_value={"treeid": "t1"})
    monkeypatch.setattr(tools_maestro, "send_checkout_full", send)
    result = tools_maestro._trigger_checkout(
        "https://pipeline/",
        "tok",
        "https://git.example.org/linux.git",
        "master",
        "deadbeef",
        ["baseline-arm64"],
        None,
    )
    assert result == {"treeid": "t1"}
    send.assert_called_once_with(
        "https://pipeline/",
        "tok",
        giturl="https://git.example.org/linux.git",
        branch="master",
        commit="deadbeef",
        job_filter=["baseline-arm64"],
    )


def test_trigger_checkout_includes_platform_filter(monkeypatch):
    send = Mock(return_value={"treeid": "t1"})
    monkeypatch.setattr(tools_maestro, "send_checkout_full", send)
    tools_maestro._trigger_checkout(
        "https://pipeline/",
        "tok",
        "https://git.example.org/linux.git",
        "master",
        "deadbeef",
        ["baseline-arm64"],
        ["qemu-arm64"],
    )
    assert send.call_args.kwargs["platform_filter"] == ["qemu-arm64"]


def test_trigger_checkout_failure_raises(monkeypatch):
    monkeypatch.setattr(tools_maestro, "send_checkout_full", Mock(return_value=None))
    with pytest.raises(ToolExecutionError, match="deadbeef"):
        tools_maestro._trigger_checkout(
            "https://pipeline/",
            "tok",
            "https://git.example.org/linux.git",
            "master",
            "deadbeef",
            ["baseline-arm64"],
            None,
        )
