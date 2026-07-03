#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kcidev.libs.maestro_common import maestro_get_node, maestro_get_nodes
from kcidev.mcp.errors import ToolExecutionError, tool_errors
from kcidev.subcommands.checkout import send_checkout_full
from kcidev.subcommands.testretry import send_jobretry


def _retry_job(pipeline_url, token, node_id):
    result = send_jobretry(pipeline_url, node_id, token)
    if result is None:
        raise ToolExecutionError(f"Maestro job retry failed for node {node_id}")
    return result


def _trigger_checkout(
    pipeline_url, token, giturl, branch, commit, job_filter, platform_filter
):
    kwargs = {
        "giturl": giturl,
        "branch": branch,
        "commit": commit,
        "job_filter": job_filter,
    }
    if platform_filter:
        kwargs["platform_filter"] = platform_filter
    result = send_checkout_full(pipeline_url, token, **kwargs)
    if result is None:
        raise ToolExecutionError(f"Maestro checkout failed for {giturl} at {commit}")
    return result


def register_tools(server, api_url, pipeline_url, token):
    from mcp.types import ToolAnnotations

    read_only = ToolAnnotations(readOnlyHint=True)
    action = ToolAnnotations(readOnlyHint=False, destructiveHint=False)

    if api_url:

        @server.tool(annotations=read_only)
        @tool_errors
        def get_node(node_id: str):
            """Get a Maestro node (job, build or test run) by node id.

            Returns the full node including state (running, done, timeout),
            result (pass, fail, incomplete), artifacts and timestamps. Use
            this to poll a job started with trigger_checkout or retry_job.
            Node ids are 24-character hex strings.
            """
            return maestro_get_node(api_url, node_id)

        @server.tool(annotations=read_only)
        @tool_errors
        def list_nodes(
            filters: list[str] | None = None, limit: int = 50, offset: int = 0
        ):
            """List Maestro nodes, oldest first, optionally filtered.

            Filters are 'field=value' strings, for example 'name=checkout',
            'state=done', 'result=fail' or 'treeid=<tree id>'. Matching is
            exact; append '__re' to a field for a regex match, for example
            'name__re=baseline' matches all baseline job variants. Results
            are returned oldest first, so to reach recent nodes window the
            query with a filter such as 'created__gt=2026-07-01' rather
            than paginating from the start. Use limit and offset to
            paginate within the window.
            """
            return maestro_get_nodes(api_url, limit, offset, filters or [], True)

    if pipeline_url and token:

        @server.tool(annotations=action)
        @tool_errors
        def retry_job(node_id: str):
            """Retry a failed or incomplete KernelCI test job.

            Creates a new job for the given Maestro node id. Use list_nodes
            or the dashboard tools to find the node id of the failed job.
            """
            return _retry_job(pipeline_url, token, node_id)

        @server.tool(annotations=action)
        @tool_errors
        def trigger_checkout(
            giturl: str,
            branch: str,
            commit: str,
            job_filter: list[str],
            platform_filter: list[str] | None = None,
        ):
            """Trigger a custom KernelCI pipeline run for a tree/branch/commit.

            Starts a checkout of the given kernel git URL, branch and commit,
            running only the jobs named in job_filter (for example
            ['baseline-arm64']), optionally restricted to the platforms in
            platform_filter. Returns a tree id; poll progress with list_nodes
            using 'treeid=<tree id>'.
            """
            return _trigger_checkout(
                pipeline_url, token, giturl, branch, commit, job_filter, platform_filter
            )
