#!/usr/bin/env python3

import click

from kcidev.libs.common import kci_msg, kci_msg_green, kci_msg_json, kci_msg_red
from kcidev.subcommands.maestro_results import maestro_results
from kcidev.subcommands.results import builds


def get_builds(ctx, giturl, branch, commit, arch=None):
    """Get builds matching git URL, branch, and commit
    Architecture can also be provided for filtering"""
    maestro_builds = []
    dashboard_builds = []
    filters = [
        "kind=kbuild",
        "data.kernel_revision.url=" + giturl,
        "data.kernel_revision.branch=" + branch,
        "data.kernel_revision.commit=" + commit,
    ]
    if arch:
        filters.append("data.arch=" + arch)
    maestro_builds = ctx.invoke(
        maestro_results,
        count=True,
        nodes=True,
        filter=filters,
        paginate=False,
    )
    try:
        dashboard_builds = ctx.invoke(
            builds, giturl=giturl, branch=branch, commit=commit, count=True
        )
    except click.Abort:
        kci_msg_red("Aborted while fetching dashboard builds")
        return maestro_builds, []
    return maestro_builds, dashboard_builds


def find_missing_builds(maestro_builds, dashboard_builds, verbose):
    """
    Compare build IDs found in maestro with dashboard builds
    Return missing builds in dashboard.
    """
    missing_builds = []
    dashboard_build_id = [b["id"].split(":")[1] for b in dashboard_builds]
    for b in maestro_builds:
        if b["id"] not in dashboard_build_id:
            missing_builds.append(b)
    if missing_builds:
        if verbose:
            kci_msg("Missing builds:")
            kci_msg_json(missing_builds)
        else:
            missing_build_ids = [b["id"] for b in missing_builds]
            kci_msg(f"Missing build IDs:{missing_build_ids}")


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
    dashboard_build_status_dict = {b["id"]: b["status"] for b in dashboard_builds}
    for b in maestro_builds:
        build_id = f"maestro:{b['id']}"
        if build_id in dashboard_build_status_dict:
            if dashboard_build_status_dict[build_id] != status_map.get(b["result"]):
                kci_msg_red(f"Build status mismatched: {build_id}")


def get_build_stats(ctx, giturl, branch, commit, verbose, arch=None):
    """Get build stats"""
    maestro_builds, dashboard_builds = get_builds(ctx, giturl, branch, commit, arch)
    if len(dashboard_builds) == len(maestro_builds):
        kci_msg_green("Build count matched")
    else:
        kci_msg_red("Build count didn't match")
        find_missing_builds(maestro_builds, dashboard_builds, verbose)
    validate_build_status(maestro_builds, dashboard_builds)
