#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
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
- retry_fail: the number of times to retry the failed test
- history: the list of commits that have been tested (each entry has "commitid": state)
"""
default_state = {
    "giturl": "",
    "branch": "",
    "retry_fail": 0,
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
    logging.debug(f"Loading bisection state from {file}")
    if os.path.exists(file):
        with open(file, "r") as f:
            state = json.load(f)
            logging.info(f"Loaded bisection state from {file}")
            return state
    else:
        logging.debug(f"No state file found at {file}")
        return None


def print_state(state):
    click.secho("Loaded state file", fg="green")
    click.secho("giturl: " + state["giturl"], fg="green")
    click.secho("branch: " + state["branch"], fg="green")
    click.secho("good: " + state["good"], fg="green")
    click.secho("bad: " + state["bad"], fg="green")
    click.secho("retry_fail: " + str(state["retry_fail"]), fg="green")
    click.secho("history: " + str(state["history"]), fg="green")
    click.secho("job_filter: " + str(state["job_filter"]), fg="green")
    click.secho("platform_filter: " + str(state["platform_filter"]), fg="green")
    click.secho("test: " + state["test"], fg="green")
    click.secho("workdir: " + state["workdir"], fg="green")
    click.secho("bisect_init: " + str(state["bisect_init"]), fg="green")
    click.secho("next_commit: " + str(state["next_commit"]), fg="green")


def save_state(state, file="state.json"):
    logging.debug(f"Saving bisection state to {file}")
    with open(file, "w") as f:
        json.dump(state, f)
    logging.info(f"Bisection state saved to {file}")


def git_exec_getcommit(cmd):
    click.secho("Executing git command: " + " ".join(cmd), fg="green")
    logging.info(f"Executing git bisect command: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        logging.error(f"Git command failed with return code {result.returncode}")
        logging.error(f"stderr: {result.stderr}")
        logging.error(f"stdout: {result.stdout}")
        kci_err("git command return failed. Error:")
        kci_err(result.stderr)
        kci_err(result.stdout)
        sys.exit(1)
    lines = result.stdout.split(b"\n")
    logging.debug(f"Git output lines: {len(lines)}")
    if len(lines) < 2:
        logging.error(f"Unexpected git output: {lines}")
        kci_err(f"git command answer length failed: {lines}")
        sys.exit(1)
    # is it last bisect?: "is the first bad commit"
    if "is the first bad commit" in str(lines[1]):
        logging.info("Bisection complete - found first bad commit")
        click.secho(f"git command: {lines}", fg="green")
        # TBD save state somehow?
        sys.exit(0)
    re_commit = re.search(r"\[([a-f0-9]+)\]", str(lines[1]))
    if not re_commit:
        logging.error(f"Could not parse commit from git output: {lines}")
        kci_err(f"git command regex failed: {lines}")
        sys.exit(1)
    commit = re_commit.group(1)
    logging.info(f"Next commit to test: {commit}")
    return commit


def kcidev_exec(cmd):
    """
    Execute a kci-dev and return the return code
    """
    process = None
    click.secho("Executing kci-dev command: " + " " + str(cmd), fg="green")
    logging.info(f"Executing kci-dev command: {' '.join(cmd)}")
    with subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as process:
        try:
            for line in process.stdout:
                click.echo(line, nl=False)
            process.wait()
            logging.debug(
                f"kci-dev command completed with return code: {process.returncode}"
            )
        except Exception as e:
            logging.error(f"Error executing kci-dev: {e}")
            kci_err(f"Error executing kci-dev: {e}")
            sys.exit(1)

    return process


def execute_cmdline(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    try:
        return subprocess.run(cmd, stdout=stdout, stderr=stderr)
    except subprocess.CalledProcessError as e:
        kci_err(f"cmdline failed with exit code {e.returncode}")
        click.Abort()


def init_bisect(repo, state):
    olddir = os.getcwd()
    os.chdir(state["workdir"])
    click.secho("Initiating bisection...", fg="green")
    logging.info(f"Initializing bisection - good: {state['good']}, bad: {state['bad']}")

    execute_cmdline(["git", "bisect", "start"], subprocess.DEVNULL)
    execute_cmdline(["git", "bisect", "good", state["good"]], subprocess.DEVNULL)
    execute_cmdline(["git", "bisect", "bad", state["bad"]], subprocess.DEVNULL)

    results = execute_cmdline(["git", "bisect", "log"])
    if results.stdout:
        logging.debug("Git bisect log:")
        logging.debug(
            results.stdout.decode()
            if isinstance(results.stdout, bytes)
            else results.stdout
        )
        kci_log("---")
        kci_log(results.stdout)

    commit_sha = repo.head.commit.hexsha
    logging.info(f"Starting bisection at commit: {commit_sha}")
    os.chdir(olddir)
    return commit_sha


def update_tree(workdir, branch, giturl):
    if not os.path.exists(workdir):
        click.secho(
            "Cloning repository (this might take significant time!)...", fg="green"
        )
        logging.info(f"Cloning repository {giturl} to {workdir}")
        repo = Repo.clone_from(giturl, workdir)
        repo.git.checkout(branch)
        logging.info(f"Cloned and checked out branch {branch}")
    else:
        click.secho("Pulling repository...", fg="green")
        logging.info(f"Updating existing repository in {workdir}")
        repo = Repo(workdir)
        repo.git.fetch("origin", branch)
        repo.git.reset("--hard", f"origin/{branch}")
        logging.info(f"Updated to latest {branch} branch")
    return repo


def bisection_loop(state):
    olddir = os.getcwd()
    os.chdir(state["workdir"])
    commit = state["next_commit"]
    if commit is None:
        logging.error(
            "No next commit to test - bisection may be complete or in error state"
        )
        click.secho("Bisection error?", fg="green")
        return
    click.secho("Testing commit: " + commit, fg="green")
    logging.info(f"Testing commit {commit} for regression")
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
        cmd.append("--job-filter")
        cmd.append(job)
    for platform in state["platform_filter"]:
        cmd.append("--platform-filter")
        cmd.append(platform)
    result = kcidev_exec(cmd)
    try:
        testret = result.returncode
    except Exception as e:
        logging.error(f"Error getting return code from kci-dev: {e}")
        kci_err(f"Error executing kci-dev, no returncode: {e}")
        sys.exit

    logging.info(f"Test completed with return code: {testret}")

    if testret == 0:
        bisect_result = "good"
        logging.info(f"Commit {commit} marked as GOOD (test passed)")
    elif testret == 1:
        # TBD: Retry failed test to make sure it is not a flaky test
        bisect_result = "bad"
        logging.info(f"Commit {commit} marked as BAD (test failed)")
    elif testret == 2:
        # TBD: Retry failed test to make sure it is not a flaky test
        bisect_result = "skip"
        logging.info(f"Commit {commit} marked as SKIP (test inconclusive)")
    elif testret == 3:
        logging.warning("Maestro internal error - will retry")
        kci_err(f"Maestro failed to execute the test.")
        # Internal maestro error, retry procesure
        return None
    else:
        logging.error(f"Unexpected return code {testret} from kci-dev")
        kci_err(
            f"Unknown or critical return code from kci-dev: {testret}. Try to run last command manually and inspect the output:"
        )
        kci_err(f"{' '.join(cmd)}")
        sys.exit(1)
    cmd = ["git", "bisect", bisect_result]
    commitid = git_exec_getcommit(cmd)
    if not commitid:
        logging.error("Git bisect returned empty commit")
        kci_err("git bisect failed, commit return is empty")
        sys.exit(1)

    state["history"].append({commit: bisect_result})
    state["next_commit"] = commitid
    logging.info(f"Bisection history updated - {len(state['history'])} commits tested")
    os.chdir(olddir)
    return state


@click.command(
    help="""Bisect Linux Kernel regression to find the commit that introduced a failure.

This command performs automated git bisection to identify which commit caused a
test regression. It automatically checks out commits, runs tests via KernelCI,
and marks commits as good/bad based on test results.

The bisection state is saved to a file, allowing you to interrupt and resume
the process. Use --ignore-state to start a fresh bisection.

\b
Examples:
  kci-dev bisect --giturl https://git.kernel.org/torvalds/linux.git \\
                 --branch master --good v6.6 --bad v6.7 \\
                 --job-filter baseline --platform-filter qemu-x86 \\
                 --test baseline.login

  # Resume previous bisection
  kci-dev bisect

  # Start fresh, ignoring saved state
  kci-dev bisect --ignore-state --giturl ... --good ... --bad ...
"""
)
@click.option("--giturl", help="Git repository URL containing the kernel source")
@click.option("--branch", help="Git branch to bisect on")
@click.option("--good", help="Known good commit (tag, SHA, or ref)")
@click.option("--bad", help="Known bad commit (tag, SHA, or ref)")
@click.option(
    "--retry-fail", help="Number of times to retry failed tests (default: 2)", default=2
)
@click.option(
    "--workdir",
    help="Local directory for kernel source checkout (default: kcidev-src)",
    default="kcidev-src",
    type=click.Path(),
)
@click.option(
    "--ignore-state", help="Ignore saved state and start fresh bisection", is_flag=True
)
@click.option(
    "--state-file",
    help="State file name (default: state.json)",
    default="state.json",
    type=click.Path(),
)
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
    "--test", help="Specific test expected to fail (e.g., baseline.login, ltp.syscalls)"
)

# test
@click.pass_context
def bisect(
    ctx,
    giturl,
    branch,
    good,
    bad,
    retry_fail,
    workdir,
    ignore_state,
    state_file,
    job_filter,
    platform_filter,
    test,
):
    logging.info("Starting bisect command")
    logging.debug(
        f"Parameters - giturl: {giturl}, branch: {branch}, good: {good}, bad: {bad}"
    )
    logging.debug(
        f"Filters - job: {job_filter}, platform: {platform_filter}, test: {test}"
    )
    logging.debug(f"Options - workdir: {workdir}, ignore_state: {ignore_state}")

    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")

    state_file = os.path.join(workdir, state_file)
    state = load_state(state_file)
    if state is None or ignore_state:
        if ignore_state:
            logging.info("Ignoring saved state, starting fresh bisection")
        else:
            logging.info("No saved state found, starting new bisection")
        state = default_state
        # Check if user provided any required parameters
        if not any([giturl, branch, good, bad, job_filter, platform_filter, test]):
            # No parameters provided and no state file - show help
            logging.debug("No parameters provided and no state file - showing help")
            ctx = click.get_current_context()
            click.echo(ctx.get_help())
            sys.exit(0)

        # Validate required parameters for new bisection
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
        state["retry_fail"] = retry_fail
        state["job_filter"] = job_filter
        state["platform_filter"] = platform_filter
        state["test"] = test
        state["workdir"] = workdir
        logging.info("Initialized new bisection state")
        repo = update_tree(workdir, branch, giturl)
        save_state(state, state_file)
    else:
        logging.info("Resuming bisection from saved state")
        print_state(state)
        repo = update_tree(state["workdir"], state["branch"], state["giturl"])

    if not state["bisect_init"]:
        logging.info("Initializing git bisect")
        state["next_commit"] = init_bisect(repo, state)
        state["bisect_init"] = True
        save_state(state, state_file)

    while True:
        click.secho("Bisection loop", fg="green")
        logging.info(
            f"Starting bisection iteration - commits tested: {len(state.get('history', []))}"
        )
        new_state = bisection_loop(state)
        if new_state is None:
            logging.warning("Test failed, retrying")
            click.secho("Retry failed test", fg="green")
            continue
        state = new_state
        save_state(state, state_file)


if __name__ == "__main__":
    main_kcidev()
