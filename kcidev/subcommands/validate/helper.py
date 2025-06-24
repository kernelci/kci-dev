#!/usr/bin/env python3

import click
from tabulate import tabulate

from kcidev.libs.common import kci_msg, kci_msg_json, kci_msg_red
from kcidev.subcommands.maestro.results import results
from kcidev.subcommands.results import builds


def get_builds(ctx, giturl, branch, commit, arch=None):
    """Get builds matching git URL, branch, and commit
    Architecture can also be provided for filtering"""
    maestro_builds = []
    dashboard_builds = []
    filters = [
        "kind=kbuild",
        "data.error_code__ne=node_timeout",  # maestro doesn't submit timed-out nodes
        "data.kernel_revision.url=" + giturl,
        "data.kernel_revision.branch=" + branch,
        "data.kernel_revision.commit=" + commit,
        "state__in=done,available",
    ]
    if arch:
        filters.append("data.arch=" + arch)
    maestro_builds = ctx.invoke(
        results,
        count=True,
        nodes=True,
        filter=filters,
        paginate=False,
    )
    try:
        dashboard_builds = ctx.invoke(
            builds,
            giturl=giturl,
            branch=branch,
            commit=commit,
            count=True,
            verbose=False,
        )
    except click.Abort:
        kci_msg_red("Aborted while fetching dashboard builds")
        return maestro_builds, None
    return maestro_builds, dashboard_builds


def find_missing_items(maestro_data, dashboard_data, verbose):
    """
    Compare build/boot IDs found in maestro with dashboard results
    Return missing builds/boots in dashboard.
    """
    dashboard_ids = [b["id"].split(":")[1] for b in dashboard_data]
    maestro_ids = [b["id"] for b in maestro_data]

    if len(maestro_ids) > len(dashboard_ids):
        missing_items = [b for b in maestro_data if b["id"] not in dashboard_ids]
        missing_ids = [b["id"] for b in missing_items]
    else:
        missing_items = [
            b for b in dashboard_data if b["id"].split(":")[1] not in maestro_ids
        ]
        missing_ids = [b["id"].split(":")[1] for b in missing_items]

    if missing_items and verbose:
        kci_msg("Missing items:")
        kci_msg_json(missing_items)

    return missing_ids


def validate_build_status(maestro_builds, dashboard_builds):
    """
    Validate if the build status of dashboard pulled build
    matches with the maestro build status
    """
    status_map = {
        "pass": "PASS",
        "fail": "FAIL",
        "incomplete": "ERROR",
    }
    builds_with_status_mismatch = []
    dashboard_build_status_dict = {
        b["id"].split(":")[1]: b["status"] for b in dashboard_builds
    }
    for b in maestro_builds:
        build_id = b["id"]
        if build_id in dashboard_build_status_dict:
            if dashboard_build_status_dict[build_id] != status_map.get(b["result"]):
                builds_with_status_mismatch.append(build_id)
    return builds_with_status_mismatch


def get_build_stats(ctx, giturl, branch, commit, tree_name, verbose, arch=None):
    """Get build stats"""
    maestro_builds, dashboard_builds = get_builds(ctx, giturl, branch, commit, arch)
    if dashboard_builds is None:
        return []
    missing_build_ids = []
    if len(dashboard_builds) == len(maestro_builds):
        count_comparison_flag = "✅"
    else:
        count_comparison_flag = "❌"
        missing_build_ids = find_missing_items(
            maestro_builds, dashboard_builds, verbose
        )
    builds_with_status_mismatch = validate_build_status(
        maestro_builds, dashboard_builds
    )
    stats = [
        f"{tree_name}/{branch}",
        commit,
        len(maestro_builds),
        len(dashboard_builds),
        count_comparison_flag,
        missing_build_ids,
        builds_with_status_mismatch,
    ]
    return stats


def print_stats(data, headers, max_col_width, table_fmt):
    """Print build statistics in tabular format"""
    print("Creating a stats report...")
    print(
        tabulate(data, headers=headers, maxcolwidths=max_col_width, tablefmt=table_fmt)
    )
