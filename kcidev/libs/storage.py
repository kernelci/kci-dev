#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os

import click
import requests

from kcidev.libs.common import kci_err, kci_msg, kcidev_session


def resolve_storage_config(cfg, instance, cli_url, cli_token):
    """
    Resolve storage URL and token. Priority:
    1. CLI flags (--storage-url, --storage-token)
    2. Environment variables (KCI_STORAGE_URL, KCI_STORAGE_TOKEN)
    3. Instance config (storage_url, storage_token in TOML)

    Returns (storage_url, token) tuple.
    Raises click.Abort if no valid credentials found.
    """
    # 1. CLI flags
    if cli_url or cli_token:
        if not cli_url or not cli_token:
            kci_err("Both --storage-url and --storage-token must be provided together")
            raise click.Abort()
        logging.debug(f"Using storage config from CLI flags: {cli_url}")
        return cli_url, cli_token

    # 2. Environment variables
    env_url = os.environ.get("KCI_STORAGE_URL")
    env_token = os.environ.get("KCI_STORAGE_TOKEN")
    if env_url or env_token:
        if env_url and env_token:
            logging.debug(f"Using storage config from env vars: {env_url}")
            return env_url, env_token
        kci_err(
            "Both KCI_STORAGE_URL and KCI_STORAGE_TOKEN env vars must be set together"
        )
        raise click.Abort()

    # 3. Instance config
    if cfg and instance and instance in cfg:
        inst_cfg = cfg[instance]
        storage_url = inst_cfg.get("storage_url")
        storage_token = inst_cfg.get("storage_token")
        if storage_url and storage_token:
            logging.debug(
                f"Using storage config from instance '{instance}': {storage_url}"
            )
            return storage_url, storage_token

    kci_err(
        "No storage credentials found. Provide --storage-url and --storage-token, "
        "set KCI_STORAGE_URL/KCI_STORAGE_TOKEN env vars, "
        "or configure storage_url/storage_token in config file"
    )
    raise click.Abort()


def upload_file(storage_url, token, remote_path, local_file_path, timeout=120):
    """
    Upload a file to kernelci-storage.

    POST /v1/file with multipart form:
      - path: remote directory path
      - file0: file content
    """
    url = storage_url.rstrip("/") + "/v1/file"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    logging.info(f"Uploading {local_file_path} to {remote_path}/")
    logging.debug(f"POST request to: {url}")

    try:
        with open(local_file_path, "rb") as f:
            files = {"file0": (os.path.basename(local_file_path), f)}
            data = {"path": remote_path}
            response = kcidev_session.post(
                url, headers=headers, files=files, data=data, timeout=timeout
            )
        logging.debug(f"Upload response status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Upload request failed: {e}")
        kci_err(f"Storage connection error: {e}")
        raise click.Abort()

    if response.status_code == 200:
        logging.info(f"Upload successful: {os.path.basename(local_file_path)}")
        return response.text
    elif response.status_code == 401:
        kci_err("Authentication failed: invalid or expired token")
        raise click.Abort()
    else:
        kci_err(f"Upload failed (HTTP {response.status_code}): {response.text}")
        raise click.Abort()


def check_auth(storage_url, token, timeout=30):
    """
    Validate a JWT token against the storage server.

    GET /v1/checkauth
    Returns the response text on success.
    """
    url = storage_url.rstrip("/") + "/v1/checkauth"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    logging.info("Checking storage authentication")
    logging.debug(f"GET request to: {url}")

    try:
        response = kcidev_session.get(url, headers=headers, timeout=timeout)
        logging.debug(f"Auth check response status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Auth check request failed: {e}")
        kci_err(f"Storage connection error: {e}")
        raise click.Abort()

    if response.status_code == 200:
        logging.info(f"Authentication valid: {response.text}")
        return response.text
    elif response.status_code == 401:
        kci_err("Authentication failed: invalid or expired token")
        raise click.Abort()
    else:
        kci_err(f"Auth check failed (HTTP {response.status_code}): {response.text}")
        raise click.Abort()
