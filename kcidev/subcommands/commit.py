#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import sys

import click
import requests
from git import Repo


def api_connection(host):
    logging.info(f"Connecting to API at: {host}")
    click.secho("api connect: " + host, fg="green")
    return host


def find_diff(path, branch, origin, repository):
    logging.info(f"Finding diff between {origin} and {branch} in {path}")
    repo = Repo(path)
    assert not repo.bare

    commit_range = f"{origin}..{branch}"
    logging.debug(f"Checking commits in range: {commit_range}")

    hcommit = repo.iter_commits(commit_range)
    commits = []
    for i in hcommit:
        commits.append(repo.git.show(i))

    logging.info(f"Found {len(commits)} commits to test")
    if commits:
        logging.debug(f"First commit size: {len(commits[0])} bytes")
    return commits[0] if commits else None


def send_build(url, patch, branch, treeurl, token):
    logging.info(f"Preparing to send build for branch {branch} to {url}")
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

    logging.debug(f"Request headers: {headers}")
    logging.debug(f"Request values: {values}")

    # temporary disabled as API not working yet
    logging.warning("API integration is currently disabled - request not sent")
    click.secho(url, fg="green")
    click.secho(headers, fg="green")
    click.secho(values, fg="green")
    # response = requests.post(url, headers=headers, files={"patch": patch}, data=values)
    # logging.info(f"Response status: {response.status_code}")
    # logging.debug(f"Response: {response.json()}")
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
    logging.info("Starting commit command")
    logging.debug(
        f"Parameters - repository: {repository}, branch: {branch}, origin: {origin}"
    )
    logging.debug(f"Options - private: {private}, path: {path}")

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
            logging.debug("Running in git repository with default parameters")
        except:
            # Not in a git repo, show help
            logging.debug("Not in a git repository, showing help")
            ctx = click.get_current_context()
            click.echo(ctx.get_help())
            sys.exit(0)

    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    logging.debug(f"Using instance: {instance}")

    url = api_connection(config[instance]["pipeline"])
    diff = find_diff(path, branch, origin, repository)

    if diff:
        logging.info("Sending build with local commits")
        send_build(url, diff, branch, repository, config[instance]["token"])
    else:
        logging.warning("No commits found to test")
        click.secho(
            "No commits found between {} and {}".format(origin, branch), fg="yellow"
        )


if __name__ == "__main__":
    main_kcidev()
