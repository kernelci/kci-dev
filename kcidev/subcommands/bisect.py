#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import subprocess
import sys

import click
import requests
from git import Repo

from kcidev.libs.common import *

"""
To not lose the state of the bisection, we need to store the state in a file
The state file is a json file that contains the following keys:
- giturl: the repository url
- branch: the repository branch
- good: the known good commit
- bad: the known bad commit
- retryfail: the number of times to retry the failed test
- history: the list of commits that have been tested (each entry has "commitid": state)
"""
default_state = {
    "giturl": "",
    "branch": "",
    "retryfail": 0,
    "good": "",
    "bad": "",
    "history": [],
    "job_filter": [],
    "platform_filter": [],
    "test": "",
    "workdir": "",
    "bisect_init": False,
    "next_commit": None,
}


def load_state(file="state.json"):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    else:
        return None


def print_state(state):
    click.secho("Loaded state file", fg="green")
    click.secho("giturl: " + state["giturl"], fg="green")
    click.secho("branch: " + state["branch"], fg="green")
    click.secho("good: " + state["good"], fg="green")
    click.secho("bad: " + state["bad"], fg="green")
    click.secho("retryfail: " + str(state["retryfail"]), fg="green")
    click.secho("history: " + str(state["history"]), fg="green")
    click.secho("job_filter: " + str(state["job_filter"]), fg="green")
    click.secho("platform_filter: " + str(state["platform_filter"]), fg="green")
    click.secho("test: " + state["test"], fg="green")
    click.secho("workdir: " + state["workdir"], fg="green")
    click.secho("bisect_init: " + str(state["bisect_init"]), fg="green")
    click.secho("next_commit: " + str(state["next_commit"]), fg="green")


def save_state(state, file="state.json"):
    with open(file, "w") as f:
        json.dump(state, f)


def git_exec_getcommit(cmd):
    click.secho("Executing git command: " + " ".join(cmd), fg="green")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        kci_err("git command return failed. Error:")
        kci_err(result.stderr)
        kci_err(result.stdout)
        sys.exit(1)
    lines = result.stdout.split(b"\n")
    if len(lines) < 2:
        kci_err(f"git command answer length failed: {lines}")
        sys.exit(1)
    # is it last bisect?: "is the first bad commit"
    if "is the first bad commit" in str(lines[1]):
        click.secho(f"git command: {lines}", fg="green")
        # TBD save state somehow?
        sys.exit(0)
    re_commit = re.search(r"\[([a-f0-9]+)\]", str(lines[1]))
    if not re_commit:
        kci_err(f"git command regex failed: {lines}")
        sys.exit(1)
    return re_commit.group(1)


def kcidev_exec(cmd):
    """
    Execute a kci-dev and return the return code
    """
    process = None
    click.secho("Executing kci-dev command: " + " " + str(cmd), fg="green")
    with subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as process:
        try:
            for line in process.stdout:
                click.echo(line, nl=False)
            process.wait()
        except Exception as e:
            kci_err(f"Error executing kci-dev: {e}")
            sys.exit(1)

    return process


def init_bisect(state):
    olddir = os.getcwd()
    os.chdir(state["workdir"])
    click.secho("init bisect", fg="green")
    r = os.system("git bisect start")
    if r != 0:
        kci_err("git bisect start failed")
        sys.exit(1)
    r = os.system("git bisect good " + state["good"])
    if r != 0:
        kci_err("git bisect good failed")
        sys.exit(1)
    # result = subprocess.run(['ls', '-l'], stdout=subprocess.PIPE)
    cmd = ["git", "bisect", "bad", state["bad"]]
    commitid = git_exec_getcommit(cmd)
    os.chdir(olddir)
    return commitid


def update_tree(workdir, branch, giturl):
    if not os.path.exists(workdir):
        click.secho(
            "Cloning repository (this might take significant time!)", fg="green"
        )
        repo = Repo.clone_from(giturl, workdir)
        repo.git.checkout(branch)
    else:
        click.secho("Pulling repository", fg="green")
        repo = Repo(workdir)
        repo.git.checkout(branch)
        repo.git.pull()


def bisection_loop(state):
    olddir = os.getcwd()
    os.chdir(state["workdir"])
    commit = state["next_commit"]
    if commit is None:
        click.secho("Bisection error?", fg="green")
        return
    click.secho("Testing commit: " + commit, fg="green")
    cmd = [
        "kci-dev",
        "checkout",
        "--giturl",
        state["giturl"],
        "--branch",
        state["branch"],
        "--test",
        state["test"],
        "--commit",
        commit,
        "--watch",
    ]
    # job_filter is array, so we need to add each element as a separate argument
    for job in state["job_filter"]:
        cmd.append("--job_filter")
        cmd.append(job)
    for platform in state["platform_filter"]:
        cmd.append("--platform_filter")
        cmd.append(platform)
    result = kcidev_exec(cmd)
    try:
        testret = result.returncode
    except Exception as e:
        kci_err(f"Error executing kci-dev, no returncode: {e}")
        sys.exit
    if testret == 0:
        bisect_result = "good"
    elif testret == 1:
        # TBD: Retry failed test to make sure it is not a flaky test
        bisect_result = "bad"
    elif testret == 2:
        # TBD: Retry failed test to make sure it is not a flaky test
        bisect_result = "skip"
    else:
        kci_err("Maestro failed to execute the test")
        # Internal maestro error, retry procesure
        return None
    cmd = ["git", "bisect", bisect_result]
    commitid = git_exec_getcommit(cmd)
    if not commitid:
        kci_err("git bisect failed, commit return is empty")
        sys.exit(1)
    state["history"].append({commit: bisect_result})
    state["next_commit"] = commitid
    os.chdir(olddir)
    return state


@click.command(help="Bisect Linux Kernel regression")
@click.option("--giturl", help="define the repository url")
@click.option("--branch", help="define the repository branch")
@click.option("--good", help="known good commit")
@click.option("--bad", help="known bad commit")
@click.option("--retryfail", help="retry failed test N times", default=2)
@click.option("--workdir", help="define the repository origin", default="kcidev-src")
@click.option("--ignorestate", help="ignore save state", is_flag=True)
@click.option("--statefile", help="state file", default="state.json")
@click.option("--job-filter", help="filter the job", multiple=True)
@click.option("--platform-filter", help="filter the platform", multiple=True)
@click.option("--test", help="Test expected to fail")

# test
@click.pass_context
def bisect(
    ctx,
    giturl,
    branch,
    good,
    bad,
    retryfail,
    workdir,
    ignorestate,
    statefile,
    job_filter,
    platform_filter,
    test,
):
    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")

    state_file = os.path.join(workdir, statefile)
    state = load_state(state_file)
    if state is None or ignorestate:
        state = default_state
        if not giturl:
            kci_err("--giturl is required")
            return
        if not branch:
            kci_err("--branch is required")
            return
        if not good:
            kci_err("--good is required")
            return
        if not bad:
            kci_err("--bad is required")
            return
        if not job_filter:
            kci_err("--job-filter is required")
            return
        if not platform_filter:
            kci_err("--platform-filter is required")
            return
        if not test:
            kci_err("--test is required")
            return

        state["giturl"] = giturl
        state["branch"] = branch
        state["good"] = good
        state["bad"] = bad
        state["retryfail"] = retryfail
        state["job_filter"] = job_filter
        state["platform_filter"] = platform_filter
        state["test"] = test
        state["workdir"] = workdir
        update_tree(workdir, branch, giturl)
        save_state(state, state_file)
    else:
        print_state(state)
        update_tree(workdir, branch, giturl)

    if not state["bisect_init"]:
        state["next_commit"] = init_bisect(state)
        state["bisect_init"] = True
        save_state(state, state_file)

    while True:
        click.secho("Bisection loop", fg="green")
        new_state = bisection_loop(state)
        if new_state is None:
            click.secho("Retry failed test", fg="green")
            continue
        state = new_state
        save_state(state, state_file)


if __name__ == "__main__":
    main_kcidev()
