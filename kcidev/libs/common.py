#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import click
import toml


def load_toml(settings):
    fname = "kci-dev.toml"
    config = None

    global_path = os.path.join("/", "etc", fname)
    if os.path.exists(global_path):
        with open(global_path, "r") as f:
            config = toml.load(f)

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    if os.path.exists(user_path):
        with open(user_path, "r") as f:
            config = toml.load(f)

    if os.path.exists(settings):
        with open(settings, "r") as f:
            config = toml.load(f)

    if not config:
        kci_err(
            f"No `{fname}` configuration file found at `{global_path}`, `{user_path}` or `{settings}`"
        )
        raise click.Abort()

    return config


def kci_msg(content):
    click.echo(content)


def kci_err(content):
    click.secho(content, fg="red", err=True)


def kci_msg_nonl(content):
    click.echo(content, nl=False)


def kci_msg_green_nonl(content):
    click.secho(content, fg="green", nl=False)


def kci_msg_red_nonl(content):
    click.secho(content, fg="red", nl=False)


def kci_msg_yellow_nonl(content):
    click.secho(content, fg="bright_yellow", nl=False)


def kci_msg_cyan_nonl(content):
    click.secho(content, fg="cyan", nl=False)
