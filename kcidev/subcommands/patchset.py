#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import sys

import click

from kcidev.libs.common import *
from kcidev.libs.maestro_common import *

MAX_INLINE_PATCHES = 32
MAX_INLINE_PATCH_SIZE = 10 * 1024 * 1024


def load_patch_files(paths):
    """Read local patch files, rejecting what the server would refuse."""
    if len(paths) > MAX_INLINE_PATCHES:
        raise click.ClickException(
            f"Too many patches: {len(paths)} (maximum {MAX_INLINE_PATCHES})"
        )
    patches = []
    for path in paths:
        size = os.path.getsize(path)
        if size > MAX_INLINE_PATCH_SIZE:
            raise click.ClickException(
                f"{path}: patch too large ({size} bytes, "
                f"maximum {MAX_INLINE_PATCH_SIZE})"
            )
        with open(path, "rb") as f:
            data = f.read()
        if not data:
            raise click.ClickException(f"{path}: patch file is empty")
        if b"\x00" in data:
            raise click.ClickException(f"{path}: binary content not allowed")
        try:
            patches.append(data.decode("utf-8"))
        except UnicodeDecodeError:
            raise click.ClickException(f"{path}: not valid UTF-8 text")
    return patches


@click.command(
    help="""Test patches on top of an existing KernelCI checkout.

This command submits a patchset request to KernelCI's pipeline system,
applying one or more patches on top of a checkout node created with the
checkout command. Patches can be local files, uploaded inline, or URLs
from an allowed domain such as patchwork.kernel.org. Patches are applied
in the order given.

\b
Examples:
  # Trigger a checkout first, then test local patches on top of it
  kci-dev checkout --giturl https://git.kernel.org/torvalds/linux.git \\
                   --branch master --tipoftree
  kci-dev patchset --nodeid <checkout_nodeid> \\
                   --patch 0001-fix.patch --patch 0002-fix.patch

  # Test a patchwork series URL with job and platform filters
  kci-dev patchset --nodeid <checkout_nodeid> \\
                   --patchurl https://patchwork.kernel.org/series/123/mbox/ \\
                   --job-filter baseline --platform-filter qemu-x86

  # Watch for a specific test result and return appropriate exit code
  kci-dev patchset --nodeid <checkout_nodeid> --patch fix.patch \\
                   --job-filter baseline --watch --test baseline.login
"""
)
@click.option(
    "--nodeid",
    help="Checkout node ID to apply the patches on (from kci-dev checkout)",
    required=True,
)
@click.option(
    "--patch",
    help="Local patch file to upload. Can be used multiple times",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--patchurl",
    help="Patch URL from an allowed domain. Can be used multiple times",
    multiple=True,
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
    "--watch",
    "-w",
    help="Watch and display test results interactively as they complete",
    is_flag=True,
)
@click.option(
    "--test",
    help="Watch for specific test result and set exit code accordingly (requires --watch)",
)
@click.pass_context
def patchset(ctx, nodeid, patch, patchurl, job_filter, platform_filter, watch, test):
    logging.info(f"Starting patchset command for node: {nodeid}")
    logging.debug(f"Patches: {patch}, patch URLs: {patchurl}")
    logging.debug(
        f"Filters: job_filter={job_filter}, platform_filter={platform_filter}"
    )
    logging.debug(f"Options: watch={watch}, test={test}")

    if patch and patchurl:
        raise click.UsageError("--patch and --patchurl are mutually exclusive")
    if not patch and not patchurl:
        raise click.UsageError("Either --patch or --patchurl is required")
    if watch and not job_filter:
        kci_err("No job filter defined. Can't watch for a job(s)!")
        return
    if test and not watch:
        kci_err("Test option only works with watch option")
        return

    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = cfg[instance]["pipeline"]
    apiurl = cfg[instance]["api"]
    token = cfg[instance]["token"]

    logging.debug(f"Using instance: {instance}")
    logging.debug(f"Pipeline URL: {url}")
    logging.debug(f"API URL: {apiurl}")

    patches = load_patch_files(patch) if patch else None

    resp = send_patchset(
        url,
        token,
        nodeid,
        patches=patches,
        patchurls=list(patchurl) if patchurl else None,
        job_filter=list(job_filter) if job_filter else None,
        platform_filter=list(platform_filter) if platform_filter else None,
    )
    if not resp:
        kci_err("Failed to submit patchset")
        sys.exit(64)

    if "message" in resp:
        click.secho(resp["message"], fg="green")

    treeid = None
    node = resp.get("node")
    if node:
        treeid = node.get("treeid")
        patchset_nodeid = node.get("id")

        logging.info(
            f"Patchset submitted successfully - treeid: {treeid}, "
            f"nodeid: {patchset_nodeid}"
        )

        if treeid:
            click.secho(f"treeid: {treeid}", fg="green")
        if patchset_nodeid:
            click.secho(f"patchset_nodeid: {patchset_nodeid}", fg="green")

    if watch:
        if not treeid:
            logging.error("No treeid in response, cannot watch jobs")
            kci_err("No treeid returned. Can't watch for a job(s)!")
            return
        click.secho(f"Watching for jobs on treeid: {treeid}", fg="green")
        if test:
            click.secho(f"Watching for test result: {test}", fg="green")
        maestro_watch_jobs(apiurl, token, treeid, job_filter, test)
