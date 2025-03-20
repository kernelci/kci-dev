#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from functools import wraps

import click
from libs.dashboard import (
    dashboard_fetch_boots,
    dashboard_fetch_build,
    dashboard_fetch_builds,
    dashboard_fetch_summary,
    dashboard_fetch_test,
    dashboard_fetch_tests,
)
from libs.git_repo import set_giturl_branch_commit
from subcommands.results.parser import (
    cmd_builds,
    cmd_list_trees,
    cmd_single_build,
    cmd_single_test,
    cmd_summary,
    cmd_tests,
)


def results_display_options(func):
    @click.option("--json", "use_json", is_flag=True, help="Displays results as json")
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def common_options(func):
    @click.option(
        "--origin",
        help="Select KCIDB origin",
        default="maestro",
    )
    @click.option(
        "--giturl",
        help="Git URL of kernel tree ",
    )
    @click.option(
        "--branch",
        help="Branch to get results for",
    )
    @click.option(
        "--git-folder",
        help="Path of git repository folder",
    )
    @click.option(
        "--commit",
        help="Commit or tag to get results for",
    )
    @click.option(
        "--latest",
        is_flag=True,
        help="Select latest results available",
    )
    @click.option("--arch", help="Filter by arch")
    @results_display_options
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def builds_and_tests_options(func):
    @click.option(
        "--download-logs",
        is_flag=True,
        help="Select desired results action",
    )
    @click.option(
        "--status",
        type=click.Choice(["all", "pass", "fail", "inconclusive"], case_sensitive=True),
        help="Status of test result",
        default="all",
    )
    @click.option(
        "--filter",
        type=click.File("r"),
        help="Pass filter file for builds, boot and tests results.",
    )
    @click.option(
        "--count", is_flag=True, help="Display the number of matching results"
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def single_build_and_test_options(func):
    @click.option(
        "--id",
        "op_id",
        required=True,
        help="Pass an id filter to get specific results",
    )
    @click.option(
        "--download-logs",
        is_flag=True,
        help="Select desired results action",
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


@click.group(help="[Experimental] Get results from the dashboard")
def results():
    """Commands related to results."""
    pass


@results.command()
@common_options
def summary(origin, git_folder, giturl, branch, commit, latest, arch, use_json):
    """Display a summary of results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_summary(origin, giturl, branch, commit, arch, use_json)
    cmd_summary(data, use_json)


@results.command()
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@results_display_options
def trees(origin, use_json):
    """List trees from a give origin."""
    cmd_list_trees(origin, use_json)


@results.command()
@common_options
@builds_and_tests_options
def builds(
    origin,
    git_folder,
    giturl,
    branch,
    commit,
    latest,
    arch,
    download_logs,
    status,
    filter,
    count,
    use_json,
):
    """Display build results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_builds(origin, giturl, branch, commit, arch, use_json)
    cmd_builds(data, commit, download_logs, status, count, use_json)


@results.command()
@common_options
@builds_and_tests_options
def boots(
    origin,
    git_folder,
    giturl,
    branch,
    commit,
    latest,
    arch,
    download_logs,
    status,
    filter,
    count,
    use_json,
):
    """Display boot results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_boots(origin, giturl, branch, commit, arch, use_json)
    cmd_tests(data["boots"], commit, download_logs, status, filter, count, use_json)


@results.command()
@common_options
@builds_and_tests_options
def tests(
    origin,
    git_folder,
    giturl,
    branch,
    commit,
    latest,
    arch,
    download_logs,
    status,
    filter,
    count,
    use_json,
):
    """Display test results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_tests(origin, giturl, branch, commit, arch, use_json)
    cmd_tests(data["tests"], commit, download_logs, status, filter, count, use_json)


@results.command()
@single_build_and_test_options
@results_display_options
def test(op_id, download_logs, use_json):
    data = dashboard_fetch_test(op_id, use_json)
    cmd_single_test(data, download_logs, use_json)


@results.command()
@single_build_and_test_options
@results_display_options
def build(op_id, download_logs, use_json):
    data = dashboard_fetch_build(op_id, use_json)
    cmd_single_build(data, download_logs, use_json)


if __name__ == "__main__":
    main_kcidev()
