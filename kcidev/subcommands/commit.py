#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys

import click
import requests
from git import Repo


def api_connection(host):
    click.secho("api connect: " + host, fg="green")
    return host


def find_diff(path, branch, origin, repository):
    repo = Repo(path)
    assert not repo.bare
    hcommit = repo.iter_commits(origin + ".." + branch)
    commits = []
    for i in hcommit:
        commits.append(repo.git.show(i))
    return commits[0]


def send_build(url, patch, branch, treeurl, token):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": "Bearer {}".format(token),
    }
    values = {
        "treeurl": treeurl,
        "branch": branch,
        "commit": "example",
        "kbuildname": "example",
        "testname": "example",
    }
    # temporary disabled as API not working yet
    click.secho(url, fg="green")
    click.secho(headers, fg="green")
    click.secho(values, fg="green")
    # response = requests.post(url, headers=headers, files={"patch": patch}, data=values)
    # click.secho(response.status_code, fg="green")
    # click.secho(response.json(), fg="green")


@click.command(
    help="""Test local commits from a kernel repository.

This command allows you to test local kernel commits that haven't been pushed
to a remote repository. It extracts the diff between your local branch and the
origin branch, then submits it for testing in KernelCI.

Note: This command is currently experimental and the API integration is not
fully operational.

\b
Examples:
  # Test local commits on top of mainline master
  kci-dev commit --path /path/to/kernel --branch my-feature

  # Test commits from a different upstream repository
  kci-dev commit --repository next --branch my-feature --origin linux-next/master

  # Test commits privately (results not published)
  kci-dev commit --private --path /path/to/kernel
"""
)
@click.option(
    "--repository",
    default="mainline",
    help="Upstream kernel repository name (default: mainline)",
)
@click.option(
    "--branch",
    default="master",
    help="Local branch name with your commits (default: master)",
)
@click.option(
    "--origin",
    default="master",
    help="Origin branch to compare against (default: master)",
)
@click.option(
    "--private",
    default=False,
    is_flag=True,
    help="Keep test results private (not published publicly)",
)
@click.option(
    "--path",
    default=".",
    help="Path to local kernel repository (default: current directory)",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.pass_context
def commit(ctx, repository, branch, origin, private, path):
    # Check if user provided no custom options (all defaults)
    # Show help if running with all defaults and no explicit path
    if (
        repository == "mainline"
        and branch == "master"
        and origin == "master"
        and not private
        and path == "."
        and not ctx.parent.params.get("help")
    ):
        # Check if running in a git repo
        try:
            Repo(".")
        except:
            # Not in a git repo, show help
            ctx = click.get_current_context()
            click.echo(ctx.get_help())
            sys.exit(0)

    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = api_connection(config[instance]["pipeline"])
    diff = find_diff(path, branch, origin, repository)
    send_build(url, diff, branch, repository, config[instance]["token"])


if __name__ == "__main__":
    main_kcidev()
