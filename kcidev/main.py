#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click

from kcidev.libs.common import *
from kcidev.subcommands import checkout, commit, patch, results, testretry


@click.group(
    help="Stand alone tool for Linux Kernel developers and maintainers that can test local Linux Kernel changes on a enabled KernelCI server"
)
@click.version_option("0.1.0", prog_name="kci-dev")
@click.option("--settings", default=".kci-dev.toml", help="path of toml setting file")
@click.option("--instance", help="API instance to use", required=False)
@click.pass_context
def cli(ctx, settings, instance):
    ctx.obj = {"CFG": load_toml(settings)}
    if instance:
        ctx.obj["INSTANCE"] = instance
    else:
        ctx.obj["INSTANCE"] = ctx.obj["CFG"].get("default_instance")
    if not ctx.obj["INSTANCE"]:
        click.secho("No instance defined in settings or as argument", fg="red")
        raise click.Abort()
    if ctx.obj["INSTANCE"] not in ctx.obj["CFG"]:
        click.secho(f"Instance {ctx.obj['INSTANCE']} not found in {settings}", fg="red")
        raise click.Abort()
    pass


def run():
    cli.add_command(checkout.checkout)
    cli.add_command(commit.commit)
    cli.add_command(patch.patch)
    cli.add_command(results.results)
    cli.add_command(testretry.testretry)
    cli()


if __name__ == "__main__":
    run()
