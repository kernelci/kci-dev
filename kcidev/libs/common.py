#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
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

    logging.debug(f"Loading config for subcommand: {subcommand}")
    logging.debug(f"Settings path: {settings}")

    if os.path.exists(settings):
        if os.path.isfile(settings):
            logging.info(f"Loading config from: {settings}")
            try:
                with open(settings, "rb") as f:
                    config = tomllib.load(f)
                logging.debug(f"Successfully loaded config from {settings}")
            except Exception as e:
                logging.error(f"Failed to parse TOML file {settings}: {e}")
                kci_err(f"Failed to parse config file: {e}")
                raise click.Abort()
        else:
            logging.error(f"Settings path is not a file: {settings}")
            kci_err("The --settings location is not a kci-dev config file")
            raise click.Abort()
        return config

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    logging.debug(f"Checking user config path: {user_path}")
    if os.path.exists(user_path):
        logging.info(f"Loading config from user directory: {user_path}")
        try:
            with open(user_path, "rb") as f:
                config = tomllib.load(f)
            logging.debug("Successfully loaded user config")
        except Exception as e:
            logging.error(f"Failed to parse user config {user_path}: {e}")
            kci_err(f"Failed to parse config file: {e}")
            raise click.Abort()
        return config

    global_path = os.path.join("/", "etc", fname)
    logging.debug(f"Checking global config path: {global_path}")
    if os.path.exists(global_path):
        logging.info(f"Loading config from global directory: {global_path}")
        try:
            with open(global_path, "rb") as f:
                config = tomllib.load(f)
            logging.debug("Successfully loaded global config")
        except Exception as e:
            logging.error(f"Failed to parse global config {global_path}: {e}")
            kci_err(f"Failed to parse config file: {e}")
            raise click.Abort()
        return config

    # config and results subcommand work without a config file
    if subcommand != "config" and subcommand != "results":
        if not config:
            logging.warning(f"No config file found for subcommand {subcommand}")
            kci_err(
                f"No config file found, please use `kci-dev config` to create a config file"
            )
            raise click.Abort()
    else:
        logging.debug(f"No config file required for {subcommand} subcommand")

    return config


def config_path(settings):
    fname = "kci-dev.toml"

    logging.debug(f"Looking for config file, settings: {settings}")

    if os.path.exists(settings):
        logging.debug(f"Found config at settings path: {settings}")
        return settings

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    if os.path.exists(user_path):
        logging.debug(f"Found config at user path: {user_path}")
        return user_path

    global_path = os.path.join("/", "etc", fname)
    if os.path.exists(global_path):
        logging.debug(f"Found config at global path: {global_path}")
        return global_path

    logging.debug("No config file found in any location")
    return None


def kci_info(content):
    logging.info(content)


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


def kci_msg_bold(content, nl=True):
    click.secho(content, bold=True, nl=nl)


def kci_msg_green(content, nl=True):
    click.secho(content, fg="green", nl=nl)


def kci_msg_red(content, nl=True):
    click.secho(content, fg="red", nl=nl)


def kci_msg_yellow(content, nl=True):
    click.secho(content, fg="bright_yellow", nl=nl)


def kci_msg_cyan(content, nl=True):
    click.secho(content, fg="cyan", nl=nl)


def kci_msg_json(content, indent=1):
    click.echo(json.dumps(content, indent=indent))
