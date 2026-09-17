#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Public Python API for using kci-dev as a library.

The CLI remains the primary user interface, but applications can import this
module to build and submit KCIDB payloads or query KernelCI dashboard data
without invoking Click commands or shelling out to ``kci-dev``.
"""

import ipaddress
import json
import socket
import zlib
from datetime import datetime, timezone
from time import monotonic
from urllib.parse import urljoin, urlparse

import click
import requests
from click.testing import CliRunner

from kcidev.libs.common import kcidev_session
from kcidev.libs.dashboard import (
    dashboard_api_url,
    dashboard_fetch_boot_issues,
    dashboard_fetch_boots,
    dashboard_fetch_build,
    dashboard_fetch_build_issues,
    dashboard_fetch_builds,
    dashboard_fetch_commits_history,
    dashboard_fetch_hardware_boots,
    dashboard_fetch_hardware_builds,
    dashboard_fetch_hardware_list,
    dashboard_fetch_hardware_summary,
    dashboard_fetch_hardware_tests,
    dashboard_fetch_issue,
    dashboard_fetch_issue_builds,
    dashboard_fetch_issue_list,
    dashboard_fetch_issue_tests,
    dashboard_fetch_issues_extra,
    dashboard_fetch_summary,
    dashboard_fetch_test,
    dashboard_fetch_tests,
    dashboard_fetch_tree_list,
    dashboard_fetch_tree_report,
    resolve_dashboard_api,
)
from kcidev.libs.git_repo import get_folder_repository
from kcidev.libs.kcidb import (
    build_build_payload,
    build_checkout_payload,
    build_submission_payload,
    generate_build_id,
    generate_checkout_id,
    resolve_kcidb_config,
    submit_to_kcidb,
)
from kcidev.libs.maestro_common import (
    maestro_get_node,
    maestro_get_nodes,
    send_checkout_full,
    send_jobretry,
    send_patchset,
)
from kcidev.libs.regression import RegressionReport
from kcidev.main import get_cli


def run_command(args, *, catch_exceptions=True, env=None, input=None):
    """Run a kci-dev CLI command from Python and return Click's result object.

    Args:
        args: Command-line arguments, either as a sequence such as
            ``["results", "summary", "--help"]`` or as a shell-like string. Do
            not include the leading ``kci-dev`` executable name.
        catch_exceptions: Passed to :class:`click.testing.CliRunner`; keep the
            default to receive failures in the returned result instead of
            raising them.
        env: Optional environment variables for the command invocation.
        input: Optional standard input text for interactive Click commands.

    Returns:
        A :class:`click.testing.Result` containing ``exit_code``, ``output``,
        ``stdout``, ``stderr``, and any captured exception.
    """
    runner = CliRunner()
    return runner.invoke(
        get_cli(),
        args,
        input=input,
        env=env,
        catch_exceptions=catch_exceptions,
    )


class KciDevError(RuntimeError):
    """Raised by the library API when an operation cannot be completed."""


def _as_library_error(action, func, *args, **kwargs):
    """Run an existing CLI-oriented helper and expose failures as exceptions."""
    try:
        return func(*args, **kwargs)
    except click.ClickException as exc:
        raise KciDevError(f"{action}: {exc.message}") from exc
    except click.Abort as exc:
        raise KciDevError(action) from exc
    except SystemExit as exc:
        raise KciDevError(action) from exc


NOTHING_RELATED_MARKERS = (
    "No issues found",
    "No issues were found",
    "No tests found",
    "No builds found",
)

MAX_LOG_BYTES = 1 << 20
MAX_CALLBACK_BYTES = 8 << 20
LOG_SCAN_LIMIT = 64 << 20
LOG_DEADLINE_SECONDS = 60
_LOG_CHUNK = 1 << 16
_MAX_LOG_REDIRECTS = 5


def _require_public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise KciDevError(f"Refusing to fetch non-http(s) log URL: {url}")
    host = parsed.hostname
    if not host:
        raise KciDevError(f"Log URL has no host: {url}")
    default_port = 443 if parsed.scheme == "https" else 80
    try:
        port = parsed.port or default_port
    except ValueError as exc:
        raise KciDevError(f"Invalid port in log URL {url}: {exc}") from exc
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (OSError, UnicodeError) as exc:
        raise KciDevError(f"Could not resolve log host {host}: {exc}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise KciDevError(
                f"Refusing to fetch log from non-public address {ip} ({host})"
            )


def _stream_public_get(url):
    for _ in range(_MAX_LOG_REDIRECTS + 1):
        _require_public_url(url)
        response = kcidev_session.get(
            url, stream=True, timeout=30, allow_redirects=False
        )
        if 300 <= response.status_code < 400:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise KciDevError(f"Redirect without Location header: {url}")
            url = urljoin(url, location)
            continue
        return response
    raise KciDevError("Too many redirects while fetching log")


def _gunzip_iter(raw_iter):
    decomp = zlib.decompressobj(zlib.MAX_WBITS | 16)
    carry = b""
    trailing_garbage = False
    for chunk in raw_iter:
        to_feed = carry + chunk
        carry = b""
        while to_feed:
            if decomp.eof:
                if to_feed[:2] == b"\x1f\x8b":
                    decomp = zlib.decompressobj(zlib.MAX_WBITS | 16)
                elif len(to_feed) < 2:
                    carry = to_feed
                    break
                else:
                    trailing_garbage = True
                    break
            yield decomp.decompress(to_feed, _LOG_CHUNK)
            to_feed = decomp.unused_data if decomp.eof else decomp.unconsumed_tail
        if trailing_garbage:
            break
    if trailing_garbage:
        return
    rest = decomp.flush()
    if rest:
        yield rest
    if not decomp.eof:
        raise KciDevError("Log gzip stream is incomplete or malformed")


def _maestro_node_id(node_id):
    """Return the Maestro node id, or None when the id is not Maestro's.

    The dashboard prefixes ids with their origin while Maestro takes the
    bare hex, so only a bare id or an explicitly maestro-prefixed one may
    be looked up. Stripping any prefix would let a missing
    other-origin:<id> resolve to an unrelated Maestro <id>.
    """
    if ":" not in node_id:
        return node_id
    origin, _, rest = node_id.partition(":")
    return rest if origin == "maestro" else None


def _bounded_text(raw, max_bytes, tail):
    """Apply the head/tail bound to text already held in memory."""
    if len(raw) <= max_bytes:
        return raw, len(raw)
    return (raw[-max_bytes:] if tail else raw[:max_bytes]), len(raw)


def _pick_log_url(test):
    if not isinstance(test, dict):
        return None
    if test.get("log_url"):
        return test["log_url"]
    logs = [
        f
        for f in (test.get("output_files") or [])
        if isinstance(f, dict)
        and f.get("url")
        and isinstance(f.get("name"), str)
        and "log" in f["name"].lower()
    ]
    logs.sort(key=lambda f: ("stderr" in f["name"].lower(), f["name"].lower()))
    return logs[0]["url"] if logs else None


class KernelCIClient:
    """Client for interacting with KernelCI services from Python code.

    Args:
        cfg: Optional kci-dev configuration dictionary, for example the result
            of :func:`kcidev.libs.common.load_toml`.
        instance: Optional instance name in ``cfg``.
        kcidb_rest_url: Optional KCIDB submit endpoint override.
        kcidb_token: Optional KCIDB bearer token override.
        dashboard_api: Optional dashboard API base URL override; when unset,
            ``dashboard_api`` from the instance section or the top level of
            ``cfg`` is used, falling back to the production dashboard.
    """

    def __init__(
        self,
        cfg=None,
        instance=None,
        kcidb_rest_url=None,
        kcidb_token=None,
        dashboard_api=None,
    ):
        self.cfg = cfg
        self.instance = instance or (cfg or {}).get("default_instance")
        self.kcidb_rest_url = kcidb_rest_url
        self.kcidb_token = kcidb_token
        self.dashboard_api = resolve_dashboard_api(
            cfg, self.instance, override=dashboard_api
        )

    def _dashboard_request(self, action, func, *args):
        """Run one dashboard request with this client's endpoint."""
        with dashboard_api_url(self.dashboard_api):
            return _as_library_error(action, func, *args)

    def run_command(self, args, *, catch_exceptions=True, env=None, input=None):
        """Run a kci-dev subcommand using the same command tree as the CLI."""
        return run_command(
            args,
            catch_exceptions=catch_exceptions,
            env=env,
            input=input,
        )

    def resolve_kcidb_config(self):
        """Return the configured ``(rest_url, token)`` for KCIDB submission."""
        return _as_library_error(
            "Unable to resolve KCIDB credentials",
            resolve_kcidb_config,
            self.cfg,
            self.instance,
            self.kcidb_rest_url,
            self.kcidb_token,
        )

    def build_kcidb_build_submission(
        self,
        *,
        origin,
        giturl=None,
        branch=None,
        commit=None,
        tree_name=None,
        patchset_hash=None,
        arch=None,
        config_name=None,
        compiler=None,
        status=None,
        start_time=None,
        duration=None,
        log_url=None,
        config_url=None,
        comment=None,
        command=None,
        git_folder=None,
    ):
        """Create a KCIDB checkout/build submission payload.

        This mirrors ``kci-dev submit build`` payload creation and can either use
        explicit ``giturl``/``branch``/``commit`` values or auto-detect them from
        ``git_folder``.
        """
        if git_folder:
            detected_url, detected_branch, detected_commit = _as_library_error(
                "Unable to inspect git folder",
                get_folder_repository,
                git_folder,
                branch,
            )
            giturl = giturl or detected_url
            branch = branch or detected_branch
            commit = commit or detected_commit

        if not origin:
            raise KciDevError("origin is required")
        if not giturl or not commit:
            raise KciDevError("giturl and commit are required")

        branch = branch or ""
        patchset_hash = patchset_hash or ""
        start_time = start_time or datetime.now(timezone.utc).isoformat()

        checkout_id = generate_checkout_id(
            origin, giturl, branch, commit, patchset_hash
        )
        build_id = generate_build_id(
            origin,
            checkout_id,
            arch or "",
            config_name or "",
            compiler or "",
            start_time,
        )
        checkout = build_checkout_payload(
            origin,
            checkout_id,
            tree_name=tree_name,
            git_repository_url=giturl,
            git_repository_branch=branch if branch else None,
            git_commit_hash=commit,
            patchset_hash=patchset_hash if patchset_hash else None,
        )
        build = build_build_payload(
            origin,
            build_id,
            checkout_id,
            start_time=start_time,
            duration=duration,
            architecture=arch,
            compiler=compiler,
            config_name=config_name,
            config_url=config_url,
            log_url=log_url,
            comment=comment,
            command=command,
            status=status,
        )
        return build_submission_payload([checkout], [build])

    def submit_kcidb(self, payload, timeout=60):
        """Submit a KCIDB payload and return the API response."""
        rest_url, token = self.resolve_kcidb_config()
        return _as_library_error(
            "KCIDB submission failed",
            submit_to_kcidb,
            rest_url,
            token,
            payload,
            timeout,
        )

    def submit_build(self, **kwargs):
        """Build and submit a KCIDB build payload in one call."""
        return self.submit_kcidb(self.build_kcidb_build_submission(**kwargs))

    def get_summary(self, origin, giturl, branch, commit, arch=None):
        return self._dashboard_request(
            "Dashboard summary request failed",
            dashboard_fetch_summary,
            origin,
            giturl,
            branch,
            commit,
            arch,
            True,
        )

    def get_builds(
        self,
        origin,
        giturl,
        branch,
        commit,
        arch=None,
        tree=None,
        start_date=None,
        end_date=None,
    ):
        return self._dashboard_request(
            "Dashboard builds request failed",
            dashboard_fetch_builds,
            origin,
            giturl,
            branch,
            commit,
            arch,
            tree,
            start_date,
            end_date,
            True,
        )

    def get_boots(
        self,
        origin,
        giturl,
        branch,
        commit,
        arch=None,
        tree=None,
        start_date=None,
        end_date=None,
        boot_origin=None,
    ):
        return self._dashboard_request(
            "Dashboard boots request failed",
            dashboard_fetch_boots,
            origin,
            giturl,
            branch,
            commit,
            arch,
            tree,
            start_date,
            end_date,
            True,
            boot_origin,
        )

    def get_tests(
        self,
        origin,
        giturl,
        branch,
        commit,
        arch=None,
        tree=None,
        start_date=None,
        end_date=None,
    ):
        return self._dashboard_request(
            "Dashboard tests request failed",
            dashboard_fetch_tests,
            origin,
            giturl,
            branch,
            commit,
            arch,
            tree,
            start_date,
            end_date,
            True,
        )

    def get_commits_history(self, origin, giturl, branch, commit):
        return self._dashboard_request(
            "Dashboard history request failed",
            dashboard_fetch_commits_history,
            origin,
            giturl,
            branch,
            commit,
            True,
        )

    def get_build(self, build_id):
        return self._dashboard_request(
            "Dashboard build request failed", dashboard_fetch_build, build_id, True
        )

    def get_test(self, test_id):
        return self._dashboard_request(
            "Dashboard test request failed", dashboard_fetch_test, test_id, True
        )

    def get_log(self, test_id, max_bytes=16384, tail=True):
        """Fetch the raw log for a test, decompressing gzip, size-bounded.

        Resolves the test's log URL (``log_url`` or, when that is empty, a
        log entry from ``output_files``), downloads it with a bounded head or
        tail buffer, decompressing gzip (including multi-member streams)
        incrementally, and returns the text with the decompressed
        ``total_bytes`` and a ``truncated`` flag. At most ``max_bytes`` bytes
        are returned (capped at ``MAX_LOG_BYTES``), taken from the end when
        ``tail`` is true (where failures usually are) or the start otherwise.
        Reading stops once ``LOG_SCAN_LIMIT`` compressed or decompressed
        bytes are seen, to bound memory and download against oversized or
        malicious logs; ``scan_limited`` is then set and ``total_bytes`` is a
        floor rather than the exact size. Reading also stops after
        ``LOG_DEADLINE_SECONDS``, since the request timeout is per read
        rather than total and a slow server would otherwise hold the
        caller indefinitely; ``deadline_exceeded`` is then set and
        ``total_bytes`` is likewise a floor. The log URL is validated (scheme
        and resolved address) before fetching, though a DNS rebind between
        that check and the request remains a residual gap.

        A job that failed before producing results has no dashboard test,
        so its log is read from Maestro instead: the ``lava_log``
        artifact where present, which is a plain log this same path
        streams, otherwise the log field of the LAVA callback. The
        returned ``source`` says which was used, and for the callback
        ``log_url`` is that document rather than a log file. Only bare
        or maestro-prefixed ids are looked up, so a missing test from
        another origin keeps its dashboard error.
        """
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
            raise KciDevError("max_bytes must be a positive integer")
        if max_bytes <= 0:
            raise KciDevError("max_bytes must be a positive integer")
        max_bytes = min(max_bytes, MAX_LOG_BYTES)

        try:
            test = self.get_test(test_id)
        except KciDevError as exc:
            if "not found" not in str(exc).lower():
                raise
            if _maestro_node_id(test_id) is None:
                raise
            log_url, log_source, callback = self._job_log_source(test_id, exc)
            if callback is not None:
                return self._callback_log(test_id, callback, max_bytes, tail)
        else:
            log_url = _pick_log_url(test)
            log_source = "dashboard"
            if not log_url:
                raise KciDevError(f"No log available for test {test_id}")

        buf = bytearray()
        total = 0
        raw_total = 0
        scan_limited = False
        deadline_exceeded = False
        deadline = monotonic() + LOG_DEADLINE_SECONDS
        response = None
        try:
            response = _stream_public_get(log_url)
            response.raise_for_status()
            chunks = response.iter_content(_LOG_CHUNK)

            prefix = b""
            for chunk in chunks:
                if not chunk:
                    continue
                prefix += chunk
                if len(prefix) >= 2:
                    break

            def raw_iter():
                nonlocal raw_total, scan_limited, deadline_exceeded
                if prefix:
                    raw_total += len(prefix)
                    yield prefix
                for chunk in chunks:
                    if not chunk:
                        continue
                    if monotonic() > deadline:
                        deadline_exceeded = True
                        return
                    raw_total += len(chunk)
                    if raw_total > LOG_SCAN_LIMIT:
                        scan_limited = True
                        return
                    yield chunk

            source = (
                _gunzip_iter(raw_iter()) if prefix[:2] == b"\x1f\x8b" else raw_iter()
            )
            try:
                for out in source:
                    if not out:
                        continue
                    total += len(out)
                    if tail:
                        buf += out
                        if len(buf) > max_bytes:
                            del buf[:-max_bytes]
                    elif len(buf) < max_bytes:
                        buf += out[: max_bytes - len(buf)]
                    if total >= LOG_SCAN_LIMIT:
                        scan_limited = True
                        break
            except KciDevError:
                if not (scan_limited or deadline_exceeded):
                    raise
        except KciDevError:
            raise
        except (requests.exceptions.RequestException, zlib.error, OSError) as exc:
            raise KciDevError(f"Log download failed for test {test_id}: {exc}") from exc
        finally:
            if response is not None:
                response.close()

        returned = bytes(buf)
        return {
            "test_id": test_id,
            "log_url": log_url,
            "total_bytes": total,
            "returned_bytes": len(returned),
            "truncated": scan_limited or deadline_exceeded or total > len(returned),
            "scan_limited": scan_limited,
            "deadline_exceeded": deadline_exceeded,
            "tail": tail,
            "source": log_source,
            "text": returned.decode("utf-8", errors="replace"),
        }

    def _job_log_source(self, test_id, dashboard_error):
        """Resolve a Maestro job's log, preferring a plain log artifact.

        lava_log is a gzipped log file the normal streaming path can read.
        The LAVA callback carries the log as a JSON field instead, which
        has to be read whole, and the pipeline treats that field as
        temporary, so it is only the fallback.
        """
        try:
            node = self.get_node(_maestro_node_id(test_id))
        except KciDevError as exc:
            raise KciDevError(
                f"{dashboard_error}; the Maestro fallback also failed: {exc}"
            ) from exc
        artifacts = node.get("artifacts") or {}
        if artifacts.get("lava_log"):
            return artifacts["lava_log"], "maestro-log", None
        if artifacts.get("callback_data"):
            return None, "maestro-callback", artifacts["callback_data"]
        raise KciDevError(f"No log available for {test_id}")

    def _callback_log(self, test_id, callback_url, max_bytes, tail):
        """Fall back to the Maestro job callback when the dashboard has none.

        A job that fails before producing results never reaches the
        dashboard, so its log is only in the LAVA callback Maestro keeps.
        That callback is a JSON document rather than a log file, so it has
        to be read whole before the log field can be taken out; it is
        capped at ``MAX_CALLBACK_BYTES`` rather than streamed.
        """
        response = None
        try:
            response = _stream_public_get(callback_url)
            response.raise_for_status()
            body = bytearray()
            deadline = monotonic() + LOG_DEADLINE_SECONDS
            for chunk in response.iter_content(_LOG_CHUNK):
                if not chunk:
                    continue
                if monotonic() > deadline:
                    raise KciDevError(
                        f"Job callback download for {test_id} passed the "
                        f"{LOG_DEADLINE_SECONDS}s deadline"
                    )
                body += chunk
                if len(body) > MAX_CALLBACK_BYTES:
                    raise KciDevError(
                        f"Job callback for {test_id} exceeds "
                        f"{MAX_CALLBACK_BYTES} bytes"
                    )
            raw = bytes(body)
            if raw[:2] == b"\x1f\x8b":
                expanded = bytearray()
                for piece in _gunzip_iter(iter([raw])):
                    expanded += piece
                    if len(expanded) > MAX_CALLBACK_BYTES:
                        raise KciDevError(
                            f"Job callback for {test_id} exceeds "
                            f"{MAX_CALLBACK_BYTES} bytes decompressed"
                        )
                raw = bytes(expanded)
            callback = json.loads(raw.decode("utf-8", errors="replace"))
        except KciDevError:
            raise
        except (
            requests.exceptions.RequestException,
            zlib.error,
            OSError,
            ValueError,
        ) as exc:
            raise KciDevError(
                f"Job callback download failed for {test_id}: {exc}"
            ) from exc
        finally:
            if response is not None:
                response.close()

        log = callback.get("log")
        if not isinstance(log, str):
            raise KciDevError(f"Job callback for {test_id} carries no log")

        encoded = log.encode("utf-8", errors="replace")
        returned, total = _bounded_text(encoded, max_bytes, tail)
        return {
            "test_id": test_id,
            "log_url": callback_url,
            "total_bytes": total,
            "returned_bytes": len(returned),
            "truncated": total > len(returned),
            "scan_limited": False,
            "deadline_exceeded": False,
            "tail": tail,
            "source": "maestro-callback",
            "text": returned.decode("utf-8", errors="replace"),
        }

    def get_tree_list(self, origin, days=7):
        return self._dashboard_request(
            "Dashboard tree list request failed",
            dashboard_fetch_tree_list,
            origin,
            True,
            days,
        )

    def get_hardware_list(self, origin):
        return self._dashboard_request(
            "Dashboard hardware list request failed",
            dashboard_fetch_hardware_list,
            origin,
            True,
        )

    def get_hardware_summary(self, name, origin):
        return self._dashboard_request(
            "Dashboard hardware summary request failed",
            dashboard_fetch_hardware_summary,
            name,
            origin,
            True,
        )

    def get_hardware_boots(self, name, origin):
        return self._dashboard_request(
            "Dashboard hardware boots request failed",
            dashboard_fetch_hardware_boots,
            name,
            origin,
            True,
        )

    def get_hardware_builds(self, name, origin):
        return self._dashboard_request(
            "Dashboard hardware builds request failed",
            dashboard_fetch_hardware_builds,
            name,
            origin,
            True,
        )

    def get_hardware_tests(self, name, origin):
        return self._dashboard_request(
            "Dashboard hardware tests request failed",
            dashboard_fetch_hardware_tests,
            name,
            origin,
            True,
        )

    def _related_or_empty(self, action, func, *args):
        """Fetch one artifact's related list, treating "none" as empty.

        The dashboard reports an artifact with nothing related to it as
        an error rather than an empty list. A caller asking what an
        issue affects, or whether a failure is already known, should
        read that as a clean answer rather than a failed call.
        """
        try:
            return self._dashboard_request(action, func, *args)
        except KciDevError as exc:
            if any(marker in str(exc) for marker in NOTHING_RELATED_MARKERS):
                return []
            raise

    def get_build_issues(self, build_id, error_verbose=True):
        return self._related_or_empty(
            "Dashboard build issues request failed",
            dashboard_fetch_build_issues,
            build_id,
            True,
            error_verbose,
        )

    def get_boot_issues(self, test_id, error_verbose=True):
        return self._related_or_empty(
            "Dashboard boot issues request failed",
            dashboard_fetch_boot_issues,
            test_id,
            True,
            error_verbose,
        )

    def get_issue_list(self, origin=None, days=7):
        return self._dashboard_request(
            "Dashboard issue list request failed",
            dashboard_fetch_issue_list,
            origin,
            days,
            True,
        )

    def get_issue(self, issue_id):
        return self._dashboard_request(
            "Dashboard issue request failed", dashboard_fetch_issue, issue_id, True
        )

    def get_issue_builds(self, issue_id, origin=None):
        return self._related_or_empty(
            "Dashboard issue builds request failed",
            dashboard_fetch_issue_builds,
            origin,
            issue_id,
            True,
            False,
        )

    def get_issue_tests(self, issue_id, origin=None):
        return self._related_or_empty(
            "Dashboard issue tests request failed",
            dashboard_fetch_issue_tests,
            origin,
            issue_id,
            True,
            False,
        )

    def get_issues_extra(self, issues):
        return self._dashboard_request(
            "Dashboard issues extra request failed",
            dashboard_fetch_issues_extra,
            issues,
            True,
        )

    def get_tree_report(
        self,
        origin,
        git_branch,
        git_url,
        test_path=None,
        history_size=10,
        max_age_in_hours=24,
        min_age_in_hours=0,
    ):
        return self._dashboard_request(
            "Dashboard tree report request failed",
            dashboard_fetch_tree_report,
            origin,
            git_branch,
            git_url,
            True,
            test_path or [],
            history_size,
            max_age_in_hours,
            min_age_in_hours,
        )

    def compare_results(
        self, base, head, giturl, branch, origin="maestro", include_issues=False
    ):
        """Compare two dashboard checkouts and return a CI-grade report dict.

        Issue lookup is disabled by default because it requires one additional
        Dashboard request for every regression and persistent failure.
        """

        def checkout(commit):
            return {
                "builds": self.get_builds(origin, giturl, branch, commit).get(
                    "builds", []
                ),
                "boots": self.get_boots(origin, giturl, branch, commit).get(
                    "boots", []
                ),
                "tests": self.get_tests(origin, giturl, branch, commit).get(
                    "tests", []
                ),
            }

        base_results, head_results = checkout(base), checkout(head)
        # tree-report supplies history-aware unstable/regression decisions.  If
        # HEAD is not the newest checkout the raw transition remains useful.
        history_incomplete = False
        try:
            history = self.get_tree_report(origin, branch, giturl)
        except KciDevError:
            # History improves classification, but is not required to compare
            # the two explicitly requested checkouts.
            history = None
            history_incomplete = True
        report = RegressionReport.compare(
            base, head, base_results, head_results, history
        )
        report.incomplete = history_incomplete
        if include_issues:
            for item in report.items:
                if item["category"] not in ("regression", "persistent_fail"):
                    continue
                result_id = item["head_id"]
                if not result_id:
                    continue
                try:
                    issues = (
                        self.get_build_issues(result_id, error_verbose=False)
                        if item["identity"]["kind"] == "build"
                        else self.get_boot_issues(result_id, error_verbose=False)
                    )
                except KciDevError as exc:
                    if "no issues" in str(exc).lower():
                        issues = []
                    else:
                        report.incomplete = True
                        continue
                item["known_issues"] = [
                    issue.get("id", issue) if isinstance(issue, dict) else issue
                    for issue in issues
                ]
        return report.to_dict()

    def _instance_setting(self, key, *, human_readable_key=None):
        value = ((self.cfg or {}).get(self.instance) or {}).get(key)
        if not value:
            raise KciDevError(
                f"No Maestro {human_readable_key or key} configured;"
                " pass it explicitly or set it in the instance config"
            )
        return value

    def get_node(self, node_id, api_url=None):
        """Fetch a single Maestro node by id."""
        url = api_url or self._instance_setting("api", human_readable_key="api URL")
        return _as_library_error(
            "Maestro node request failed", maestro_get_node, url, node_id
        )

    def get_nodes(self, limit=50, offset=0, filters=None, api_url=None):
        """List Maestro nodes with 'field=value' filters and pagination."""
        url = api_url or self._instance_setting("api", human_readable_key="api URL")
        return _as_library_error(
            "Maestro nodes request failed",
            maestro_get_nodes,
            url,
            limit,
            offset,
            filters or [],
            True,
        )

    def retry_job(self, node_id, pipeline_url=None, token=None):
        """Retry a failed or incomplete job by Maestro node id."""
        url = pipeline_url or self._instance_setting(
            "pipeline", human_readable_key="pipeline URL"
        )
        token = token or self._instance_setting("token")
        result = _as_library_error(
            "Maestro job retry failed", send_jobretry, url, node_id, token
        )
        if result is None:
            raise KciDevError(f"Maestro job retry failed for node {node_id}")
        return result

    def trigger_checkout(
        self,
        giturl,
        branch,
        commit,
        job_filter,
        platform_filter=None,
        pipeline_url=None,
        token=None,
    ):
        """Trigger a pipeline checkout of a tree/branch/commit with a job filter."""
        url = pipeline_url or self._instance_setting(
            "pipeline", human_readable_key="pipeline URL"
        )
        token = token or self._instance_setting("token")
        kwargs = {
            "giturl": giturl,
            "branch": branch,
            "commit": commit,
            "job_filter": job_filter,
        }
        if platform_filter:
            kwargs["platform_filter"] = platform_filter
        result = _as_library_error(
            "Maestro checkout failed", send_checkout_full, url, token, **kwargs
        )
        if result is None:
            raise KciDevError(f"Maestro checkout failed for {giturl} at {commit}")
        return result

    def trigger_patchset(
        self,
        nodeid,
        patches=None,
        patchurls=None,
        job_filter=None,
        platform_filter=None,
        pipeline_url=None,
        token=None,
    ):
        """Test patches on top of an existing checkout node.

        Patches are passed inline as strings via patches, or as URLs from
        an allowed domain via patchurls. Exactly one of the two must be
        provided.
        """
        if bool(patches) == bool(patchurls):
            raise KciDevError("Exactly one of patches or patchurls must be provided")
        url = pipeline_url or self._instance_setting(
            "pipeline", human_readable_key="pipeline URL"
        )
        token = token or self._instance_setting("token")
        result = _as_library_error(
            "Maestro patchset failed",
            send_patchset,
            url,
            token,
            nodeid,
            patches=patches,
            patchurls=patchurls,
            job_filter=job_filter,
            platform_filter=platform_filter,
        )
        if result is None:
            raise KciDevError(f"Maestro patchset failed for node {nodeid}")
        return result
