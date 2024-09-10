#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from subcommands import commit, patch


@click.group(
    help="Stand alone tool for Linux Kernel developers and maintainers that can test local Linux Kernel changes on a enabled KernelCI server"
)
@click.version_option("0.0.1", prog_name="kci-dev")
def cli():
    pass


def run():
    cli.add_command(commit.commit)
    cli.add_command(patch.patch)
    cli()


if __name__ == "__main__":
    run()
