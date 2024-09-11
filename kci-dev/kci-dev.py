#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from libs.common import *
from subcommands import commit, patch


@click.group(
    help="Stand alone tool for Linux Kernel developers and maintainers that can test local Linux Kernel changes on a enabled KernelCI server"
)
@click.version_option("0.0.1", prog_name="kci-dev")
@click.option("--settings", default=".kci-dev.toml", help="path of toml setting file")
@click.pass_context
def cli(ctx, settings):
    ctx.obj = {"CFG": load_toml(settings)}
    pass


def run():
    cli.add_command(commit.commit)
    cli.add_command(patch.patch)
    cli()


if __name__ == "__main__":
    run()
