#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import click
from git import Repo


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


@click.command(
    help="""Test local commits from a kernel repository.

This command allows you to test local kernel commits that haven't been pushed
to a remote repository. It extracts the diff between your local branch and the
origin branch, then submits it for testing in KernelCI.

Note: This command is not implemented. Use ``kci-dev patchset`` to submit
local changes for testing.

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
    raise click.ClickException(
        "The commit command is not implemented; use 'kci-dev patchset' instead."
    )


if __name__ == "__main__":
    main_kcidev()
