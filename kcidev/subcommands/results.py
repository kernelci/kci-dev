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
    kci_print("pass/fail/inconclusive")

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


def cmd_failed_builds(data, download_logs):
    kci_print("Failed builds:")
    for build in data["builds"]:
        if not build["valid"]:
            log_path = build["log_url"]
            if download_logs:
                try:
                    log_gz = requests.get(build["log_url"])
                    log = gzip.decompress(log_gz.content)
                    log_file = f"{build['config_name']}-{build['architecture']}-{build['compiler']}.log"
                    with open(log_file, mode="wb") as file:
                        file.write(log)
                    log_path = os.path.join(os.getcwd(), log_file)
                except:
                    kci_err(f"Failed to fetch log {log_file}).")
                    pass

            kci_print(
                f"- config: {build['config_name']}; arch: {build['architecture']}"
            )
            kci_print(f"  compiler: {build['compiler']}")
            kci_print(f"  config_url: {build['config_url']}")
            kci_print(f"  log: {log_path}")
            kci_print(f"  id: {build['id']}")


def fetch_full_results(origin, giturl, branch, commit):
    endpoint = f"tree/{commit}/full"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
        "commit": commit,
    }

    return fetch_from_api(endpoint, params)


@click.command(help=" [Experimental] Get results from the dashboard")
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@click.option(
    "--giturl",
    help="Git URL of kernel tree ",
    required=True,
)
@click.option(
    "--branch",
    help="Branch to get results for",
    required=True,
)
@click.option(
    "--commit",
    help="Commit or tag to get results for",
    required=True,
)
@click.option(
    "--action",
    help="Select desired results action",
)
@click.option(
    "--download-logs",
    is_flag=True,
    help="Select desired results action",
)
@click.pass_context
def results(ctx, origin, giturl, branch, commit, action, download_logs):
    data = fetch_full_results(origin, giturl, branch, commit)
    if action == None or action == "summary":
        cmd_summary(data)
    elif action == "failed-builds":
        cmd_failed_builds(data, download_logs)


if __name__ == "__main__":
    main_kcidev()
