#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kcidev.libs.dashboard import (
    dashboard_fetch_boots,
    dashboard_fetch_build,
    dashboard_fetch_builds,
    dashboard_fetch_hardware_list,
    dashboard_fetch_hardware_summary,
    dashboard_fetch_issue,
    dashboard_fetch_issue_builds,
    dashboard_fetch_issue_list,
    dashboard_fetch_issue_tests,
    dashboard_fetch_summary,
    dashboard_fetch_test,
    dashboard_fetch_tests,
    dashboard_fetch_tree_list,
)
from kcidev.mcp.errors import tool_errors


@tool_errors
def list_trees(origin: str = "maestro", days: int = 7):
    """List kernel trees with recent results in the KernelCI dashboard.

    Returns tree names, git URLs, branches and latest commit hashes for
    the given origin over the last N days. Use this first to discover
    valid giturl/branch/commit values for the other query tools.
    """
    return dashboard_fetch_tree_list(origin, True, days)


@tool_errors
def get_summary(
    giturl: str,
    branch: str,
    commit: str,
    origin: str = "maestro",
    arch: str | None = None,
):
    """Get the build/boot/test summary for one commit of a tree.

    Returns aggregated pass/fail/inconclusive counts. Use list_trees to
    find giturl, branch and commit values.
    """
    return dashboard_fetch_summary(origin, giturl, branch, commit, arch, True)


@tool_errors
def list_builds(
    giturl: str,
    branch: str,
    commit: str,
    origin: str = "maestro",
    arch: str | None = None,
    tree: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """List kernel builds for one commit of a tree.

    Optional filters: arch (e.g. 'arm64'), tree name, ISO date range.
    Returns build entries with ids usable with get_build.
    """
    return dashboard_fetch_builds(
        origin, giturl, branch, commit, arch, tree, start_date, end_date, True
    )


@tool_errors
def list_boots(
    giturl: str,
    branch: str,
    commit: str,
    origin: str = "maestro",
    arch: str | None = None,
    tree: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    boot_origin: str | None = None,
):
    """List boot test results for one commit of a tree.

    Optional filters: arch, tree name, ISO date range, boot origin.
    Returns boot entries with ids usable with get_test.
    """
    return dashboard_fetch_boots(
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


@tool_errors
def list_tests(
    giturl: str,
    branch: str,
    commit: str,
    origin: str = "maestro",
    arch: str | None = None,
    tree: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """List test results for one commit of a tree.

    Optional filters: arch, tree name, ISO date range.
    Returns test entries with ids usable with get_test.
    """
    return dashboard_fetch_tests(
        origin, giturl, branch, commit, arch, tree, start_date, end_date, True
    )


@tool_errors
def get_build(build_id: str):
    """Get details for a single build by dashboard build id.

    Build ids look like 'maestro:<hex>'. Returns config, compiler, logs
    and status for the build.
    """
    return dashboard_fetch_build(build_id, True)


@tool_errors
def get_test(test_id: str):
    """Get details for a single test or boot by dashboard test id.

    Test ids look like 'maestro:<hex>'. Returns status, logs, environment
    and misc data for the test.
    """
    return dashboard_fetch_test(test_id, True)


@tool_errors
def list_hardware(origin: str = "maestro"):
    """List hardware platforms with results over the last 7 days.

    Returns platform names usable with get_hardware_summary.
    """
    return dashboard_fetch_hardware_list(origin, True)


@tool_errors
def get_hardware_summary(name: str, origin: str = "maestro"):
    """Get the build/boot/test summary for one hardware platform.

    Covers the last 7 days. Use list_hardware to find platform names.
    """
    return dashboard_fetch_hardware_summary(name, origin, True)


@tool_errors
def list_issues(origin: str = "maestro", days: int = 7):
    """List known issues (recognised failure patterns) from the dashboard.

    Returns issue ids and descriptions for the last N days. Issue ids
    are usable with get_issue, get_issue_builds and get_issue_tests.
    """
    return dashboard_fetch_issue_list(origin, days, True)


@tool_errors
def get_issue(issue_id: str):
    """Get details for a single known issue by issue id.

    Issue ids look like 'maestro:<hex>'.
    """
    return dashboard_fetch_issue(issue_id, True)


@tool_errors
def get_issue_builds(issue_id: str, origin: str = "maestro"):
    """List builds affected by a known issue."""
    return dashboard_fetch_issue_builds(origin, issue_id, True)


@tool_errors
def get_issue_tests(issue_id: str, origin: str = "maestro"):
    """List tests affected by a known issue."""
    return dashboard_fetch_issue_tests(origin, issue_id, True)


READ_ONLY_TOOLS = (
    list_trees,
    get_summary,
    list_builds,
    list_boots,
    list_tests,
    get_build,
    get_test,
    list_hardware,
    get_hardware_summary,
    list_issues,
    get_issue,
    get_issue_builds,
    get_issue_tests,
)


def register_tools(server):
    from mcp.types import ToolAnnotations

    for tool in READ_ONLY_TOOLS:
        server.tool(annotations=ToolAnnotations(readOnlyHint=True))(tool)
