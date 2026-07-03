#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import click

from kcidev.libs.common import *
from kcidev.subcommands import (
    bisect,
    checkout,
    commit,
    config,
    maestro,
    results,
    storage,
    submit,
    testretry,
    watch,
)


@click.group(
    help="Stand alone tool for Linux Kernel developers and maintainers to interact with KernelCI."
)
@click.version_option(kcidev_version, prog_name="kci-dev")
@click.option(
    "--settings",
    default=".kci-dev.toml",
    help="Local settings file to use",
    required=False,
)
@click.option("--instance", help="API instance to use", required=False)
@click.option("--debug", is_flag=True, help="Enable debug info")
@click.pass_context
def cli(ctx, settings, instance, debug):
    if debug:
        # DEBUG level is too verbose about included packages
        # us INFO instead
        logging.basicConfig(level=logging.INFO)

    subcommand = ctx.invoked_subcommand
    ctx.obj = {"CFG": load_toml(settings, subcommand)}
    ctx.obj["SETTINGS"] = settings
    if subcommand not in ("results", "config"):
        if instance:
            ctx.obj["INSTANCE"] = instance
        elif subcommand not in ("submit", "storage"):
            ctx.obj["INSTANCE"] = ctx.obj["CFG"].get("default_instance")
            fconfig = config_path(settings)
            if not ctx.obj["INSTANCE"]:
                kci_err(f"No instance defined in settings or as argument in {fconfig}")
                raise click.Abort()
            if ctx.obj["INSTANCE"] not in ctx.obj["CFG"]:
                kci_err(f"Instance {ctx.obj['INSTANCE']} not found in {fconfig}")
                raise click.Abort()


def register_commands(command_group=None):
    """Register all kci-dev subcommands on a Click command group.

    The CLI entry point and the public Python API both use this helper so the
    same commands are available from the shell and from library code.
    """
    command_group = command_group or cli
    command_group.add_command(bisect.bisect)
    command_group.add_command(checkout.checkout)
    command_group.add_command(commit.commit)
    command_group.add_command(config.config)
    command_group.add_command(maestro.maestro)
    command_group.add_command(testretry.testretry)
    command_group.add_command(results.results)
    command_group.add_command(storage.storage)
    command_group.add_command(submit.submit)
    command_group.add_command(watch.watch)
    return command_group


def get_cli():
    """Return the kci-dev Click command group with subcommands registered."""
    return register_commands(cli)


def run():
    get_cli()()


if __name__ == "__main__":
    run()
