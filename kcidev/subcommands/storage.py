#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

import click

from kcidev.libs.common import kci_err, kci_msg
from kcidev.libs.storage import check_auth, resolve_storage_config, upload_file


@click.group(
    help="""Interact with KernelCI storage.

This command group provides access to KernelCI storage operations including
uploading files and validating authentication tokens.

\b
Examples:
  # Upload a file (path recommended to match your origin)
  kci-dev storage upload --path myci/build-123 ./some-files.tar.xz
  # Upload multiple files
  kci-dev storage upload --path myci/build-123 log.txt config.gz
  # Validate authentication token
  kci-dev storage checkauth
""",
    invoke_without_command=True,
)
@click.pass_context
def storage(ctx):
    """Commands related to KernelCI storage."""
    cfg = ctx.obj.get("CFG")
    if cfg:
        instance = ctx.obj.get("INSTANCE")
        if not instance:
            instance = cfg.get("default_instance")
        ctx.obj["INSTANCE"] = instance

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        sys.exit(0)


@storage.command()
@click.option(
    "--storage-url",
    help="Storage server URL (overrides config and env)",
)
@click.option(
    "--storage-token",
    help="Storage JWT token (overrides config and env)",
)
@click.option(
    "--path",
    "remote_path",
    required=True,
    help="Remote directory path, recommended to match your origin (e.g. origin/build-123)",
)
@click.argument(
    "files",
    nargs=-1,
    required=True,
    type=click.Path(exists=True),
)
@click.pass_context
def upload(ctx, storage_url, storage_token, remote_path, files):
    """Upload files to KernelCI storage."""
    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")

    url, token = resolve_storage_config(cfg, instance, storage_url, storage_token)

    for file_path in files:
        if os.path.isdir(file_path):
            kci_err(f"Skipping directory: {file_path}")
            continue
        filename = os.path.basename(file_path)
        kci_msg(f"Uploading {filename} to {remote_path}/...")
        result = upload_file(url, token, remote_path, file_path)
        kci_msg(f"Uploaded: {filename} - {result}")


@storage.command()
@click.option(
    "--storage-url",
    help="Storage server URL (overrides config and env)",
)
@click.option(
    "--storage-token",
    help="Storage JWT token (overrides config and env)",
)
@click.pass_context
def checkauth(ctx, storage_url, storage_token):
    """Validate storage authentication token."""
    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")

    url, token = resolve_storage_config(cfg, instance, storage_url, storage_token)

    result = check_auth(url, token)
    kci_msg(result)
