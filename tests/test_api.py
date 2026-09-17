import json
from unittest.mock import Mock

import pytest
import requests

from kcidev import KciDevError, KernelCIClient, api
from kcidev.libs import maestro_common

CFG = {
    "test": {
        "api": "https://api.example.org/",
        "pipeline": "https://pipeline.example.org/",
        "token": "secret",
    }
}


def _client():
    return KernelCIClient(cfg=CFG, instance="test")


def test_client_uses_configured_default_instance(monkeypatch):
    cfg = {"default_instance": "test", **CFG}
    response = Mock(status_code=200)
    response.json.return_value = {"id": "n1"}
    get = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "get", get)

    client = KernelCIClient(cfg=cfg)

    assert client.instance == "test"
    assert client.get_node("n1") == {"id": "n1"}
    assert get.call_args[0][0] == "https://api.example.org/latest/node/n1"


def test_get_node_uses_configured_api_url(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"id": "n1", "state": "done"}
    get = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "get", get)
    assert _client().get_node("n1") == {"id": "n1", "state": "done"}
    assert get.call_args[0][0] == "https://api.example.org/latest/node/n1"


def test_get_node_without_api_url_raises():
    with pytest.raises(KciDevError, match="api URL"):
        KernelCIClient().get_node("n1")


def test_get_node_http_error_raises_library_error(monkeypatch):
    response = Mock(status_code=404)
    response.json.return_value = {"detail": "Node not found"}
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=response
    )
    monkeypatch.setattr(
        maestro_common.kcidev_session, "get", Mock(return_value=response)
    )
    with pytest.raises(KciDevError, match="Maestro node request failed"):
        _client().get_node("n1")


def test_get_node_plain_text_http_error_raises_library_error(monkeypatch):
    response = Mock(
        status_code=503,
        url="https://api.example.org/latest/node/n1",
        text="service unavailable",
    )
    response.json.side_effect = requests.exceptions.JSONDecodeError("bad", "", 0)
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=response
    )
    monkeypatch.setattr(
        maestro_common.kcidev_session, "get", Mock(return_value=response)
    )

    with pytest.raises(KciDevError, match="Maestro node request failed"):
        _client().get_node("n1")


def test_get_nodes_passes_pagination_and_filters(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = []
    get = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "get", get)
    _client().get_nodes(limit=5, offset=10, filters=["name=checkout"])
    assert get.call_args[0][0] == "https://api.example.org/latest/nodes/fast"
    assert get.call_args.kwargs["params"] == [
        ("limit", 5),
        ("offset", 10),
        ("name", "checkout"),
    ]
    assert get.call_args.kwargs["timeout"] == 30


def test_retry_job_posts_with_token(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"message": "OK"}
    post = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    assert _client().retry_job("n1") == {"message": "OK"}
    assert post.call_args[0][0] == "https://pipeline.example.org/api/jobretry"
    assert post.call_args.kwargs["headers"]["Authorization"] == "secret"


def test_pipeline_url_does_not_require_trailing_slash(monkeypatch):
    cfg = {
        "test": {
            "pipeline": "https://pipeline.example.org",
            "token": "secret",
        }
    }
    response = Mock(status_code=200)
    response.json.return_value = {"message": "OK"}
    post = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)

    KernelCIClient(cfg=cfg, instance="test").retry_job("n1")

    assert post.call_args[0][0] == "https://pipeline.example.org/api/jobretry"


def test_retry_job_failure_raises(monkeypatch):
    post = Mock(side_effect=requests.exceptions.ConnectionError("no route"))
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    with pytest.raises(KciDevError, match="retry failed"):
        _client().retry_job("n1")


def test_trigger_checkout_posts_payload(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"treeid": "t1"}
    post = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    result = _client().trigger_checkout(
        "https://git.example.org/linux.git", "master", "deadbeef", ["baseline-arm64"]
    )
    assert result == {"treeid": "t1"}
    body = json.loads(post.call_args.kwargs["data"])
    assert body == {
        "url": "https://git.example.org/linux.git",
        "branch": "master",
        "commit": "deadbeef",
        "jobfilter": ["baseline-arm64"],
    }


def test_trigger_checkout_includes_platform_filter(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"treeid": "t1"}
    post = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    _client().trigger_checkout(
        "https://git.example.org/linux.git",
        "master",
        "deadbeef",
        ["baseline-arm64"],
        platform_filter=["qemu-arm64"],
    )
    body = json.loads(post.call_args.kwargs["data"])
    assert body["platformfilter"] == ["qemu-arm64"]


def test_trigger_checkout_requires_token():
    cfg = {"test": {"pipeline": "https://pipeline.example.org/"}}
    with pytest.raises(KciDevError, match="token"):
        KernelCIClient(cfg=cfg, instance="test").trigger_checkout(
            "https://git.example.org/linux.git", "master", "deadbeef", ["baseline"]
        )


def test_trigger_patchset_posts_payload(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"message": "OK", "node": {"treeid": "t1"}}
    post = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    result = _client().trigger_patchset(
        "0" * 24, patches=["patch content"], job_filter=["baseline-arm64"]
    )
    assert result == {"message": "OK", "node": {"treeid": "t1"}}
    assert post.call_args[0][0] == "https://pipeline.example.org/api/patchset"
    body = json.loads(post.call_args.kwargs["data"])
    assert body == {
        "nodeid": "0" * 24,
        "patch": ["patch content"],
        "jobfilter": ["baseline-arm64"],
    }


def test_trigger_patchset_posts_patch_urls(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"message": "OK", "node": {}}
    post = Mock(return_value=response)
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    _client().trigger_patchset(
        "0" * 24,
        patchurls=["https://patchwork.kernel.org/series/1/mbox/"],
        platform_filter=["qemu-arm64"],
    )
    body = json.loads(post.call_args.kwargs["data"])
    assert body["patchurl"] == ["https://patchwork.kernel.org/series/1/mbox/"]
    assert body["platformfilter"] == ["qemu-arm64"]


def test_trigger_patchset_rejects_both_patch_forms():
    with pytest.raises(KciDevError, match="xactly one"):
        _client().trigger_patchset(
            "0" * 24,
            patches=["patch content"],
            patchurls=["https://patchwork.kernel.org/series/1/mbox/"],
        )


def test_trigger_patchset_requires_a_patch_form():
    with pytest.raises(KciDevError, match="xactly one"):
        _client().trigger_patchset("0" * 24)


def test_trigger_patchset_failure_raises(monkeypatch):
    post = Mock(side_effect=requests.exceptions.ConnectionError("no route"))
    monkeypatch.setattr(maestro_common.kcidev_session, "post", post)
    with pytest.raises(KciDevError, match="patchset failed"):
        _client().trigger_patchset("0" * 24, patches=["patch content"])


def test_get_tree_report_uses_integer_age_defaults(monkeypatch):
    client = _client()
    request = Mock(return_value={})
    monkeypatch.setattr(client, "_dashboard_request", request)

    client.get_tree_report("maestro", "main", "https://example.com/linux.git")

    assert request.call_args.args[-2:] == (24, 0)


@pytest.mark.parametrize(
    ("method_name", "result_id"),
    [("get_build_issues", "build-id"), ("get_boot_issues", "test-id")],
)
def test_get_issues_forwards_error_verbosity(monkeypatch, method_name, result_id):
    client = _client()
    request = Mock(return_value=[])
    monkeypatch.setattr(client, "_dashboard_request", request)

    getattr(client, method_name)(result_id, error_verbose=False)

    assert request.call_args.args[-2:] == (True, False)


def test_compare_results_continues_without_tree_history(monkeypatch):
    client = _client()
    monkeypatch.setattr(client, "get_builds", Mock(return_value={"builds": []}))
    monkeypatch.setattr(client, "get_boots", Mock(return_value={"boots": []}))
    monkeypatch.setattr(client, "get_tests", Mock(return_value={"tests": []}))
    monkeypatch.setattr(
        client,
        "get_tree_report",
        Mock(side_effect=KciDevError("tree report unavailable")),
    )

    report = client.compare_results(
        "base", "head", "https://example.com/linux.git", "main"
    )

    assert report["incomplete"] is True
    assert report["items"] == []


def test_compare_results_only_fetches_issues_when_requested(monkeypatch):
    client = _client()
    passing = {
        "id": "base-test",
        "status": "PASS",
        "path": "suite.case",
        "environment_misc": {"platform": "qemu"},
    }
    failing = {**passing, "id": "head-test", "status": "FAIL"}
    monkeypatch.setattr(client, "get_builds", Mock(return_value={"builds": []}))
    monkeypatch.setattr(client, "get_boots", Mock(return_value={"boots": []}))
    get_tests = Mock(side_effect=[{"tests": [passing]}, {"tests": [failing]}] * 2)
    monkeypatch.setattr(client, "get_tests", get_tests)
    monkeypatch.setattr(client, "get_tree_report", Mock(return_value={}))
    get_issues = Mock(return_value=[{"id": "issue-1"}])
    monkeypatch.setattr(client, "get_boot_issues", get_issues)

    report = client.compare_results(
        "base", "head", "https://example.com/linux.git", "main"
    )

    assert report["items"][0]["known_issues"] == []
    get_issues.assert_not_called()

    report = client.compare_results(
        "base",
        "head",
        "https://example.com/linux.git",
        "main",
        include_issues=True,
    )

    assert report["items"][0]["known_issues"] == ["issue-1"]
    get_issues.assert_called_once_with("head-test", error_verbose=False)


class _FakeStream:
    def __init__(self, chunks, status_code=200, headers=None, raise_after=None):
        self._chunks = list(chunks)
        self.status_code = status_code
        self.headers = headers or {}
        self.closed = False
        self._raise_after = raise_after

    def raise_for_status(self):
        pass

    def iter_content(self, size):
        for i, chunk in enumerate(self._chunks):
            if self._raise_after is not None and i == self._raise_after:
                raise requests.exceptions.ChunkedEncodingError("conn reset")
            yield chunk

    def close(self):
        self.closed = True


def _log_test(url="https://files.kernelci.org/x.log", output_files=None):
    return {"log_url": url, "output_files": output_files or []}


def _mock_stream(monkeypatch, chunks):
    monkeypatch.setattr(api, "_stream_public_get", lambda url: _FakeStream(chunks))


def _addrinfo(ip, port=443):
    return [(2, 1, 6, "", (ip, port))]


def test_get_log_decompresses_gzip(monkeypatch):
    import gzip

    monkeypatch.setattr(
        KernelCIClient, "get_test", lambda self, tid: _log_test("https://f/log.gz")
    )
    _mock_stream(monkeypatch, [gzip.compress(b"boot ok\nTEST FAIL: oops\n")])
    out = _client().get_log("maestro:abc")
    assert out["truncated"] is False
    assert "TEST FAIL: oops" in out["text"]
    assert out["total_bytes"] == len(b"boot ok\nTEST FAIL: oops\n")


def test_get_log_tail_truncates(monkeypatch):
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    _mock_stream(monkeypatch, [b"A" * 100 + b"TAILEND"])
    out = _client().get_log("t", max_bytes=7, tail=True)
    assert out["truncated"] is True
    assert out["text"] == "TAILEND"
    assert out["returned_bytes"] == 7


def test_get_log_head_truncates(monkeypatch):
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    _mock_stream(monkeypatch, [b"HEADSTART" + b"Z" * 100])
    out = _client().get_log("t", max_bytes=9, tail=False)
    assert out["text"] == "HEADSTART"
    assert out["truncated"] is True


def test_get_log_tail_spans_chunk_boundaries(monkeypatch):
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    _mock_stream(monkeypatch, [b"1234567890", b"abcde", b"XYZ"])
    out = _client().get_log("t", max_bytes=5, tail=True)
    assert out["text"] == "deXYZ"
    assert out["total_bytes"] == 18


def test_get_log_no_url_raises(monkeypatch):
    monkeypatch.setattr(
        KernelCIClient,
        "get_test",
        lambda self, tid: {"log_url": None, "output_files": []},
    )
    with pytest.raises(KciDevError, match="No log available"):
        _client().get_log("t")


def test_get_log_falls_back_to_output_files(monkeypatch):
    test = {
        "log_url": None,
        "output_files": [
            {"name": "build_kselftest_stderr_log", "url": "https://f/stderr.log.gz"},
            {"name": "test_log", "url": "https://f/test.log.gz"},
            {"name": "job_definition", "url": "https://f/def.json"},
        ],
    }
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: test)
    _mock_stream(monkeypatch, [b"from output_files"])
    out = _client().get_log("t")
    assert out["log_url"] == "https://f/test.log.gz"
    assert out["text"] == "from output_files"


@pytest.mark.parametrize("bad", [0, -1, -1000, 1.5, True, "100"])
def test_get_log_rejects_bad_max_bytes(bad):
    with pytest.raises(KciDevError, match="positive integer"):
        _client().get_log("t", max_bytes=bad)


def test_get_log_clamps_oversized_max_bytes(monkeypatch):
    monkeypatch.setattr(api, "MAX_LOG_BYTES", 10)
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    _mock_stream(monkeypatch, [b"B" * 50])
    out = _client().get_log("t", max_bytes=10_000, tail=False)
    assert out["returned_bytes"] == 10
    assert out["truncated"] is True


def test_get_log_scan_limit_bounds_download(monkeypatch):
    monkeypatch.setattr(api, "LOG_SCAN_LIMIT", 20)
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    _mock_stream(monkeypatch, [b"C" * 15, b"D" * 15, b"E" * 15])
    out = _client().get_log("t", max_bytes=100, tail=False)
    assert out["scan_limited"] is True
    assert out["truncated"] is True
    assert out["total_bytes"] == 15


def test_get_log_truncated_gzip_raises(monkeypatch):
    import gzip

    good = gzip.compress(b"hello world" * 50)
    monkeypatch.setattr(
        KernelCIClient, "get_test", lambda self, tid: _log_test("https://f/x.gz")
    )
    _mock_stream(monkeypatch, [good[:20]])
    with pytest.raises(KciDevError, match="incomplete or malformed"):
        _client().get_log("t")


def test_get_log_corrupt_gzip_raises(monkeypatch):
    import gzip

    good = gzip.compress(b"hello world" * 50)
    monkeypatch.setattr(
        KernelCIClient, "get_test", lambda self, tid: _log_test("https://f/x.gz")
    )
    _mock_stream(monkeypatch, [good[:10] + b"\x00" * 40])
    with pytest.raises(KciDevError, match="Log download failed"):
        _client().get_log("t")


def test_get_log_download_failure_raises(monkeypatch):
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())

    def boom(url):
        raise requests.exceptions.ConnectionError("no route")

    monkeypatch.setattr(api, "_stream_public_get", boom)
    with pytest.raises(KciDevError, match="Log download failed"):
        _client().get_log("t")


def test_require_public_url_rejects_non_http():
    with pytest.raises(KciDevError, match="non-http"):
        api._require_public_url("ftp://files.kernelci.org/x")
    with pytest.raises(KciDevError, match="non-http"):
        api._require_public_url("file:///etc/passwd")


@pytest.mark.parametrize(
    "ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1"]
)
def test_require_public_url_rejects_private(monkeypatch, ip):
    monkeypatch.setattr(api.socket, "getaddrinfo", lambda *a, **k: _addrinfo(ip))
    with pytest.raises(KciDevError, match="non-public"):
        api._require_public_url("https://evil.example/x")


def test_require_public_url_allows_public(monkeypatch):
    monkeypatch.setattr(
        api.socket, "getaddrinfo", lambda *a, **k: _addrinfo("93.184.216.34")
    )
    api._require_public_url("https://files.kernelci.org/x")


def test_require_public_url_unresolvable(monkeypatch):
    def boom(*a, **k):
        raise api.socket.gaierror("nope")

    monkeypatch.setattr(api.socket, "getaddrinfo", boom)
    with pytest.raises(KciDevError, match="resolve"):
        api._require_public_url("https://nope.invalid/x")


def test_stream_public_get_follows_validated_redirect(monkeypatch):
    monkeypatch.setattr(
        api.socket, "getaddrinfo", lambda *a, **k: _addrinfo("93.184.216.34")
    )
    r1 = Mock(status_code=302, headers={"Location": "https://cdn.example/final"})
    r1.close = Mock()
    r2 = _FakeStream([b"ok"])
    calls = []

    def fake_get(url, **k):
        calls.append(url)
        return r1 if len(calls) == 1 else r2

    monkeypatch.setattr(api.kcidev_session, "get", fake_get)
    assert api._stream_public_get("https://files.kernelci.org/x") is r2
    assert calls == ["https://files.kernelci.org/x", "https://cdn.example/final"]


def test_stream_public_get_rejects_redirect_to_private(monkeypatch):
    def ai(host, *a, **k):
        good = host == "files.kernelci.org"
        return _addrinfo("93.184.216.34" if good else "169.254.169.254")

    monkeypatch.setattr(api.socket, "getaddrinfo", ai)
    r1 = Mock(
        status_code=302, headers={"Location": "http://169.254.169.254/latest/meta"}
    )
    r1.close = Mock()
    monkeypatch.setattr(api.kcidev_session, "get", Mock(return_value=r1))
    with pytest.raises(KciDevError, match="non-public"):
        api._stream_public_get("https://files.kernelci.org/x")


def test_stream_public_get_too_many_redirects(monkeypatch):
    monkeypatch.setattr(
        api.socket, "getaddrinfo", lambda *a, **k: _addrinfo("93.184.216.34")
    )
    rr = Mock(status_code=302, headers={"Location": "https://a.example/loop"})
    rr.close = Mock()
    monkeypatch.setattr(api.kcidev_session, "get", Mock(return_value=rr))
    with pytest.raises(KciDevError, match="Too many redirects"):
        api._stream_public_get("https://a.example/loop")


def test_gunzip_iter_roundtrip():
    import gzip

    assert b"".join(api._gunzip_iter([gzip.compress(b"hello")])) == b"hello"


def test_gunzip_iter_truncated_raises():
    import gzip

    good = gzip.compress(b"data" * 100)
    with pytest.raises(KciDevError, match="incomplete or malformed"):
        list(api._gunzip_iter([good[:15]]))


def test_gunzip_iter_multi_member():
    import gzip

    stream = gzip.compress(b"first\n") + gzip.compress(b"SECOND\n")
    assert b"".join(api._gunzip_iter([stream])) == b"first\nSECOND\n"


def test_gunzip_iter_multi_member_split_and_boundary():
    import gzip

    stream = gzip.compress(b"AAA") + gzip.compress(b"BBB")
    split = [stream[:4], stream[4:]]
    assert b"".join(api._gunzip_iter(split)) == b"AAABBB"
    boundary = [gzip.compress(b"AAA"), gzip.compress(b"BBB")]
    assert b"".join(api._gunzip_iter(boundary)) == b"AAABBB"


def test_gunzip_iter_tolerates_trailing_garbage():
    import gzip

    assert b"".join(api._gunzip_iter([gzip.compress(b"log") + b"junk"])) == b"log"


def test_get_log_reads_multi_member_gzip(monkeypatch):
    import gzip

    stream = gzip.compress(b"member one\n") + gzip.compress(b"MEMBER TWO FAIL\n")
    monkeypatch.setattr(
        KernelCIClient, "get_test", lambda self, tid: _log_test("https://f/x.gz")
    )
    _mock_stream(monkeypatch, [stream])
    out = _client().get_log("t")
    assert "MEMBER TWO FAIL" in out["text"]
    assert out["truncated"] is False
    assert out["total_bytes"] == len(b"member one\nMEMBER TWO FAIL\n")


def test_get_log_closes_response_on_success(monkeypatch):
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    stream = _FakeStream([b"hello"])
    monkeypatch.setattr(api, "_stream_public_get", lambda url: stream)
    _client().get_log("t")
    assert stream.closed is True


def test_get_log_closes_response_on_gzip_error(monkeypatch):
    import gzip

    monkeypatch.setattr(
        KernelCIClient, "get_test", lambda self, tid: _log_test("https://f/x.gz")
    )
    stream = _FakeStream([gzip.compress(b"data" * 50)[:20]])
    monkeypatch.setattr(api, "_stream_public_get", lambda url: stream)
    with pytest.raises(KciDevError):
        _client().get_log("t")
    assert stream.closed is True


def test_get_log_closes_response_on_stream_error(monkeypatch):
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    stream = _FakeStream([b"a", b"b"], raise_after=1)
    monkeypatch.setattr(api, "_stream_public_get", lambda url: stream)
    with pytest.raises(KciDevError, match="Log download failed"):
        _client().get_log("t")
    assert stream.closed is True


def test_get_log_raw_scan_limit_bounds_compressed(monkeypatch):
    import gzip

    monkeypatch.setattr(api, "LOG_SCAN_LIMIT", 15)
    monkeypatch.setattr(
        KernelCIClient, "get_test", lambda self, tid: _log_test("https://f/x.gz")
    )
    gz = gzip.compress(b"hi there friend")
    _mock_stream(monkeypatch, [gz[:2], gz[2:10], gz[10:20], gz[20:]])
    out = _client().get_log("t")
    assert out["scan_limited"] is True
    assert out["truncated"] is True


def test_get_log_output_files_url_goes_through_guard(monkeypatch):
    test = {
        "log_url": None,
        "output_files": [{"name": "test_log", "url": "https://internal.evil/x.log"}],
    }
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: test)
    monkeypatch.setattr(
        api.socket, "getaddrinfo", lambda *a, **k: _addrinfo("169.254.169.254")
    )
    with pytest.raises(KciDevError, match="non-public"):
        _client().get_log("t")


def test_get_log_ignores_non_string_output_file_name(monkeypatch):
    test = {
        "log_url": None,
        "output_files": [
            {"name": 7, "url": "https://f/weird"},
            {"name": "test_log", "url": "https://f/ok.log"},
        ],
    }
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: test)
    _mock_stream(monkeypatch, [b"ok"])
    out = _client().get_log("t")
    assert out["log_url"] == "https://f/ok.log"


def test_require_public_url_rejects_bad_port():
    with pytest.raises(KciDevError, match="[Pp]ort"):
        api._require_public_url("https://files.kernelci.org:99999/x")


@pytest.mark.parametrize(
    "ip", ["::ffff:127.0.0.1", "::ffff:169.254.169.254", "0.0.0.0"]
)
def test_require_public_url_rejects_mapped_and_unspecified(monkeypatch, ip):
    monkeypatch.setattr(api.socket, "getaddrinfo", lambda *a, **k: _addrinfo(ip))
    with pytest.raises(KciDevError, match="non-public"):
        api._require_public_url("https://evil.example/x")


def test_require_public_url_idna_error_is_clean(monkeypatch):
    def boom(*a, **k):
        raise UnicodeError("label too long")

    monkeypatch.setattr(api.socket, "getaddrinfo", boom)
    with pytest.raises(KciDevError, match="resolve"):
        api._require_public_url("https://" + "a" * 70 + ".example/x")


def test_stream_public_get_redirect_without_location(monkeypatch):
    monkeypatch.setattr(
        api.socket, "getaddrinfo", lambda *a, **k: _addrinfo("93.184.216.34")
    )
    r = Mock(status_code=302, headers={})
    r.close = Mock()
    monkeypatch.setattr(api.kcidev_session, "get", Mock(return_value=r))
    with pytest.raises(KciDevError, match="without Location"):
        api._stream_public_get("https://files.kernelci.org/x")


def test_stream_public_get_rejects_redirect_to_file_scheme(monkeypatch):
    monkeypatch.setattr(
        api.socket, "getaddrinfo", lambda *a, **k: _addrinfo("93.184.216.34")
    )
    r = Mock(status_code=302, headers={"Location": "file:///etc/passwd"})
    r.close = Mock()
    monkeypatch.setattr(api.kcidev_session, "get", Mock(return_value=r))
    with pytest.raises(KciDevError, match="non-http"):
        api._stream_public_get("https://files.kernelci.org/x")


def test_get_log_stops_at_the_total_deadline(monkeypatch):
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    _mock_stream(monkeypatch, [b"X" * 1000 for _ in range(50)])
    ticks = iter([0.0] + [api.LOG_DEADLINE_SECONDS + 1] * 200)
    monkeypatch.setattr(api, "monotonic", lambda: next(ticks))

    out = _client().get_log("t", max_bytes=100000)

    assert out["deadline_exceeded"] is True
    assert out["truncated"] is True
    assert out["total_bytes"] < 50 * 1000


def test_get_log_normal_download_is_not_deadline_limited(monkeypatch):
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    _mock_stream(monkeypatch, [b"Y" * 100])

    out = _client().get_log("t", max_bytes=100000)

    assert out["deadline_exceeded"] is False
    assert out["truncated"] is False


def test_get_log_deadline_returns_partial_gzip(monkeypatch):
    import gzip

    raw = bytes(range(256)) * 40
    payload = gzip.compress(raw)
    chunks = [payload[i : i + 64] for i in range(0, len(payload), 64)]
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    _mock_stream(monkeypatch, chunks)
    ticks = iter([0.0] + [api.LOG_DEADLINE_SECONDS + 1] * 500)
    monkeypatch.setattr(api, "monotonic", lambda: next(ticks))

    out = _client().get_log("t", max_bytes=100000)

    assert out["deadline_exceeded"] is True
    assert out["truncated"] is True


def _job_node(callback_url="https://files.kernelci.org/cb.json.gz"):
    return {
        "id": "6a90b63cc5867fba9468b9b1",
        "kind": "job",
        "result": "incomplete",
        "data": {"error_code": "Infrastructure", "error_msg": "Unable to flash"},
        "artifacts": {"callback_data": callback_url} if callback_url else {},
    }


def _mock_node(monkeypatch, node):
    response = Mock(status_code=200)
    response.json.return_value = node
    monkeypatch.setattr(
        maestro_common.kcidev_session, "get", Mock(return_value=response)
    )


def _no_dashboard_test(monkeypatch):
    def boom(self, tid):
        raise api.KciDevError("Dashboard test request failed: Test not found")

    monkeypatch.setattr(KernelCIClient, "get_test", boom)


def test_get_log_falls_back_to_the_maestro_job_callback(monkeypatch):
    import gzip

    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    payload = gzip.compress(json.dumps({"log": "flash failed\nboom\n"}).encode())
    _mock_stream(monkeypatch, [payload])

    out = _client().get_log("6a90b63cc5867fba9468b9b1")

    assert "flash failed" in out["text"]
    assert out["source"] == "maestro-callback"


def test_get_log_fallback_accepts_the_prefixed_id(monkeypatch):
    import gzip

    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    _mock_stream(monkeypatch, [gzip.compress(json.dumps({"log": "hello"}).encode())])

    out = _client().get_log("maestro:6a90b63cc5867fba9468b9b1")

    assert out["text"] == "hello"


def test_get_log_fallback_without_a_callback_is_a_clean_error(monkeypatch):
    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node(callback_url=None))

    with pytest.raises(api.KciDevError, match="No log available"):
        _client().get_log("6a90b63cc5867fba9468b9b1")


def test_get_log_dashboard_path_is_still_preferred(monkeypatch):
    monkeypatch.setattr(KernelCIClient, "get_test", lambda self, tid: _log_test())
    _mock_stream(monkeypatch, [b"from the dashboard"])

    out = _client().get_log("maestro:abc")

    assert out["source"] == "dashboard"
    assert out["text"] == "from the dashboard"


def test_get_log_fallback_caps_an_oversized_callback(monkeypatch):
    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    huge = b"x" * (api.MAX_CALLBACK_BYTES + 1)
    _mock_stream(monkeypatch, [huge])

    with pytest.raises(api.KciDevError, match="exceeds"):
        _client().get_log("6a90b63cc5867fba9468b9b1")


def test_get_log_fallback_bounds_the_extracted_log(monkeypatch):
    import gzip

    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    body = json.dumps({"log": "A" * 100 + "TAILEND"}).encode()
    _mock_stream(monkeypatch, [gzip.compress(body)])

    out = _client().get_log("6a90b63cc5867fba9468b9b1", max_bytes=7, tail=True)

    assert out["text"] == "TAILEND"
    assert out["truncated"] is True
    assert out["total_bytes"] == 107


def test_get_log_fallback_refuses_a_decompression_bomb(monkeypatch):
    import gzip

    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    bomb = gzip.compress(b"\0" * (api.MAX_CALLBACK_BYTES * 8))
    assert len(bomb) < api.MAX_CALLBACK_BYTES
    _mock_stream(monkeypatch, [bomb])

    with pytest.raises(api.KciDevError, match="exceeds"):
        _client().get_log("6a90b63cc5867fba9468b9b1")


def test_get_log_does_not_fall_back_on_a_non_not_found_error(monkeypatch):
    def boom(self, tid):
        raise api.KciDevError("Dashboard test request failed: upstream exploded")

    monkeypatch.setattr(KernelCIClient, "get_test", boom)
    node = Mock(side_effect=AssertionError("fallback must not run"))
    monkeypatch.setattr(KernelCIClient, "get_node", node)

    with pytest.raises(api.KciDevError, match="upstream exploded"):
        _client().get_log("maestro:abc")


def test_get_log_reports_both_errors_when_the_fallback_also_fails(monkeypatch):
    _no_dashboard_test(monkeypatch)

    def no_node(self, nid):
        raise api.KciDevError("No Maestro api URL configured")

    monkeypatch.setattr(KernelCIClient, "get_node", no_node)

    with pytest.raises(api.KciDevError) as excinfo:
        _client().get_log("maestro:abc")

    assert "Test not found" in str(excinfo.value)
    assert "No Maestro api URL configured" in str(excinfo.value)


def test_get_log_fallback_reads_an_uncompressed_callback(monkeypatch):
    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    _mock_stream(monkeypatch, [json.dumps({"log": "plain json"}).encode()])

    assert _client().get_log("6a90b63c")["text"] == "plain json"


def test_get_log_fallback_without_a_log_field_is_a_clean_error(monkeypatch):
    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    _mock_stream(monkeypatch, [json.dumps({"results": {}}).encode()])

    with pytest.raises(api.KciDevError, match="carries no log"):
        _client().get_log("6a90b63c")


def test_get_log_fallback_head_bounding(monkeypatch):
    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    _mock_stream(monkeypatch, [json.dumps({"log": "HEADSTART" + "z" * 90}).encode()])

    out = _client().get_log("6a90b63c", max_bytes=9, tail=False)
    assert out["text"] == "HEADSTART"


def test_get_log_fallback_stops_at_the_deadline(monkeypatch):
    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    _mock_stream(monkeypatch, [b"x" * 1000 for _ in range(50)])
    ticks = iter([0.0] + [api.LOG_DEADLINE_SECONDS + 1] * 200)
    monkeypatch.setattr(api, "monotonic", lambda: next(ticks))

    with pytest.raises(api.KciDevError, match="deadline|too long|timed out"):
        _client().get_log("6a90b63c")


def test_get_log_does_not_fall_back_for_a_non_maestro_origin(monkeypatch):
    _no_dashboard_test(monkeypatch)
    monkeypatch.setattr(
        KernelCIClient,
        "get_node",
        Mock(side_effect=AssertionError("must not query Maestro")),
    )

    with pytest.raises(api.KciDevError, match="Test not found"):
        _client().get_log("redhat:6a90b63cc5867fba9468b9b1")


def test_get_log_fallback_malformed_gzip_is_a_clean_error(monkeypatch):
    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    _mock_stream(monkeypatch, [b"\x1f\x8b\x08\x00" + b"\xff" * 200])

    with pytest.raises(api.KciDevError):
        _client().get_log("6a90b63cc5867fba9468b9b1")


def test_get_log_prefers_the_lava_log_artifact(monkeypatch):
    import gzip

    node = _job_node()
    node["artifacts"]["lava_log"] = "https://files.kernelci.org/log.txt.gz"
    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, node)
    _mock_stream(monkeypatch, [gzip.compress(b"from the lava_log artifact\n")])

    out = _client().get_log("6a90b63cc5867fba9468b9b1")

    assert "from the lava_log artifact" in out["text"]
    assert out["source"] == "maestro-log"
    assert out["log_url"] == "https://files.kernelci.org/log.txt.gz"


def test_get_log_uses_the_callback_when_there_is_no_lava_log(monkeypatch):
    import gzip

    _no_dashboard_test(monkeypatch)
    _mock_node(monkeypatch, _job_node())
    _mock_stream(monkeypatch, [gzip.compress(json.dumps({"log": "from cb"}).encode())])

    out = _client().get_log("6a90b63cc5867fba9468b9b1")

    assert out["text"] == "from cb"
    assert out["source"] == "maestro-callback"
