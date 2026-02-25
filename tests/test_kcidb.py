#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

import click
import pytest

from kcidev.libs.kcidb import (
    build_build_payload,
    build_checkout_payload,
    build_submission_payload,
    generate_build_id,
    generate_checkout_id,
    resolve_kcidb_config,
)

# ---------------------
# ID generation tests
# ---------------------


class TestGenerateCheckoutId:
    def test_deterministic(self):
        id1 = generate_checkout_id(
            "myci", "https://git.kernel.org/linux.git", "main", "abc123", ""
        )
        id2 = generate_checkout_id(
            "myci", "https://git.kernel.org/linux.git", "main", "abc123", ""
        )
        assert id1 == id2

    def test_format(self):
        result = generate_checkout_id(
            "myci", "https://git.kernel.org/linux.git", "main", "abc123", ""
        )
        assert result.startswith("myci:ck-")
        # origin:ck- + 64 hex chars
        local_id = result.split(":")[1]
        assert local_id.startswith("ck-")
        assert len(local_id) == 3 + 64

    def test_different_repos_produce_different_ids(self):
        id1 = generate_checkout_id("myci", "https://repo1.git", "main", "abc", "")
        id2 = generate_checkout_id("myci", "https://repo2.git", "main", "abc", "")
        assert id1 != id2

    def test_different_commits_produce_different_ids(self):
        id1 = generate_checkout_id("myci", "https://repo.git", "main", "abc", "")
        id2 = generate_checkout_id("myci", "https://repo.git", "main", "def", "")
        assert id1 != id2

    def test_different_patchsets_produce_different_ids(self):
        id1 = generate_checkout_id("myci", "https://repo.git", "main", "abc", "")
        id2 = generate_checkout_id("myci", "https://repo.git", "main", "abc", "patch1")
        assert id1 != id2

    def test_different_origins_produce_different_ids(self):
        id1 = generate_checkout_id("ci1", "https://repo.git", "main", "abc", "")
        id2 = generate_checkout_id("ci2", "https://repo.git", "main", "abc", "")
        assert id1 != id2


class TestGenerateBuildId:
    def test_deterministic(self):
        id1 = generate_build_id(
            "myci",
            "myci:ck-abc",
            "x86_64",
            "defconfig",
            "gcc-12",
            "2024-01-01T00:00:00+00:00",
        )
        id2 = generate_build_id(
            "myci",
            "myci:ck-abc",
            "x86_64",
            "defconfig",
            "gcc-12",
            "2024-01-01T00:00:00+00:00",
        )
        assert id1 == id2

    def test_format(self):
        result = generate_build_id(
            "myci",
            "myci:ck-abc",
            "x86_64",
            "defconfig",
            "gcc-12",
            "2024-01-01T00:00:00+00:00",
        )
        assert result.startswith("myci:b-")
        local_id = result.split(":")[1]
        assert local_id.startswith("b-")
        assert len(local_id) == 2 + 64

    def test_different_arch_produce_different_ids(self):
        id1 = generate_build_id("myci", "ck1", "x86_64", "defconfig", "gcc", "t1")
        id2 = generate_build_id("myci", "ck1", "arm64", "defconfig", "gcc", "t1")
        assert id1 != id2


# ---------------------
# Payload building tests
# ---------------------


class TestBuildCheckoutPayload:
    def test_minimal(self):
        result = build_checkout_payload("myci", "myci:ck-1")
        assert result == {"id": "myci:ck-1", "origin": "myci"}

    def test_with_optional_fields(self):
        result = build_checkout_payload(
            "myci",
            "myci:ck-1",
            git_repository_url="https://repo.git",
            git_commit_hash="abc123",
            tree_name="mainline",
        )
        assert result["git_repository_url"] == "https://repo.git"
        assert result["git_commit_hash"] == "abc123"
        assert result["tree_name"] == "mainline"

    def test_none_fields_excluded(self):
        result = build_checkout_payload(
            "myci",
            "myci:ck-1",
            git_repository_url="https://repo.git",
            tree_name=None,
        )
        assert "tree_name" not in result
        assert "git_repository_url" in result


class TestBuildBuildPayload:
    def test_minimal(self):
        result = build_build_payload("myci", "myci:b-1", "myci:ck-1")
        assert result == {
            "id": "myci:b-1",
            "origin": "myci",
            "checkout_id": "myci:ck-1",
        }

    def test_with_optional_fields(self):
        result = build_build_payload(
            "myci",
            "myci:b-1",
            "myci:ck-1",
            architecture="x86_64",
            status="PASS",
            duration=120.5,
        )
        assert result["architecture"] == "x86_64"
        assert result["status"] == "PASS"
        assert result["duration"] == 120.5

    def test_none_fields_excluded(self):
        result = build_build_payload(
            "myci",
            "myci:b-1",
            "myci:ck-1",
            architecture="x86_64",
            duration=None,
        )
        assert "duration" not in result
        assert result["architecture"] == "x86_64"


class TestBuildSubmissionPayload:
    def test_complete(self):
        checkouts = [{"id": "x:1", "origin": "x"}]
        builds = [{"id": "x:2", "origin": "x", "checkout_id": "x:1"}]
        result = build_submission_payload(checkouts, builds)
        assert result["version"] == {"major": 5, "minor": 3}
        assert len(result["checkouts"]) == 1
        assert len(result["builds"]) == 1

    def test_empty_lists_excluded(self):
        result = build_submission_payload([], [])
        assert "checkouts" not in result
        assert "builds" not in result
        assert "version" in result


# ---------------------
# Config resolution tests
# ---------------------


class TestResolveKcidbConfig:
    def test_cli_flags_take_priority(self):
        url, token = resolve_kcidb_config(None, None, "https://host/submit", "mytoken")
        assert url == "https://host/submit"
        assert token == "mytoken"

    def test_env_var(self, monkeypatch):
        monkeypatch.setenv("KCIDB_REST", "https://mytoken@kcidb.example.com/")
        url, token = resolve_kcidb_config(None, None, None, None)
        assert "kcidb.example.com" in url
        assert token == "mytoken"

    def test_env_var_appends_submit(self, monkeypatch):
        monkeypatch.setenv("KCIDB_REST", "https://mytoken@kcidb.example.com/")
        url, token = resolve_kcidb_config(None, None, None, None)
        assert url.endswith("/submit")

    def test_instance_config(self):
        cfg = {
            "staging": {
                "kcidb_rest_url": "https://host/submit",
                "kcidb_token": "tok123",
            }
        }
        url, token = resolve_kcidb_config(cfg, "staging", None, None)
        assert url == "https://host/submit"
        assert token == "tok123"

    def test_no_credentials_aborts(self, monkeypatch):
        monkeypatch.delenv("KCIDB_REST", raising=False)
        with pytest.raises(click.exceptions.Abort):
            resolve_kcidb_config(None, None, None, None)

    def test_cli_overrides_env(self, monkeypatch):
        monkeypatch.setenv("KCIDB_REST", "https://envtoken@host.com/")
        url, token = resolve_kcidb_config(
            None, None, "https://cli-host/submit", "cli-token"
        )
        assert url == "https://cli-host/submit"
        assert token == "cli-token"
