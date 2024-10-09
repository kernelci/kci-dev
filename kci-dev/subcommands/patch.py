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
    response = requests.post(url, headers=headers, files={"patch": patch}, data=values)
    click.secho(response.status_code, fg="green")
    click.secho(response.json(), fg="green")


@click.command(help="Test a patch or a mbox file")
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
@click.option("--patch", required=True, help="mbox or patch file path")
@click.pass_context
def patch(ctx, repository, branch, private, patch):
    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = api_connection(config[instance]["pipeline"])
    patch = open(patch, "rb")
    send_build(url, patch, branch, repository, config[instance]["token"])


if __name__ == "__main__":
    main_kcidev()
