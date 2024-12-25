#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gzip
import json
import urllib

import click
import requests

from kcidev.libs.common import *

DASHBOARD_API = "https://dashboard.kernelci.org/api/"


def fetch_from_api(endpoint, params):
    base_url = urllib.parse.urljoin(DASHBOARD_API, endpoint)
    try:
        url = "{}?{}".format(base_url, urllib.parse.urlencode(params))
        r = requests.get(url)
    except:
        click.secho(f"Failed to fetch from {DASHBOARD_API}.")
        raise click.Abort()

    return r.json()


def fetch_full_results(origin, giturl, branch, commit):
    endpoint = f"tree/{commit}/full"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
        "commit": commit,
    }

    return fetch_from_api(endpoint, params)


def fetch_tree_fast(origin):
    params = {
        "origin": origin,
    }
    return fetch_from_api("tree-fast", params)


def get_latest_commit(origin, giturl, branch):
    trees = fetch_tree_fast(origin)
    for t in trees:
        if t["git_repository_url"] == giturl and t["git_repository_branch"] == branch:
            return t["git_commit_hash"]

    kci_err("Tree and branch not found.")
    raise click.Abort()


def print_summary(type, n_pass, n_fail, n_inconclusive):
    kci_msg_nonl(f"{type}:\t")
    kci_msg_green_nonl(f"{n_pass}") if n_pass else kci_msg_nonl(f"{n_pass}")
    kci_msg_nonl("/")
    kci_msg_red_nonl(f"{n_fail}") if n_fail else kci_msg_nonl(f"{n_fail}")
    kci_msg_nonl("/")
    (
        kci_msg_yellow_nonl(f"{n_inconclusive}")
        if n_inconclusive
        else kci_msg_nonl(f"{n_inconclusive}")
    )
    kci_msg_nonl(f"\n")


def sum_inconclusive_results(results):
    count = 0
    for status in ["ERROR", "SKIP", "MISS", "DONE", "NULL"]:
        if status in results.keys():
            count += results[status]

    return count


def cmd_summary(data):
    kci_msg("pass/fail/inconclusive")

    builds = data["buildsSummary"]["builds"]
    print_summary("builds", builds["valid"], builds["invalid"], builds["null"])

    boots = data["bootStatusSummary"]
    inconclusive_boots = sum_inconclusive_results(boots)
    pass_boots = boots["PASS"] if "PASS" in boots.keys() else 0
    fail_boots = boots["FAIL"] if "FAIL" in boots.keys() else 0
    print_summary("boots", pass_boots, fail_boots, inconclusive_boots)

    tests = data["testStatusSummary"]
    pass_tests = tests["PASS"] if "PASS" in tests.keys() else 0
    fail_tests = tests["FAIL"] if "FAIL" in tests.keys() else 0
    inconclusive_tests = sum_inconclusive_results(tests)
    print_summary("tests", pass_tests, fail_tests, inconclusive_tests)


def cmd_list_trees(origin):
    trees = fetch_tree_fast(origin)
    for t in trees:
        kci_msg_green_nonl(f"- {t['tree_name']}/{t['git_repository_branch']}:\n")
        kci_msg(f"  giturl: {t['git_repository_url']}")
        kci_msg(f"  latest: {t['git_commit_hash']} ({t['git_commit_name']})")
        kci_msg(f"  latest: {t['start_time']}")


def cmd_builds(data, commit, download_logs, status):
    if status == "inconclusive":
        kci_msg("No information about inconclusive builds.")
        return

    for build in data["builds"]:
        if build["valid"] == None:
            continue

        if not status == "all":
            if build["valid"] == (status == "fail"):
                continue

            if not build["valid"] == (status == "pass"):
                continue

        log_path = build["log_url"]
        if download_logs:
            try:
                log_gz = requests.get(build["log_url"])
                log = gzip.decompress(log_gz.content)
                log_file = f"{build['config_name']}-{build['architecture']}-{build['compiler']}-{commit}.log"
                with open(log_file, mode="wb") as file:
                    file.write(log)
                log_path = "file://" + os.path.join(os.getcwd(), log_file)
            except:
                kci_err(f"Failed to fetch log {log_file}).")
                pass

        kci_msg_nonl("- config:")
        kci_msg_cyan_nonl(build["config_name"])
        kci_msg_nonl(" arch: ")
        kci_msg_cyan_nonl(build["architecture"])
        kci_msg_nonl(" compiler: ")
        kci_msg_cyan_nonl(build["compiler"])
        kci_msg("")

        kci_msg_nonl("  status:")
        if build["valid"]:
            kci_msg_green_nonl("PASS")
        else:
            kci_msg_red_nonl("FAIL")
        kci_msg("")

        kci_msg(f"  config_url: {build['config_url']}")
        kci_msg(f"  log: {log_path}")
        kci_msg(f"  id: {build['id']}")
        kci_msg("")


@click.command(help=" [Experimental] Get results from the dashboard")
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
    "--commit",
    help="Commit or tag to get results for",
)
@click.option(
    "--action",
    type=click.Choice(["summary", "trees", "builds"], case_sensitive=True),
    help="Select desired results action",
)
@click.option(
    "--download-logs",
    is_flag=True,
    help="Select desired results action",
)
@click.option(
    "--latest",
    is_flag=True,
    help="Select latest results available",
)
@click.option(
    "--status",
    type=click.Choice(["all", "pass", "fail", "inconclusive"], case_sensitive=True),
    help="Status of test result",
    default="all",
)
@click.pass_context
def results(ctx, origin, giturl, branch, commit, action, download_logs, latest, status):
    if action == None or action == "summary":
        if not giturl or not branch or not ((commit != None) ^ latest):
            kci_err("--giturl AND --branch AND (--commit XOR --latest) are required")
            raise click.Abort()
        if latest:
            commit = get_latest_commit(origin, giturl, branch)
        data = fetch_full_results(origin, giturl, branch, commit)
        cmd_summary(data)
    elif action == "trees":
        cmd_list_trees(origin)
    elif action == "builds":
        if not giturl or not branch or not ((commit != None) ^ latest):
            kci_err("--giturl AND --branch AND (--commit XOR --latest) are required")
            raise click.Abort()
        if latest:
            commit = get_latest_commit(origin, giturl, branch)
        data = fetch_full_results(origin, giturl, branch, commit)
        cmd_builds(data, commit, download_logs, status)
    else:
        kci_err(f"action '{action}' does not exist.")
        raise click.Abort()


if __name__ == "__main__":
    main_kcidev()
