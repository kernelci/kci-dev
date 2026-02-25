#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import os
import urllib.parse

import click

from kcidev.libs.common import kci_err, kci_msg, kci_warning, kcidev_session

KCIDB_SCHEMA_MAJOR = 5
KCIDB_SCHEMA_MINOR = 3


# ---------------------
# ID generation
# ---------------------


def _sha256_hex(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def generate_checkout_id(origin, repo_url, branch, commit, patchset_hash=""):
    """
    Deterministic checkout ID from source identity.
    Format: origin:ck-<sha256(repo_url|branch|commit|patchset_hash)>
    """
    seed = f"{repo_url}|{branch}|{commit}|{patchset_hash}"
    return f"{origin}:ck-{_sha256_hex(seed)}"


def generate_build_id(origin, checkout_id, arch, config_name, compiler, start_time):
    """
    Deterministic build ID from build parameters.
    Format: origin:b-<sha256(checkout_id|arch|config_name|compiler|start_time)>
    """
    seed = f"{checkout_id}|{arch}|{config_name}|{compiler}|{start_time}"
    return f"{origin}:b-{_sha256_hex(seed)}"


# ---------------------
# Payload building
# ---------------------


def build_checkout_payload(origin, checkout_id, **kwargs):
    """Build a checkout object for the KCIDB JSON payload."""
    checkout = {
        "id": checkout_id,
        "origin": origin,
    }
    field_map = {
        "tree_name": "tree_name",
        "git_repository_url": "git_repository_url",
        "git_repository_branch": "git_repository_branch",
        "git_commit_hash": "git_commit_hash",
        "patchset_hash": "patchset_hash",
        "start_time": "start_time",
        "valid": "valid",
    }
    for json_key, kwarg_key in field_map.items():
        val = kwargs.get(kwarg_key)
        if val is not None:
            checkout[json_key] = val
    return checkout


def build_build_payload(origin, build_id, checkout_id, **kwargs):
    """Build a build object for the KCIDB JSON payload."""
    build = {
        "id": build_id,
        "origin": origin,
        "checkout_id": checkout_id,
    }
    field_map = {
        "start_time": "start_time",
        "duration": "duration",
        "architecture": "architecture",
        "compiler": "compiler",
        "config_name": "config_name",
        "config_url": "config_url",
        "log_url": "log_url",
        "comment": "comment",
        "command": "command",
        "status": "status",
    }
    for json_key, kwarg_key in field_map.items():
        val = kwargs.get(kwarg_key)
        if val is not None:
            build[json_key] = val
    return build


def build_submission_payload(checkouts, builds):
    """Build the complete KCIDB v5.3 submission JSON."""
    payload = {
        "version": {"major": KCIDB_SCHEMA_MAJOR, "minor": KCIDB_SCHEMA_MINOR},
    }
    if checkouts:
        payload["checkouts"] = checkouts
    if builds:
        payload["builds"] = builds
    return payload


# ---------------------
# Config resolution
# ---------------------


def _parse_kcidb_rest_env(env_value):
    """
    Parse KCIDB_REST env var.
    Format: https://token@host[:port][/path]
    Returns (url, token) or (None, None) on failure.
    """
    parsed = urllib.parse.urlparse(env_value)
    token = parsed.username
    if not token:
        return None, None

    # Rebuild URL without credentials
    host = parsed.hostname
    if parsed.port:
        host = f"{host}:{parsed.port}"
    path = parsed.path if parsed.path else "/"
    if not path.endswith("/submit"):
        path = path.rstrip("/") + "/submit"

    clean_url = urllib.parse.urlunparse(
        (parsed.scheme, host, path, parsed.params, parsed.query, parsed.fragment)
    )
    return clean_url, token


def resolve_kcidb_config(cfg, instance, cli_rest_url, cli_token):
    """
    Resolve KCIDB REST URL and token. Priority:
    1. CLI flags (--kcidb-rest-url, --kcidb-token)
    2. KCIDB_REST environment variable
    3. Instance config (kcidb_rest_url, kcidb_token in TOML)

    Returns (rest_url, token) tuple.
    Raises click.Abort if no valid credentials found.
    """
    # 1. CLI flags
    if cli_rest_url and cli_token:
        return cli_rest_url, cli_token

    # 2. Environment variable
    kcidb_rest_env = os.environ.get("KCIDB_REST")
    if kcidb_rest_env:
        url, token = _parse_kcidb_rest_env(kcidb_rest_env)
        if url and token:
            return url, token
        kci_warning("KCIDB_REST env var set but could not parse token from it")

    # 3. Instance config
    if cfg and instance and instance in cfg:
        inst_cfg = cfg[instance]
        rest_url = inst_cfg.get("kcidb_rest_url")
        token = inst_cfg.get("kcidb_token")
        if rest_url and token:
            return rest_url, token

    kci_err(
        "No KCIDB credentials found. Provide --kcidb-rest-url and --kcidb-token, "
        "set KCIDB_REST env var, or configure kcidb_rest_url/kcidb_token in config file"
    )
    raise click.Abort()


# ---------------------
# REST submission
# ---------------------


def submit_to_kcidb(rest_url, token, payload, timeout=60):
    """
    POST the JSON payload to the KCIDB REST API.

    Returns the response text on success.
    Raises click.Abort on failure.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    try:
        response = kcidev_session.post(
            rest_url, json=payload, headers=headers, timeout=timeout
        )
    except Exception as e:
        kci_err(f"KCIDB API connection error: {e}")
        raise click.Abort()

    if response.status_code == 200:
        return response.text
    else:
        kci_err(f"KCIDB submission failed: HTTP {response.status_code}")
        try:
            kci_err(response.json())
        except Exception:
            kci_err(response.text)
        raise click.Abort()
