#!/usr/bin/env python3

from datetime import datetime, timedelta

import click
from tabulate import tabulate

from kcidev.libs.common import kci_msg, kci_msg_bold, kci_msg_json, kci_msg_red
from kcidev.subcommands.maestro.results import results
from kcidev.subcommands.results import boots, builds


def get_builds(ctx, giturl, branch, commit, arch):
    """Get builds matching git URL, branch, and commit
    Architecture can also be provided for filtering"""
    maestro_builds = []
    dashboard_builds = []
    filters = [
        "kind=kbuild",
        "data.kernel_revision.url=" + giturl,
        "data.kernel_revision.branch=" + branch,
        "data.kernel_revision.commit=" + commit,
        "state__in=done,available",
    ]
    if arch:
        filters.append("data.arch=" + arch)
    maestro_builds = ctx.invoke(
        results,
        nodes=True,
        filter=filters,
        paginate=False,
        verbose=False,
    )
    try:
        dashboard_builds = ctx.invoke(
            builds,
            giturl=giturl,
            branch=branch,
            commit=commit,
            count=True,
            verbose=False,
            arch=arch,
        )
    except click.Abort:
        kci_msg_red(f"{branch}/{commit}: Aborted while fetching dashboard builds")
        return maestro_builds, None
    except click.ClickException as e:
        kci_msg_red(f"{branch}/{commit}: {e.message}")
        if "No builds available" in e.message:
            return maestro_builds, []
        return maestro_builds, None
    return maestro_builds, dashboard_builds


def find_missing_items(maestro_data, dashboard_data, item_type, verbose):
    """
    Compare build/boot IDs found in maestro with dashboard results
    Return missing builds/boots in dashboard.
    """
    dashboard_ids = [b["id"].split(":")[1] for b in dashboard_data]

    if item_type == "build":
        # Exclude build retries
        maestro_data = [
            b
            for b in maestro_data
            if (b["result"] != "incomplete" or b["retry_counter"] == 3)
        ]
    elif item_type == "boot":
        # Exclude boot retries
        maestro_data = [
            b
            for b in maestro_data
            if (b["result"] not in {"incomplete", "fail"} or b["retry_counter"] == 3)
        ]

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


def get_build_stats(ctx, giturl, branch, commit, tree_name, verbose, arch):
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
            maestro_builds, dashboard_builds, "build", verbose
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


def print_table_stats(data, headers, max_col_width, table_fmt):
    """Print build statistics in tabular format"""
    print("Creating a stats report...")
    print(
        tabulate(data, headers=headers, maxcolwidths=max_col_width, tablefmt=table_fmt)
    )


def extract_validation_data(row: list):
    """Extract information from validation stats"""
    try:
        tree_branch = row[0]
        commit = row[1]  # Commit hash
        comparison = row[4]  # Build/boot count comparison (✅ or ❌)
        missing_ids = row[5]  # Missing build/boot IDs
        return tree_branch, commit, comparison, missing_ids
    except IndexError:
        kci_msg_red("Failed to extract data for list view report")
        raise ValueError()


def print_simple_list(data, item_type, history=False):
    """Print a simple list format showing tree/branch with status and missing IDs"""

    if history:
        # For history mode, group by tree/branch and show overall status
        from collections import defaultdict

        tree_groups = defaultdict(list)

        for row in data:
            try:
                tree_branch, commit, comparison, missing_ids = extract_validation_data(
                    row
                )
            except ValueError:
                continue
            tree_groups[tree_branch].append(
                {"commit": commit, "status": comparison, "missing_ids": missing_ids}
            )

        for tree_branch, commits in tree_groups.items():
            kci_msg_bold(f"{tree_branch}: ")
            for commit in commits:
                if commit["status"] == "❌" and commit["missing_ids"]:
                    kci_msg(f"  Commit {commit['commit'][:12]}: ❌")
                    kci_msg(f"  Missing {item_type}: {len(commit['missing_ids'])}")
                    for id in commit["missing_ids"]:
                        kci_msg(f"  - https://api.kernelci.org/viewer?node_id={id}")
                elif commit["status"] == "✅":
                    kci_msg(f"  Commit {commit['commit'][:12]}: ✅")

    else:
        # For non-history mode, show each individual result
        for row in data:
            try:
                tree_branch, commit, comparison, missing_ids = extract_validation_data(
                    row
                )
            except ValueError:
                continue
            kci_msg_bold(f"• {tree_branch}: ", nl=False)
            kci_msg(f"{comparison}")
            kci_msg(f"  Commit: {commit}")

            if comparison == "❌" and missing_ids:
                kci_msg(f"  Missing {item_type}: {len(missing_ids)}")
                for id in missing_ids:
                    kci_msg(f"  - https://api.kernelci.org/viewer?node_id={id}")
            elif comparison == "❌":
                kci_msg(f"  Has mismatch but no missing IDs listed")
            kci_msg("")


def validate_boot_status(maestro_boots, dashboard_boots):
    """
    Validate if the boot status of dashboard pulled boot
    matches with the maestro boot status
    """
    MISSED_TEST_CODES = (
        "Bug",
        "Configuration",
        "invalid_job_params",
        "Job",
        "job_generation_error",
        "ObjectNotPersisted",
        "RequestBodyTooLarge",
        "submit_error",
        "Unexisting permission codename.",
        "kbuild_internal_error",
    )

    ERRORED_TEST_CODES = (
        "Canceled",
        "Infrastructure",
        "LAVATimeout",
        "MultinodeTimeout",
        "Test",
    )

    status_map = {
        "pass": "PASS",
        "fail": "FAIL",
    }

    boots_with_status_mismatch = []
    dashboard_boot_status_dict = {
        b["id"].split(":")[1]: b["status"] for b in dashboard_boots
    }
    for b in maestro_boots:
        boot_id = b["id"]
        if boot_id in dashboard_boot_status_dict:
            if b["result"] == "incomplete":
                result = None
                if b["data"].get("error_code") in MISSED_TEST_CODES:
                    result = "MISS"
                elif b["data"].get("error_code") in ERRORED_TEST_CODES:
                    result = "ERROR"
                if dashboard_boot_status_dict[boot_id] != result:
                    boots_with_status_mismatch.append(boot_id)
            elif dashboard_boot_status_dict[boot_id] != status_map.get(b["result"]):
                boots_with_status_mismatch.append(boot_id)
    return boots_with_status_mismatch


def get_boots(ctx, giturl, branch, commit, arch):
    """Get boots matching git URL, branch, and commit"""
    maestro_boots = []
    dashboard_boots = []
    filters = [
        "name__re=^baseline",
        "data.kernel_revision.url=" + giturl,
        "data.kernel_revision.branch=" + branch,
        "data.kernel_revision.commit=" + commit,
        "state=done",
    ]
    if arch:
        filters.append(f"data.arch={arch}")
    maestro_boots = ctx.invoke(
        results,
        nodes=True,
        filter=filters,
        paginate=False,
        verbose=False,
    )
    try:
        dashboard_boots = ctx.invoke(
            boots,
            giturl=giturl,
            branch=branch,
            commit=commit,
            count=True,
            verbose=False,
            arch=arch,
            boot_origin="maestro",
        )
    except click.Abort:
        kci_msg_red(f"{branch}/{commit}: Aborted while fetching dashboard boots")
        return maestro_boots, None
    except click.ClickException as e:
        kci_msg_red(f"{branch}/{commit}: {e.message}")
        if "No boots available" in e.message:
            return maestro_boots, []
        return maestro_boots, None
    return maestro_boots, dashboard_boots


def get_boot_stats(ctx, giturl, branch, commit, tree_name, verbose, arch):
    """Get boot stats"""
    maestro_boots, dashboard_boots = get_boots(ctx, giturl, branch, commit, arch)
    if dashboard_boots is None:
        return []
    missing_boot_ids = []
    if len(dashboard_boots) == len(maestro_boots):
        count_comparison_flag = "✅"
    else:
        count_comparison_flag = "❌"
        missing_boot_ids = find_missing_items(
            maestro_boots, dashboard_boots, "boot", verbose
        )
    boots_with_status_mismatch = validate_boot_status(maestro_boots, dashboard_boots)
    stats = [
        f"{tree_name}/{branch}",
        commit,
        len(maestro_boots),
        len(dashboard_boots),
        count_comparison_flag,
        missing_boot_ids,
        boots_with_status_mismatch,
    ]
    return stats


def get_builds_history_stats(ctx, giturl, branch, tree_name, arch, days, verbose):
    checkouts = get_checkouts(ctx, giturl, branch, days)
    final_stats = []
    builds_history = get_builds_history(ctx, checkouts, arch)
    for b in builds_history:
        missing_build_ids = find_missing_items(b[1], b[2], "build", verbose)
        total_maestro_builds = len(b[1])
        total_dashboard_builds = len(b[2])
        stats = [
            f"{tree_name}/{branch}",
            b[0],
            total_maestro_builds,
            total_dashboard_builds,
            "✅" if total_maestro_builds == total_dashboard_builds else "❌",
            missing_build_ids,
        ]
        final_stats.append(stats)
    return final_stats


def get_checkouts(ctx, giturl, branch, days):
    """Get checkouts upto last specified days for a particular git
    URL and branch"""
    now = datetime.now()
    start_timestamp = now - timedelta(days=days)
    filters = [
        "kind=checkout",
        "data.kernel_revision.url=" + giturl,
        "data.kernel_revision.branch=" + branch,
        "state=done",
        "created__gte=" + start_timestamp.isoformat(),
    ]
    checkouts = ctx.invoke(
        results,
        count=True,
        nodes=True,
        filter=filters,
        paginate=False,
    )
    return checkouts


def get_builds_history(ctx, checkouts, arch):
    """Get builds from maestro and dashboard for provided checkouts"""
    builds_history = []
    for c in checkouts:
        commit = c["data"]["kernel_revision"].get("commit")
        filters = [
            "kind=kbuild",
            "data.error_code__ne=node_timeout",
            "parent=" + c["id"],
            "state__in=done,available",
        ]
        if arch:
            filters.append(f"data.arch={arch}")
        maestro_builds = ctx.invoke(
            results,
            count=True,
            nodes=True,
            filter=filters,
            paginate=False,
        )

        branch = c["data"]["kernel_revision"].get("branch")
        try:
            dashboard_builds = ctx.invoke(
                builds,
                giturl=c["data"]["kernel_revision"].get("url"),
                branch=branch,
                commit=commit,
                count=True,
                verbose=False,
                arch=arch,
            )
            builds_history.append([commit, maestro_builds, dashboard_builds])
        except click.Abort:
            kci_msg_red(f"{branch}/{commit}: Aborted while fetching dashboard builds")
        except click.ClickException as e:
            kci_msg_red(f"{branch}/{commit}: {e.message}")
            if "No builds available" in e.message:
                builds_history.append([commit, maestro_builds, []])
    return builds_history
