#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import click
import requests
from git import Repo

from kcidev.libs.maestro_common import *


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
    maestro_print_api_call(url, values)
    response = requests.post(url, headers=headers, files={"patch": patch}, data=values)
    click.secho(response.status_code, fg="green")
    click.secho(response.json(), fg="green")


@click.command(
    help="""Test a kernel patch or mbox file against a specific tree/branch.

This command allows you to submit a patch file for testing in KernelCI. The
patch will be applied on top of the specified repository and branch, then
built and tested. Both standard patch files and mbox files (from git
format-patch or email) are supported.

\b
Examples:
  # Test a patch against mainline master
  kci-dev patch --patch my-fix.patch

  # Test a patch against a specific tree and branch
  kci-dev patch --patch feature.patch --repository next --branch linux-next/master

  # Test a patch privately (results not published)
  kci-dev patch --patch bug-fix.mbox --private

  # Test an email patch from git format-patch
  kci-dev patch --patch 0001-fix-memory-leak.patch
"""
)
@click.option(
    "--repository",
    default="mainline",
    help="Upstream kernel repository name to apply patch on (default: mainline)",
)
@click.option(
    "--branch", default="master", help="Branch to apply patch on (default: master)"
)
@click.option(
    "--private",
    default=False,
    is_flag=True,
    help="Keep test results private (not published publicly)",
)
@click.option(
    "--patch",
    required=True,
    help="Path to patch or mbox file to test",
    type=click.Path(exists=True, readable=True),
)
@click.pass_context
def patch(ctx, repository, branch, private, patch):
    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = config[instance]["pipeline"]
    patch = open(patch, "rb")
    send_build(url, patch, branch, repository, config[instance]["token"])


if __name__ == "__main__":
    main_kcidev()
