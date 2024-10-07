#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import subprocess

import click
import requests
from git import Repo
from libs.common import *


def api_connection(host):
    click.secho("api connect: " + host, fg="green")
    return host


def display_api_error(response):
    click.secho(f"API response error code: {response.status_code}", fg="red")
    try:
        click.secho(response.json(), fg="red")
    except json.decoder.JSONDecodeError:
        click.secho(f"No JSON response. Plain text: {response.text}", fg="yellow")
    return


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
        "jobfilter": kwargs["jobfilter"],
    }
    jdata = json.dumps(data)
    try:
        response = requests.post(url, headers=headers, data=jdata)
    except requests.exceptions.RequestException as e:
        click.secho(f"API connection error: {e}", fg="red")
        return

    if response.status_code != 200:
        display_api_error(response)
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


@click.command(help="Create custom tree checkout on KernelCI and trigger a tests")
@click.option(
    "--giturl",
    help="Git URL to checkout",
    required=True,
)
@click.option(
    "--branch",
    help="Branch to checkout",
    required=True,
)
@click.option(
    "--commit",
    help="Commit to checkout",
)
@click.option(
    "--tipoftree",
    help="Checkout on latest commit on tree/branch",
    is_flag=True,
)
# jobfilter is a list, might be one or more jobs
@click.option(
    "--jobfilter",
    help="Job filter to trigger",
    multiple=True,
)
@click.pass_context
def checkout(ctx, giturl, branch, commit, jobfilter, tipoftree):
    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = api_connection(cfg[instance]["host"])
    token = cfg[instance]["token"]
    if not jobfilter:
        jobfilter = None
        click.secho("No job filter defined. All jobs will be triggered!", fg="yellow")
    if not commit and not tipoftree:
        click.secho("No commit or tree/branch latest commit defined", fg="red")
        return
    if tipoftree:
        click.secho(
            f"Retrieving latest commit on tree: {giturl} branch: {branch}", fg="green"
        )
        commit = retrieve_tot_commit(giturl, branch)
        click.secho(f"Commit to checkout: {commit}", fg="green")
    resp = send_checkout_full(
        url, token, giturl=giturl, branch=branch, commit=commit, jobfilter=jobfilter
    )
    if resp and "message" in resp:
        click.secho(resp["message"], fg="green")


if __name__ == "__main__":
    main_kcidev()
