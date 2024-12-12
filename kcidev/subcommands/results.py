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
        r = requests.get(base_url, params=params)
    except:
        click.secho(f"Failed to fetch from {DASHBOARD_API}.")
        raise click.Abort()

    return r.json()


def cmd_summary(data):
    kci_print(f"Builds: {data['buildsSummary']['builds']}")
    kci_print(f"Boots: {data['bootStatusSummary']}")
    kci_print(f"Tests: {data['testStatusSummary']}")


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


def process_action(action, data, download_logs):
    if action == None or action == "summary":
        cmd_summary(data)
    elif action == "failed-builds":
        cmd_failed_builds(data, download_logs)


def fetch_full_results(origin, giturl, branch, commit):
    endpoint = f"tree/{commit}/full"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
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
    process_action(action, data, download_logs)


if __name__ == "__main__":
    main_kcidev()
