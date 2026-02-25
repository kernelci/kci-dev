#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from functools import wraps

import click


def submit_common_options(func):
    @click.option(
        "--origin",
        help="KCIDB origin name (CI system identifier)",
    )
    @click.option(
        "--kcidb-rest-url",
        help="KCIDB REST API URL (overrides config and env)",
    )
    @click.option(
        "--kcidb-token",
        help="KCIDB auth token (overrides config and env)",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Print JSON payload without submitting",
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def checkout_options(func):
    @click.option(
        "--git-folder",
        type=click.Path(exists=True),
        help="Path to git repo; auto-detects giturl, branch, commit",
    )
    @click.option(
        "--giturl",
        help="Git repository URL",
    )
    @click.option(
        "--branch",
        help="Git branch name",
    )
    @click.option(
        "--commit",
        help="Full git commit hash",
    )
    @click.option(
        "--tree-name",
        help="Tree name for dashboard grouping",
    )
    @click.option(
        "--patchset-hash",
        default=None,
        help="SHA256 patchset hash (empty string means no patches)",
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def build_options(func):
    @click.option(
        "--arch",
        help="Target build architecture (e.g. x86_64)",
    )
    @click.option(
        "--config-name",
        help="Build configuration name (e.g. defconfig)",
    )
    @click.option(
        "--compiler",
        help="Compiler name and version (e.g. gcc-14)",
    )
    @click.option(
        "--status",
        type=click.Choice(
            ["PASS", "FAIL", "ERROR", "MISS", "DONE", "SKIP"], case_sensitive=True
        ),
        help="Build status",
    )
    @click.option(
        "--start-time",
        help="RFC3339 build start time (defaults to current UTC)",
    )
    @click.option(
        "--duration",
        type=click.FLOAT,
        help="Build duration in seconds",
    )
    @click.option(
        "--log-url",
        help="URL of the build log",
    )
    @click.option(
        "--config-url",
        help="URL of the build config",
    )
    @click.option(
        "--comment",
        help="Human-readable comment",
    )
    @click.option(
        "--command",
        help="Shell command used for the build",
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
