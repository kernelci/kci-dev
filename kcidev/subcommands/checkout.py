#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import json
import re
import subprocess
import sys
import time

import click
import requests
from git import Repo

from kcidev.libs.common import *
from kcidev.libs.maestro_common import *


def send_checkout_full(baseurl, token, **kwargs):
    url = baseurl + "api/checkout"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"{token}",
    }
    data = {
        "url": kwargs["giturl"],
        "branch": kwargs["branch"],
        "commit": kwargs["commit"],
        "jobfilter": kwargs["job_filter"],
    }
    if "platform_filter" in kwargs:
        data["platformfilter"] = kwargs["platform_filter"]
    jdata = json.dumps(data)
    maestro_print_api_call(url, data)
    try:
        response = requests.post(url, headers=headers, data=jdata, timeout=30)
    except requests.exceptions.RequestException as e:
        kci_err(f"API connection error: {e}")
        return None

    if response.status_code != 200:
        maestro_api_error(response)
        return None
    return response.json()


def retrieve_tot_commit(repourl, branch):
    """
    Retrieve the latest commit on a branch

    Unfortunately, gitpython does not support fetching the latest commit
    on a branch without having to clone the repo.
    """
    process = subprocess.Popen(
        ["git", "ls-remote", repourl, f"refs/heads/{branch}"], stdout=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    sha = re.split(r"\t+", stdout.decode("ascii"))[0]
    return sha


@click.command(
    help="""Trigger test runs for a specific kernel tree/branch/commit.

This command submits a kernel checkout request to KernelCI's pipeline system,
which will build and test the specified kernel version. You can filter which
jobs and platforms to run, and optionally watch the results in real-time.

Either --commit or --tipoftree must be specified to identify which kernel
version to test.

\b
Examples:
  # Test a specific commit
  kci-dev checkout --giturl https://git.kernel.org/torvalds/linux.git \\
                   --branch master --commit abc123def456

  # Test the latest commit on a branch
  kci-dev checkout --giturl https://git.kernel.org/torvalds/linux.git \\
                   --branch master --tipoftree

  # Test with job and platform filters, and watch results
  kci-dev checkout --giturl https://git.kernel.org/torvalds/linux.git \\
                   --branch master --tipoftree \\
                   --job-filter baseline --platform-filter qemu-x86 \\
                   --watch

  # Watch for a specific test result and return appropriate exit code
  kci-dev checkout --giturl ... --branch ... --commit ... \\
                   --job-filter baseline --watch --test baseline.login
"""
)
@click.option(
    "--giturl",
    help="Git repository URL containing the kernel source",
    required=True,
)
@click.option(
    "--branch",
    help="Git branch to checkout and test",
    required=True,
)
@click.option(
    "--commit",
    help="Specific commit SHA to checkout (40 characters)",
)
@click.option(
    "--tipoftree",
    help="Use the latest commit on the specified tree/branch",
    is_flag=True,
)
@click.option(
    "--watch",
    "-w",
    help="Watch and display test results interactively as they complete",
    is_flag=True,
)
# job_filter is a list, might be one or more jobs
@click.option(
    "--job-filter",
    help="Filter tests by job name (e.g., baseline, ltp). Can be used multiple times",
    multiple=True,
)
@click.option(
    "--platform-filter",
    help="Filter tests by platform (e.g., qemu-x86, rpi4). Can be used multiple times",
    multiple=True,
)
@click.option(
    "--test",
    help="Watch for specific test result and set exit code accordingly (requires --watch)",
)
@click.pass_context
def checkout(
    ctx, giturl, branch, commit, job_filter, platform_filter, tipoftree, watch, test
):
    # Check if no parameters provided - show help
    if not any(
        [giturl, branch, commit, job_filter, platform_filter, tipoftree, watch, test]
    ):
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        sys.exit(0)

    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = cfg[instance]["pipeline"]
    apiurl = cfg[instance]["api"]
    token = cfg[instance]["token"]
    if not job_filter:
        job_filter = None
        click.secho("No job filter defined. All jobs will be triggered!", fg="yellow")
    if watch and not job_filter:
        kci_err("No job filter defined. Can't watch for a job(s)!")
        return
    if test and not watch:
        kci_err("Test option only works with watch option")
        return
    if not commit and not tipoftree:
        kci_err("No commit or tree/branch latest commit defined")
        return
    if tipoftree:
        click.secho(
            f"Retrieving latest commit on tree: {giturl} branch: {branch}", fg="green"
        )
        commit = retrieve_tot_commit(giturl, branch)
        if not commit or len(commit) != 40:
            kci_err("Unable to retrieve latest commit. Wrong tree/branch?")
            return
        click.secho(f"Commit to checkout: {commit}", fg="green")
    resp = send_checkout_full(
        url,
        token,
        giturl=giturl,
        branch=branch,
        commit=commit,
        job_filter=job_filter,
        platform_filter=platform_filter,
        watch=watch,
    )
    if not resp:
        kci_err("Failed to trigger checkout")
        sys.exit(64)

    if resp and "message" in resp:
        click.secho(resp["message"], fg="green")

    if resp and "node" in resp:
        node = resp.get("node")
        treeid = node.get("treeid")
        checkout_nodeid = node.get("id")

        if treeid:
            click.secho(f"treeid: {treeid}", fg="green")
        if checkout_nodeid:
            click.secho(f"checkout_nodeid: {checkout_nodeid}", fg="green")

    if watch and isinstance(resp, dict):
        node = resp.get("node")
        treeid = node.get("treeid")
        if not treeid:
            kci_err("No treeid returned. Can't watch for a job(s)!")
            return
        click.secho(f"Watching for jobs on treeid: {treeid}", fg="green")
        if test:
            click.secho(f"Watching for test result: {test}", fg="green")
        # watch for jobs
        maestro_watch_jobs(apiurl, token, treeid, job_filter, test)


if __name__ == "__main__":
    main_kcidev()
