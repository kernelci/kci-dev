#!/usr/bin/env python3

import click
from tabulate import tabulate

from kcidev.libs.common import kci_msg_red
from kcidev.libs.dashboard import (
    dashboard_fetch_boot_issues,
    dashboard_fetch_build_issues,
)
from kcidev.subcommands.results import boots, builds


def get_issues(ctx, origin, item_type, giturl, branch, commit, tree_name, arch):
    """Get KCIDB issues for builds/boots"""
    try:
        if item_type == "builds":
            results_cmd = builds
            dashboard_func = dashboard_fetch_build_issues
        elif item_type == "boots":
            results_cmd = boots
            dashboard_func = dashboard_fetch_boot_issues
        else:
            kci_msg_red("Please specify 'builds' or 'boots' as items type")
            return []

        dashboard_items = ctx.invoke(
            results_cmd,
            origin=origin,
            giturl=giturl,
            branch=branch,
            commit=commit,
            status="all",
            count=True,
            verbose=False,
            arch=arch,
        )
        final_stats = []
        for item in dashboard_items:
            # Exclude passed builds/boots
            if item["status"] == "PASS":
                continue
            item_id = item["id"]
            try:
                issues = dashboard_func(item_id, False)
                issue_ids = []
                for issue in issues:
                    issue_ids.append(issue["id"])
                final_stats.append([f"{tree_name}/{branch}", item_id, issue_ids])
            except click.ClickException as e:
                if e.message in (
                    "No issues were found for this build",
                    "No issues were found for this test",
                ):
                    final_stats.append([f"{tree_name}/{branch}", item_id, []])
        return final_stats
    except click.Abort:
        kci_msg_red(
            f"{tree_name}/{branch}: Aborted while fetching dashboard builds/boots"
        )
        return []
    except click.ClickException as e:
        kci_msg_red(f"{tree_name}/{branch}: {e.message}")
        return []


def get_issues_for_specific_item(item_type, item_id):
    """Get KCIDB issues for a specific build/boot matching provided ID"""
    try:
        if item_type == "builds":
            dashboard_func = dashboard_fetch_build_issues
        elif item_type == "boots":
            dashboard_func = dashboard_fetch_boot_issues
        else:
            kci_msg_red("Please specify 'builds' or 'boots' as items type")
            return []
        issues = dashboard_func(item_id, False)
        issue_ids = []
        for issue in issues:
            issue_ids.append(issue["id"])
        stats = [[item_id, issue_ids]]
        return stats
    except click.ClickException as e:
        if e.message == "No issues were found for this build":
            stats = [[item_id, []]]
            return stats
        return None


def print_stats(data, headers, max_col_width, table_fmt):
    """Print build statistics in tabular format"""
    print("Creating a stats report...")
    print(
        tabulate(data, headers=headers, maxcolwidths=max_col_width, tablefmt=table_fmt)
    )
