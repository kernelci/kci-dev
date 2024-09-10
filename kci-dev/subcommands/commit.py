#!/usr/bin/env python
# -*- coding: utf-8 -*-

import click
import toml
import requests
import json
import sys
from git import Repo


def api_connection(host):
    click.secho("api connect: " + host, fg="green")
    return host


def find_diff(path, branch, repository):
    repo = Repo(path)
    assert not repo.bare
    for ref in repo.references:
        if ref.name != branch:
            print("Branch name: " + ref.name)
            sys.exit(0)
    hcommit = repo.iter_commits("origin/master.." + branch)
    commits = []
    for i in hcommit:
        commits.append(repo.git.show(i))
    return commits


def send_build(url, patch, branch, treeurl, commit, token):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": "Bearer {}".format(token),
    }
    values = {
        "treeurl": treeurl,
        "branch": branch,
        "commit": commit,
        "kbuildname": "example",
        "testname": "example",
    }
    response = requests.post(url, headers=headers, files={"patch": patch}, data=values)
    click.secho(response.status_code, fg="green")
    click.secho(response.json(), fg="green")


def load_toml(settings):
    with open(settings) as fp:
        config = toml.load(fp)
    return config


@click.command(help="Test commits from a local Kernel repository")
@click.option(
    "--repository",
    default="mainline",
    help="define the kernel upstream repository where to test local changes",
)
@click.option("--branch", default="master", help="define the repository branch")
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
@click.option("--settings", default=".kci-dev.toml", help="path of toml setting file")
def commit(repository, branch, private, path, settings):
    config = load_toml(settings)
    url = api_connection(config["connection"]["host"])
    diff = find_diff(path, branch, repository)
    send_build(
        url,
        diff,
        branch,
        repository,
        "commit id example",
        config["connection"]["token"],
    )


if __name__ == "__main__":
    main_kcidev()
