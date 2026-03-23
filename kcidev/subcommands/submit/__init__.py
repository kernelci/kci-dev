#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime, timezone

import click

from kcidev.libs.common import kci_err, kci_msg, kci_warning
from kcidev.libs.git_repo import get_folder_repository
from kcidev.libs.kcidb import (
    build_build_payload,
    build_checkout_payload,
    build_submission_payload,
    generate_build_id,
    generate_checkout_id,
    resolve_kcidb_config,
    submit_to_kcidb,
)
from kcidev.subcommands.submit.options import (
    build_options,
    checkout_options,
    submit_common_options,
)


@click.group(help="Submit data to KCIDB")
@click.pass_context
def submit(ctx):
    """Commands related to submitting data to KCIDB."""
    cfg = ctx.obj.get("CFG")
    if cfg:
        instance = ctx.obj.get("INSTANCE")
        if not instance:
            instance = cfg.get("default_instance")
        ctx.obj["INSTANCE"] = instance


@submit.command()
@submit_common_options
@checkout_options
@build_options
@click.option(
    "--from-json",
    "from_json",
    type=click.Path(exists=True),
    help="Path to a JSON file with the complete KCIDB payload",
)
@click.pass_context
def build(
    ctx,
    origin,
    kcidb_rest_url,
    kcidb_token,
    dry_run,
    git_folder,
    giturl,
    branch,
    commit,
    tree_name,
    patchset_hash,
    arch,
    config_name,
    compiler,
    status,
    start_time,
    duration,
    log_url,
    config_url,
    comment,
    command,
    from_json,
):
    """Submit build results to KCIDB."""
    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")

    # --from-json mode
    if from_json:
        if git_folder:
            kci_err("--from-json and --git-folder are mutually exclusive")
            raise click.Abort()
        payload = _load_json_payload(from_json, origin)
        if dry_run:
            kci_msg(json.dumps(payload, indent=2, sort_keys=True))
            return
        rest_url, token = resolve_kcidb_config(
            cfg, instance, kcidb_rest_url, kcidb_token
        )
        result = submit_to_kcidb(rest_url, token, payload)
        kci_msg(f"Submitted successfully: {result}")
        return

    # Require --origin for non-JSON mode
    if not origin:
        kci_err("--origin is required (or use --from-json)")
        raise click.Abort()

    # --git-folder auto-detection
    if git_folder:
        detected_url, detected_branch, detected_commit = get_folder_repository(
            git_folder, branch
        )
        if not giturl:
            giturl = detected_url
        if not branch:
            branch = detected_branch
        if not commit:
            commit = detected_commit

    # Validate minimum required fields for ID generation
    if not giturl or not commit:
        kci_err(
            "--giturl and --commit are required (or use --git-folder or --from-json)"
        )
        raise click.Abort()

    if not branch:
        branch = ""

    if patchset_hash is None:
        patchset_hash = ""

    # Default start_time to current UTC
    if not start_time:
        start_time = datetime.now(timezone.utc).isoformat()

    # Generate IDs
    checkout_id = generate_checkout_id(origin, giturl, branch, commit, patchset_hash)
    build_id = generate_build_id(
        origin, checkout_id, arch or "", config_name or "", compiler or "", start_time
    )

    # Build payload
    checkout = build_checkout_payload(
        origin,
        checkout_id,
        tree_name=tree_name,
        git_repository_url=giturl,
        git_repository_branch=branch if branch else None,
        git_commit_hash=commit,
        patchset_hash=patchset_hash if patchset_hash else None,
    )

    build_obj = build_build_payload(
        origin,
        build_id,
        checkout_id,
        start_time=start_time,
        duration=duration,
        architecture=arch,
        compiler=compiler,
        config_name=config_name,
        config_url=config_url,
        log_url=log_url,
        comment=comment,
        command=command,
        status=status,
    )

    payload = build_submission_payload([checkout], [build_obj])

    if dry_run:
        kci_msg(json.dumps(payload, indent=2, sort_keys=True))
        return

    # Submit
    rest_url, token = resolve_kcidb_config(cfg, instance, kcidb_rest_url, kcidb_token)
    result = submit_to_kcidb(rest_url, token, payload)
    kci_msg(f"Submitted successfully: {result}")


def _load_json_payload(path, origin_override):
    """Load and validate a JSON payload file."""
    try:
        with open(path, "r") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        kci_err(f"Failed to read JSON file: {e}")
        raise click.Abort()

    if "version" not in payload:
        kci_err("JSON payload must contain a 'version' key")
        raise click.Abort()

    if "checkouts" not in payload and "builds" not in payload:
        kci_err("JSON payload must contain at least 'checkouts' or 'builds'")
        raise click.Abort()

    # Override origin if specified
    if origin_override:
        for obj_list_key in ("checkouts", "builds", "tests"):
            if obj_list_key in payload:
                for obj in payload[obj_list_key]:
                    obj["origin"] = origin_override

    return payload


if __name__ == "__main__":
    submit()
