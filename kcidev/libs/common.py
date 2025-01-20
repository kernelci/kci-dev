#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

import click

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_toml(settings, subcommand):
    fname = "kci-dev.toml"
    config = None

    if os.path.exists(settings):
        if os.path.isfile(settings):
            with open(settings, "rb") as f:
                config = tomllib.load(f)
        else:
            kci_err("The --settings location is not a kci-dev config file")
            raise click.Abort()
        return config

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    if os.path.exists(user_path):
        with open(user_path, "rb") as f:
            config = tomllib.load(f)
        return config

    global_path = os.path.join("/", "etc", fname)
    if os.path.exists(global_path):
        with open(global_path, "rb") as f:
            config = tomllib.load(f)
        return config

    # config and results subcommand work without a config file
    if subcommand != "config" and subcommand != "results":
        if not config:
            kci_err(
                f"No config file found, please use `kci-dev config` to create a config file"
            )
            raise click.Abort()

    return config


def config_path(settings):
    fname = "kci-dev.toml"

    if os.path.exists(settings):
        return settings

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    if os.path.exists(user_path):
        return user_path

    global_path = os.path.join("/", "etc", fname)
    if os.path.exists(global_path):
        return global_path


def kci_msg(content):
    click.echo(content)


def kci_log(content):
    click.secho(content, err=True)


def kci_warning(content):
    click.secho(content, fg="yellow", err=True)


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
