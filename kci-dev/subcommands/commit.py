#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import click
import requests
import toml
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


@click.command(help="Test commits from a local Kernel repository")
@click.option(
    "--repository",
    default="mainline",
    help="define the kernel upstream repository where to test local changes",
)
@click.option("--branch", default="master", help="define the repository branch")
@click.option("--origin", default="master", help="define the origin repository branch")
@click.option(
    "--private",
    default=False,
    is_flag=True,
    help="define if the test results will be published",
)
@click.option(
    "--path",
    default=".",
    help="define the directory of the local tree with local changes",
)
@click.pass_context
def commit(ctx, repository, branch, origin, private, path):
    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = api_connection(config[instance]["pipeline"])
    diff = find_diff(path, branch, origin, repository)
    send_build(url, diff, branch, repository, config[instance]["token"])


if __name__ == "__main__":
    main_kcidev()
