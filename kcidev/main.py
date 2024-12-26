#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click

from kcidev.libs.common import *
from kcidev.subcommands import (
    checkout,
    commit,
    maestro_results,
    patch,
    results,
    testretry,
)


@click.group(
    help="Stand alone tool for Linux Kernel developers and maintainers to interact with KernelCI."
)
@click.version_option("0.1.1.dev1", prog_name="kci-dev")
@click.option(
    "--settings",
    default=".kci-dev.toml",
    help="Local settings file to use",
    required=False,
)
@click.option("--instance", help="API instance to use", required=False)
@click.pass_context
def cli(ctx, settings, instance):
    if ctx.invoked_subcommand != "results":
        ctx.obj = {"CFG": load_toml(settings)}
        if instance:
            ctx.obj["INSTANCE"] = instance
        else:
            ctx.obj["INSTANCE"] = ctx.obj["CFG"].get("default_instance")
        if not ctx.obj["INSTANCE"]:
            kci_err("No instance defined in settings or as argument")
            raise click.Abort()
        if ctx.obj["INSTANCE"] not in ctx.obj["CFG"]:
            kci_err(f"Instance {ctx.obj['INSTANCE']} not found in {settings}")
            raise click.Abort()
        pass


def run():
    cli.add_command(checkout.checkout)
    cli.add_command(commit.commit)
    cli.add_command(patch.patch)
    cli.add_command(maestro_results.maestro_results)
    cli.add_command(testretry.testretry)
    cli.add_command(results.results)
    cli()


if __name__ == "__main__":
    run()
