#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Public Python API for using kci-dev as a library.

The CLI remains the primary user interface, but applications can import this
module to build and submit KCIDB payloads or query KernelCI dashboard data
without invoking Click commands or shelling out to ``kci-dev``.
"""

from datetime import datetime, timezone

import click
from click.testing import CliRunner

from kcidev.libs.dashboard import (
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
)
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


class KernelCIClient:
    """Client for interacting with KernelCI services from Python code.

    Args:
        cfg: Optional kci-dev configuration dictionary, for example the result
            of :func:`kcidev.libs.common.load_toml`.
        instance: Optional instance name in ``cfg``.
        kcidb_rest_url: Optional KCIDB submit endpoint override.
        kcidb_token: Optional KCIDB bearer token override.
    """

    def __init__(self, cfg=None, instance=None, kcidb_rest_url=None, kcidb_token=None):
        self.cfg = cfg
        self.instance = instance
        self.kcidb_rest_url = kcidb_rest_url
        self.kcidb_token = kcidb_token

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
        return _as_library_error(
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
        return _as_library_error(
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
        return _as_library_error(
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
        return _as_library_error(
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
        return _as_library_error(
            "Dashboard history request failed",
            dashboard_fetch_commits_history,
            origin,
            giturl,
            branch,
            commit,
            True,
        )

    def get_build(self, build_id):
        return _as_library_error(
            "Dashboard build request failed", dashboard_fetch_build, build_id, True
        )

    def get_test(self, test_id):
        return _as_library_error(
            "Dashboard test request failed", dashboard_fetch_test, test_id, True
        )

    def get_tree_list(self, origin, days=7):
        return _as_library_error(
            "Dashboard tree list request failed",
            dashboard_fetch_tree_list,
            origin,
            True,
            days,
        )

    def get_hardware_list(self, origin):
        return _as_library_error(
            "Dashboard hardware list request failed",
            dashboard_fetch_hardware_list,
            origin,
            True,
        )

    def get_hardware_summary(self, name, origin):
        return _as_library_error(
            "Dashboard hardware summary request failed",
            dashboard_fetch_hardware_summary,
            name,
            origin,
            True,
        )

    def get_hardware_boots(self, name, origin):
        return _as_library_error(
            "Dashboard hardware boots request failed",
            dashboard_fetch_hardware_boots,
            name,
            origin,
            True,
        )

    def get_hardware_builds(self, name, origin):
        return _as_library_error(
            "Dashboard hardware builds request failed",
            dashboard_fetch_hardware_builds,
            name,
            origin,
            True,
        )

    def get_hardware_tests(self, name, origin):
        return _as_library_error(
            "Dashboard hardware tests request failed",
            dashboard_fetch_hardware_tests,
            name,
            origin,
            True,
        )

    def get_build_issues(self, build_id):
        return _as_library_error(
            "Dashboard build issues request failed",
            dashboard_fetch_build_issues,
            build_id,
            True,
            True,
        )

    def get_boot_issues(self, test_id):
        return _as_library_error(
            "Dashboard boot issues request failed",
            dashboard_fetch_boot_issues,
            test_id,
            True,
            True,
        )

    def get_issue_list(self, origin=None, days=7):
        return _as_library_error(
            "Dashboard issue list request failed",
            dashboard_fetch_issue_list,
            origin,
            days,
            True,
        )

    def get_issue(self, issue_id):
        return _as_library_error(
            "Dashboard issue request failed", dashboard_fetch_issue, issue_id, True
        )

    def get_issue_builds(self, issue_id, origin=None):
        return _as_library_error(
            "Dashboard issue builds request failed",
            dashboard_fetch_issue_builds,
            origin,
            issue_id,
            True,
        )

    def get_issue_tests(self, issue_id, origin=None):
        return _as_library_error(
            "Dashboard issue tests request failed",
            dashboard_fetch_issue_tests,
            origin,
            issue_id,
            True,
        )

    def get_issues_extra(self, issues):
        return _as_library_error(
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
        max_age_in_hours=None,
        min_age_in_hours=None,
    ):
        return _as_library_error(
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
