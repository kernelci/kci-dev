#!/usr/bin/env python3

import json
from datetime import datetime, timedelta

import click
from tabulate import tabulate

from kcidev.libs.common import kci_msg, kci_msg_bold, kci_msg_json, kci_msg_red
from kcidev.subcommands.maestro.results import results
from kcidev.subcommands.results import boots, builds


def get_builds(ctx, giturl, branch, commit, arch, raise_errors=False):
    """Get builds matching git URL, branch, and commit
    Architecture can also be provided for filtering"""
    maestro_builds = []
    dashboard_builds = []
    filters = [
        "kind=kbuild",
        "data.kernel_revision.url=" + giturl,
        "data.kernel_revision.branch=" + branch,
        "data.kernel_revision.commit=" + commit,
        "state__ne=running",
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
        if raise_errors:
            raise
        kci_msg_red(f"{branch}/{commit}: Aborted while fetching dashboard builds")
        return maestro_builds, None
    except click.ClickException as e:
        if "No builds available" in e.message:
            return maestro_builds, []
        if raise_errors:
            raise
        kci_msg_red(f"{branch}/{commit}: {e.message}")
        return maestro_builds, None
    return maestro_builds, dashboard_builds


def filter_maestro_items_for_validation(maestro_data, item_type):
    """
    Return Maestro items that should be compared against dashboard results.

    Retry filtering must be shared by counts, missing-item checks, and status
    checks so all validation fields describe the same item set.
    """
    if item_type == "build":
        # Exclude build retries
        return [
            b
            for b in maestro_data
            if (b["result"] != "incomplete" or b["retry_counter"] == 3)
        ]
    if item_type == "boot":
        # Exclude boot retries; job-retry only retries failed baseline jobs
        return [
            b
            for b in maestro_data
            if b["retry_counter"] == 3
            or not (
                b["result"] == "incomplete"
                or (b["result"] == "fail" and b["name"].startswith("baseline"))
            )
        ]
    return maestro_data


def find_missing_items(maestro_data, dashboard_data, item_type, verbose):
    """
    Compare build/boot IDs found in maestro with dashboard results
    Return missing builds/boots in dashboard.
    """
    maestro_data = filter_maestro_items_for_validation(maestro_data, item_type)
    dashboard_ids = [b["id"].split(":")[1] for b in dashboard_data]

    missing_items = [b for b in maestro_data if b["id"] not in dashboard_ids]
    missing_ids = [b["id"] for b in missing_items]

    if missing_items and verbose:
        kci_msg("Missing items:")
        kci_msg_json(missing_items)

    return missing_ids


def find_extra_dashboard_items(maestro_data, dashboard_data, item_type, verbose):
    """
    Compare build/boot IDs found in dashboard with Maestro results.
    Return dashboard builds/boots that are not present in Maestro.
    """
    maestro_data = filter_maestro_items_for_validation(maestro_data, item_type)
    maestro_ids = {b["id"] for b in maestro_data}

    extra_items = [
        b for b in dashboard_data if b["id"].split(":")[1] not in maestro_ids
    ]
    extra_ids = [b["id"].split(":")[1] for b in extra_items]

    if extra_items and verbose:
        kci_msg("Extra dashboard items:")
        kci_msg_json(extra_items)

    return extra_ids


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


def get_build_stats(
    ctx, giturl, branch, commit, tree_name, verbose, arch, raise_errors=False
):
    """Get build stats"""
    maestro_builds, dashboard_builds = get_builds(
        ctx, giturl, branch, commit, arch, raise_errors
    )
    if dashboard_builds is None:
        return []
    maestro_builds = filter_maestro_items_for_validation(maestro_builds, "build")
    summary_flag = "✅"
    missing_build_ids = find_missing_items(
        maestro_builds, dashboard_builds, "build", verbose
    )
    extra_dashboard_build_ids = find_extra_dashboard_items(
        maestro_builds, dashboard_builds, "build", verbose
    )
    builds_with_status_mismatch = validate_build_status(
        maestro_builds, dashboard_builds
    )
    if (
        len(dashboard_builds) != len(maestro_builds)
        or missing_build_ids
        or extra_dashboard_build_ids
        or builds_with_status_mismatch
    ):
        summary_flag = "❌"
    stats = [
        f"{tree_name}/{branch}",
        commit,
        len(maestro_builds),
        len(dashboard_builds),
        summary_flag,
        missing_build_ids,
        builds_with_status_mismatch,
        extra_dashboard_build_ids,
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
        mismatched_ids = row[6]
        extra_dashboard_ids = row[7] or [] if len(row) > 7 else []
        return (
            tree_branch,
            commit,
            comparison,
            missing_ids,
            mismatched_ids,
            extra_dashboard_ids,
        )
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
                (
                    tree_branch,
                    commit,
                    comparison,
                    missing_ids,
                    mismatched_ids,
                    extra_dashboard_ids,
                ) = extract_validation_data(row)
            except ValueError:
                continue
            tree_groups[tree_branch].append(
                {
                    "commit": commit,
                    "status": comparison,
                    "missing_ids": missing_ids,
                    "mismatched_ids": mismatched_ids,
                    "extra_dashboard_ids": extra_dashboard_ids,
                }
            )

        for tree_branch, commits in tree_groups.items():
            kci_msg_bold(f"{tree_branch}: ")
            for commit in commits:
                if commit["status"] == "❌":
                    kci_msg(f"  Commit {commit['commit'][:12]}: ❌")
                    if commit["missing_ids"]:
                        kci_msg(f"  Missing {item_type}: {len(commit['missing_ids'])}")
                        for id in commit["missing_ids"]:
                            kci_msg(f"  - https://api.kernelci.org/viewer?node_id={id}")
                    if commit["mismatched_ids"]:
                        kci_msg(
                            f"  Status mismatched {item_type}: {len(commit['mismatched_ids'])}"
                        )
                        for id in commit["mismatched_ids"]:
                            kci_msg(f"  - https://api.kernelci.org/viewer?node_id={id}")
                    if commit["extra_dashboard_ids"]:
                        kci_msg(
                            f"  Extra dashboard {item_type}: {len(commit['extra_dashboard_ids'])}"
                        )
                        for id in commit["extra_dashboard_ids"]:
                            kci_msg(f"  - https://api.kernelci.org/viewer?node_id={id}")
                elif commit["status"] == "✅":
                    kci_msg(f"  Commit {commit['commit'][:12]}: ✅")

    else:
        # For non-history mode, show each individual result
        for row in data:
            try:
                (
                    tree_branch,
                    commit,
                    comparison,
                    missing_ids,
                    mismatched_ids,
                    extra_dashboard_ids,
                ) = extract_validation_data(row)
            except ValueError:
                continue
            kci_msg_bold(f"• {tree_branch}: ", nl=False)
            kci_msg(f"{comparison}")
            kci_msg(f"  Commit: {commit}")

            if comparison == "❌" and missing_ids:
                kci_msg(f"  Missing {item_type}: {len(missing_ids)}")
                for id in missing_ids:
                    kci_msg(f"  - https://api.kernelci.org/viewer?node_id={id}")
            if comparison == "❌" and mismatched_ids:
                kci_msg(f"  Status mismatched {item_type}: {len(mismatched_ids)}")
                for id in mismatched_ids:
                    kci_msg(f"  - https://api.kernelci.org/viewer?node_id={id}")
            if comparison == "❌" and extra_dashboard_ids:
                kci_msg(f"  Extra dashboard {item_type}: {len(extra_dashboard_ids)}")
                for id in extra_dashboard_ids:
                    kci_msg(f"  - https://api.kernelci.org/viewer?node_id={id}")
            kci_msg("")


def validation_rows_to_json(kind, rows, history, origin, days, arch):
    """Convert validation stats rows to the public JSON report format."""
    results = []
    for row in rows:
        missing_ids = row[5] or []
        status_mismatch_ids = row[6] or []
        extra_dashboard_ids = row[7] or [] if len(row) > 7 else []
        ok = row[2] == row[3] and row[4] == "✅" and not missing_ids
        ok = ok and not status_mismatch_ids and not extra_dashboard_ids
        results.append(
            {
                "tree_branch": row[0],
                "commit": row[1],
                "maestro_count": row[2],
                "dashboard_count": row[3],
                "ok": ok,
                "missing_ids": missing_ids,
                "extra_in_dashboard_ids": extra_dashboard_ids,
                "status_mismatch_ids": status_mismatch_ids,
            }
        )

    return {
        "kind": kind,
        "history": history,
        "origin": origin,
        "days": days,
        "arch": arch,
        "summary": {
            "checked": len(results),
            "failed": sum(not result["ok"] for result in results),
            "missing": sum(len(result["missing_ids"]) for result in results),
            "extra_in_dashboard": sum(
                len(result["extra_in_dashboard_ids"]) for result in results
            ),
            "status_mismatches": sum(
                len(result["status_mismatch_ids"]) for result in results
            ),
            "ok": all(result["ok"] for result in results),
        },
        "results": results,
    }


def validation_report_to_text(report):
    """Render a JSON validation report as human-readable text."""
    item_type = report["kind"][:-1] if report["kind"].endswith("s") else report["kind"]
    summary = report["summary"]
    scope = [
        f"origin={report['origin']}",
        f"days={report['days']}",
        f"history={'yes' if report['history'] else 'no'}",
    ]
    if report.get("arch"):
        scope.append(f"arch={report['arch']}")
    else:
        scope.append("arch=all")

    status = "PASS" if summary["ok"] else "FAIL"
    lines = [
        f"Dashboard validation: {report['kind']} ({status})",
        f"Scope: {', '.join(scope)}",
        (
            "Summary: "
            f"checked={summary['checked']}, "
            f"failed={summary['failed']}, "
            f"missing={summary['missing']}, "
            f"extra_in_dashboard={summary['extra_in_dashboard']}, "
            f"status_mismatches={summary['status_mismatches']}"
        ),
    ]

    if report["results"]:
        lines.append("")
        lines.append(
            "Note: count comparisons use raw query totals; missing IDs are "
            "reported after validation filtering. Extra dashboard IDs are "
            "dashboard rows not present in the filtered Maestro set."
        )

    for result in report["results"]:
        result_status = "PASS" if result["ok"] else "FAIL"
        commit = result["commit"]
        delta = result["maestro_count"] - result["dashboard_count"]
        if delta > 0:
            delta_text = f"{delta} more in Maestro"
        elif delta < 0:
            delta_text = f"{-delta} more in dashboard"
        else:
            delta_text = "counts match"

        lines.extend(
            [
                "",
                f"{result['tree_branch']} @ {commit[:12]}: {result_status}",
                f"  Commit: {commit}",
                f"  Maestro {report['kind']}: {result['maestro_count']}",
                f"  Dashboard {report['kind']}: {result['dashboard_count']}",
                f"  Count delta: {delta_text}",
            ]
        )

        missing_ids = result["missing_ids"]
        extra_dashboard_ids = result["extra_in_dashboard_ids"]
        status_mismatch_ids = result["status_mismatch_ids"]
        if missing_ids:
            lines.append(f"  Missing {item_type} IDs: {len(missing_ids)}")
            for node_id in missing_ids:
                lines.append(f"    - https://api.kernelci.org/viewer?node_id={node_id}")
        if extra_dashboard_ids:
            lines.append(
                f"  Extra dashboard {item_type} IDs: {len(extra_dashboard_ids)}"
            )
            for node_id in extra_dashboard_ids:
                lines.append(f"    - https://api.kernelci.org/viewer?node_id={node_id}")
        if status_mismatch_ids:
            lines.append(
                f"  Status mismatch {item_type} IDs: {len(status_mismatch_ids)}"
            )
            for node_id in status_mismatch_ids:
                lines.append(f"    - https://api.kernelci.org/viewer?node_id={node_id}")

    return "\n".join(lines)


def print_validation_human(report, err=False):
    """Print a human-readable validation report."""
    click.echo(validation_report_to_text(report), err=err)


def print_validation_json(kind, rows, history, origin, days, arch):
    """Print a single JSON validation report to stdout."""
    report = validation_rows_to_json(kind, rows, history, origin, days, arch)
    click.echo(json.dumps(report))
    return report


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


def get_boots(ctx, giturl, branch, commit, arch, raise_errors=False):
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
        if raise_errors:
            raise
        kci_msg_red(f"{branch}/{commit}: Aborted while fetching dashboard boots")
        return maestro_boots, None
    except click.ClickException as e:
        if "No boots available" in e.message:
            return maestro_boots, []
        if raise_errors:
            raise
        kci_msg_red(f"{branch}/{commit}: {e.message}")
        return maestro_boots, None
    return maestro_boots, dashboard_boots


def get_boot_stats(
    ctx, giturl, branch, commit, tree_name, verbose, arch, raise_errors=False
):
    """Get boot stats"""
    maestro_boots, dashboard_boots = get_boots(
        ctx, giturl, branch, commit, arch, raise_errors
    )
    if dashboard_boots is None:
        return []
    maestro_boots = filter_maestro_items_for_validation(maestro_boots, "boot")
    summary_flag = "✅"
    missing_boot_ids = find_missing_items(
        maestro_boots, dashboard_boots, "boot", verbose
    )
    extra_dashboard_boot_ids = find_extra_dashboard_items(
        maestro_boots, dashboard_boots, "boot", verbose
    )
    boots_with_status_mismatch = validate_boot_status(maestro_boots, dashboard_boots)
    if (
        len(dashboard_boots) != len(maestro_boots)
        or missing_boot_ids
        or extra_dashboard_boot_ids
        or boots_with_status_mismatch
    ):
        summary_flag = "❌"
    stats = [
        f"{tree_name}/{branch}",
        commit,
        len(maestro_boots),
        len(dashboard_boots),
        summary_flag,
        missing_boot_ids,
        boots_with_status_mismatch,
        extra_dashboard_boot_ids,
    ]
    return stats


def get_builds_history_stats(
    ctx, giturl, branch, tree_name, arch, days, verbose, raise_errors=False
):
    checkouts = get_checkouts(ctx, giturl, branch, days)
    final_stats = []
    builds_history = get_builds_history(ctx, checkouts, arch, raise_errors)
    for b in builds_history:
        maestro_builds = filter_maestro_items_for_validation(b[1], "build")
        missing_build_ids = find_missing_items(maestro_builds, b[2], "build", verbose)
        extra_dashboard_build_ids = find_extra_dashboard_items(
            maestro_builds, b[2], "build", verbose
        )
        total_maestro_builds = len(maestro_builds)
        total_dashboard_builds = len(b[2])
        mismatched_ids = validate_build_status(maestro_builds, b[2])
        summary_flag = (
            "✅"
            if total_maestro_builds == total_dashboard_builds
            and not missing_build_ids
            and not extra_dashboard_build_ids
            and not mismatched_ids
            else "❌"
        )
        stats = [
            f"{tree_name}/{branch}",
            b[0],
            total_maestro_builds,
            total_dashboard_builds,
            summary_flag,
            missing_build_ids,
            mismatched_ids,
            extra_dashboard_build_ids,
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
        nodes=True,
        filter=filters,
        paginate=False,
        verbose=False,
    )
    return checkouts


def get_builds_history(ctx, checkouts, arch, raise_errors=False):
    """Get builds from maestro and dashboard for provided checkouts"""
    builds_history = []
    for c in checkouts:
        commit = c["data"]["kernel_revision"].get("commit")
        filters = [
            "kind=kbuild",
            "data.error_code__ne=node_timeout",
            "parent=" + c["id"],
            "state__ne=running",
        ]
        if arch:
            filters.append(f"data.arch={arch}")
        maestro_builds = ctx.invoke(
            results,
            nodes=True,
            filter=filters,
            paginate=False,
            verbose=False,
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
            if raise_errors:
                raise
            kci_msg_red(f"{branch}/{commit}: Aborted while fetching dashboard builds")
        except click.ClickException as e:
            if "No builds available" in e.message:
                builds_history.append([commit, maestro_builds, []])
                continue
            if raise_errors:
                raise
            kci_msg_red(f"{branch}/{commit}: {e.message}")
    return builds_history
