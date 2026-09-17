#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from contextvars import ContextVar
from functools import wraps

from kcidev.api import KciDevError, KernelCIClient
from kcidev.libs.filters import StatusFilter
from kcidev.mcp.errors import tool_errors
from kcidev.mcp.validation import check_page_args, check_page_bounds, checked_status

_active_client = ContextVar("dashboard_tool_client", default=None)


def _current_client():
    return _active_client.get() or KernelCIClient()


def _page(data, key, status, limit, offset, fields=None):
    check_page_bounds(limit, offset)
    items = data[key] if isinstance(data, dict) else data
    total = len(items)
    if status:
        status_filter = StatusFilter(checked_status(status))
        items = [item for item in items if status_filter.matches(item)]
    page = items[offset : offset + limit]
    if fields:
        page = [{k: item[k] for k in fields if k in item} for item in page]
    return {
        key: page,
        "total": total,
        "matched": len(items),
        "limit": limit,
        "offset": offset,
    }


@tool_errors
def list_trees(origin: str = "maestro", days: int = 7):
    """List kernel trees with recent results in the KernelCI dashboard.

    Returns tree names, git URLs, branches and latest commit hashes for
    the given origin over the last N days. Use this first to discover
    valid giturl/branch/commit values for the other query tools.
    """
    return _current_client().get_tree_list(origin, days)


_COMPACT_SUMMARY_KEYS = ("status", "architectures", "issues", "failed_platforms")


@tool_errors
def get_summary(
    giturl: str,
    branch: str,
    commit: str,
    origin: str = "maestro",
    arch: str | None = None,
    detail: bool = False,
):
    """Get the build/boot/test summary for one commit of a tree.

    Returns compact aggregated status counts by default; pass
    detail=True for the full dashboard summary (much larger). Use
    list_trees to find giturl, branch and commit values.
    """
    data = _current_client().get_summary(origin, giturl, branch, commit, arch)
    if detail or not isinstance(data, dict):
        return data
    summary = data.get("summary")
    if not isinstance(summary, dict):
        return data
    return {
        "common": data.get("common"),
        "summary": {
            section: {k: v for k, v in counts.items() if k in _COMPACT_SUMMARY_KEYS}
            for section, counts in summary.items()
            if isinstance(counts, dict)
        },
    }


@tool_errors
def compare_checkouts(
    giturl: str,
    branch: str,
    base: str,
    head: str,
    origin: str = "maestro",
    include_issues: bool = False,
):
    """Compare two checkouts, classifying regressions, fixes and unstable tests.
    The returned report preserves duplicate executions. Set ``include_issues``
    to look up known issue ids for failing/regressing results; this can require
    one additional request per result. ``incomplete`` means the report must not
    be treated as a successful CI gate.
    """
    return _current_client().compare_results(
        base, head, giturl, branch, origin, include_issues=include_issues
    )


@tool_errors
def list_commits(giturl: str, branch: str, commit: str, origin: str = "maestro"):
    """List recent checkouts of a tree with per-commit result counts.

    Returns the commit history leading up to the given commit hash, with
    aggregated build/boot/test status counts for each checkout. Use this
    to find earlier commits of a tree and compare results across
    checkouts with get_summary. The commit must be the full 40-character
    hash of a checkout the dashboard has ingested, such as a tree head
    hash from list_trees; other commits have no history record.
    """
    try:
        commits = _current_client().get_commits_history(origin, giturl, branch, commit)
    except KciDevError as e:
        if "not found" in str(e).lower():
            raise KciDevError(
                f"{e}; history only exists for ingested checkout commits, "
                "pass the full 40-character hash of a commit from list_trees"
            ) from e
        raise
    for entry in commits:
        if isinstance(entry.get("builds"), dict):
            entry["builds"] = {k.lower(): v for k, v in entry["builds"].items()}
    return commits


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
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    fields: list[str] | None = None,
):
    """List kernel builds for one commit of a tree.

    Optional filters: arch (e.g. 'arm64'), tree name, ISO date range, and
    status ('pass', 'fail', 'inconclusive' or 'all'). Results are paginated with
    limit/offset; the response carries 'total' (before status filtering)
    and 'matched' counts so you know whether to fetch further pages;
    fields projects each entry to only those keys.
    Returns build entries with ids usable with get_build.
    """
    check_page_args(status, limit, offset)
    data = _current_client().get_builds(
        origin, giturl, branch, commit, arch, tree, start_date, end_date
    )
    return _page(data, "builds", status, limit, offset, fields)


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
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    fields: list[str] | None = None,
):
    """List boot test results for one commit of a tree.

    Optional filters: arch, tree name, ISO date range, boot origin, and
    status ('pass', 'fail', 'inconclusive' or 'all'). Results are paginated with
    limit/offset; the response carries 'total' (before status filtering)
    and 'matched' counts so you know whether to fetch further pages;
    fields projects each entry to only those keys.
    Returns boot entries with ids usable with get_test.
    """
    check_page_args(status, limit, offset)
    data = _current_client().get_boots(
        origin, giturl, branch, commit, arch, tree, start_date, end_date, boot_origin
    )
    return _page(data, "boots", status, limit, offset, fields)


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
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    fields: list[str] | None = None,
):
    """List test results for one commit of a tree.

    Optional filters: arch, tree name, ISO date range, and status ('pass',
    'fail', 'inconclusive' or 'all'). A full commit can carry tens of thousands
    of tests, so filter by status and paginate with limit/offset; the
    response carries 'total' (before status filtering) and 'matched'
    counts so you know whether to fetch further pages; fields projects
    each entry to only those keys.
    Returns test entries with ids usable with get_test.
    """
    check_page_args(status, limit, offset)
    data = _current_client().get_tests(
        origin, giturl, branch, commit, arch, tree, start_date, end_date
    )
    return _page(data, "tests", status, limit, offset, fields)


@tool_errors
def get_build(build_id: str):
    """Get details for a single build by dashboard build id.

    Build ids look like 'maestro:<hex>'. Returns config, compiler, logs
    and status for the build.
    """
    return _current_client().get_build(build_id)


@tool_errors
def get_test(test_id: str):
    """Get details for a single test or boot by dashboard test id.

    Test ids look like 'maestro:<hex>'. Returns status, logs, environment
    and misc data for the test.
    """
    return _current_client().get_test(test_id)


@tool_errors
def get_log(test_id: str, max_bytes: int = 16384, tail: bool = True):
    """Fetch the raw log for a test or job by dashboard test id.

    Downloads and decompresses the log, resolving it from the test's
    log_url or, when that is empty (common for failures), a log entry in
    output_files. Returns it size-bounded: by default the last max_bytes,
    where failures usually are (set tail=false for the start). The
    response reports total_bytes and truncated so you can widen max_bytes
    if needed, up to a 1 MiB ceiling: asking for more returns that
    ceiling rather than the whole log, so compare returned_bytes with
    total_bytes rather than retrying the same call. A download that runs
    past about a minute stops early and sets deadline_exceeded. Use
    get_test first for the shorter log_excerpt.
    """
    return _current_client().get_log(test_id, max_bytes=max_bytes, tail=tail)


@tool_errors
def get_test_issues(test_id: str):
    """List known issues detected on a specific test or boot.

    Use this to check a failing test against issues KernelCI already
    tracks before treating the failure as new. Test ids look like
    'maestro:<hex>'.
    """
    return _current_client().get_boot_issues(test_id)


@tool_errors
def get_build_issues(build_id: str):
    """List known issues detected on a specific build.

    Use this to check a failing build against issues KernelCI already
    tracks before treating the failure as new. Build ids look like
    'maestro:<hex>'.
    """
    return _current_client().get_build_issues(build_id)


@tool_errors
def list_hardware(origin: str = "maestro"):
    """List hardware platforms with results over the last 7 days.

    Returns platform names usable with get_hardware_summary.
    """
    return _current_client().get_hardware_list(origin)


@tool_errors
def get_hardware_summary(name: str, origin: str = "maestro"):
    """Get the build/boot/test summary for one hardware platform.

    Covers the last 7 days. Use list_hardware to find platform names.
    """
    return _current_client().get_hardware_summary(name, origin)


@tool_errors
def list_issues(origin: str = "maestro", days: int = 7):
    """List known issues (recognised failure patterns) from the dashboard.

    Returns issue ids and descriptions for the last N days. Issue ids
    are usable with get_issue, get_issue_builds and get_issue_tests.
    """
    return _current_client().get_issue_list(origin, days)


@tool_errors
def get_issue(issue_id: str):
    """Get details for a single known issue by issue id.

    Issue ids look like 'maestro:<hex>'.
    """
    return _current_client().get_issue(issue_id)


@tool_errors
def get_issue_builds(
    issue_id: str,
    origin: str = "maestro",
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    fields: list[str] | None = None,
):
    """List builds affected by a known issue.

    An empty list means the issue has no builds recorded against it, and
    also what an unknown issue id returns, since the dashboard reports
    both the same way; confirm the id with get_issue if it matters.
    Optional status filter ('pass', 'fail', 'inconclusive' or 'all') and
    limit/offset pagination; the response carries 'total' and 'matched'
    counts; fields projects each entry to only those keys.
    """
    check_page_args(status, limit, offset)
    data = _current_client().get_issue_builds(issue_id, origin)
    return _page(data, "builds", status, limit, offset, fields)


@tool_errors
def get_issue_tests(
    issue_id: str,
    origin: str = "maestro",
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    fields: list[str] | None = None,
):
    """List tests affected by a known issue.

    An empty list means the issue has no tests recorded against it, and
    also what an unknown issue id returns, since the dashboard reports
    both the same way; confirm the id with get_issue if it matters.
    Optional status filter ('pass', 'fail', 'inconclusive' or 'all') and
    limit/offset pagination; the response carries 'total' and 'matched'
    counts; fields projects each entry to only those keys.
    """
    check_page_args(status, limit, offset)
    data = _current_client().get_issue_tests(issue_id, origin)
    return _page(data, "tests", status, limit, offset, fields)


READ_ONLY_TOOLS = (
    list_trees,
    get_summary,
    compare_checkouts,
    list_commits,
    list_builds,
    list_boots,
    list_tests,
    get_build,
    get_test,
    get_log,
    get_test_issues,
    get_build_issues,
    list_hardware,
    get_hardware_summary,
    list_issues,
    get_issue,
    get_issue_builds,
    get_issue_tests,
)


def register_tools(server, client):
    from mcp.types import ToolAnnotations

    for tool in READ_ONLY_TOOLS:

        @wraps(tool)
        def bound_tool(*args, __tool=tool, **kwargs):
            token = _active_client.set(client)
            try:
                return __tool(*args, **kwargs)
            finally:
                _active_client.reset(token)

        server.tool(annotations=ToolAnnotations(readOnlyHint=True))(bound_tool)
