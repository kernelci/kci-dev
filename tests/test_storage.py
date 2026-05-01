#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Smoke tests for the `kci-dev storage` subcommand.

These exercise the Click layer with mocks to ensure CLI arguments are
forwarded to the underlying library functions exactly as expected.
"""

from unittest.mock import patch

from click.testing import CliRunner

from kcidev.subcommands.storage import storage


def _invoke(args, obj=None):
    runner = CliRunner()
    return runner.invoke(storage, args, obj=obj or {})


class TestStorageUpload:
    def test_cli_flags_forwarded_to_resolve_and_upload(self, tmp_path):
        local_file = tmp_path / "log.txt"
        local_file.write_text("hello")

        with patch(
            "kcidev.subcommands.storage.resolve_storage_config",
            return_value=("https://storage.example.com", "tok-abc"),
        ) as mock_resolve, patch(
            "kcidev.subcommands.storage.upload_file",
            return_value="ok",
        ) as mock_upload:
            result = _invoke(
                [
                    "upload",
                    "--storage-url",
                    "https://storage.example.com",
                    "--storage-token",
                    "tok-abc",
                    "--path",
                    "myci/build-123",
                    str(local_file),
                ],
            )

        assert result.exit_code == 0, result.output
        mock_resolve.assert_called_once_with(
            None, None, "https://storage.example.com", "tok-abc"
        )
        mock_upload.assert_called_once_with(
            "https://storage.example.com",
            "tok-abc",
            "myci/build-123",
            str(local_file),
        )

    def test_multiple_files_each_uploaded(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("a")
        f2.write_text("b")

        with patch(
            "kcidev.subcommands.storage.resolve_storage_config",
            return_value=("https://s", "t"),
        ), patch(
            "kcidev.subcommands.storage.upload_file",
            return_value="ok",
        ) as mock_upload:
            result = _invoke(
                [
                    "upload",
                    "--storage-url",
                    "https://s",
                    "--storage-token",
                    "t",
                    "--path",
                    "myci/build-1",
                    str(f1),
                    str(f2),
                ],
            )

        assert result.exit_code == 0, result.output
        assert mock_upload.call_count == 2
        mock_upload.assert_any_call("https://s", "t", "myci/build-1", str(f1))
        mock_upload.assert_any_call("https://s", "t", "myci/build-1", str(f2))

    def test_context_cfg_and_instance_forwarded_to_resolve(self, tmp_path):
        local_file = tmp_path / "log.txt"
        local_file.write_text("hello")

        cfg = {"staging": {"storage_url": "https://s", "storage_token": "t"}}

        with patch(
            "kcidev.subcommands.storage.resolve_storage_config",
            return_value=("https://s", "t"),
        ) as mock_resolve, patch(
            "kcidev.subcommands.storage.upload_file",
            return_value="ok",
        ):
            result = _invoke(
                [
                    "upload",
                    "--path",
                    "myci/build-9",
                    str(local_file),
                ],
                obj={"CFG": cfg, "INSTANCE": "staging"},
            )

        assert result.exit_code == 0, result.output
        mock_resolve.assert_called_once_with(cfg, "staging", None, None)

    def test_path_is_required(self, tmp_path):
        local_file = tmp_path / "log.txt"
        local_file.write_text("hello")

        result = _invoke(["upload", str(local_file)])
        assert result.exit_code != 0
        assert "--path" in result.output

    def test_files_argument_required(self):
        result = _invoke(["upload", "--path", "myci/build-1"])
        assert result.exit_code != 0


class TestStorageCheckauth:
    def test_cli_flags_forwarded_to_resolve_and_check_auth(self):
        with patch(
            "kcidev.subcommands.storage.resolve_storage_config",
            return_value=("https://storage.example.com", "tok-abc"),
        ) as mock_resolve, patch(
            "kcidev.subcommands.storage.check_auth",
            return_value="valid",
        ) as mock_check:
            result = _invoke(
                [
                    "checkauth",
                    "--storage-url",
                    "https://storage.example.com",
                    "--storage-token",
                    "tok-abc",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_resolve.assert_called_once_with(
            None, None, "https://storage.example.com", "tok-abc"
        )
        mock_check.assert_called_once_with(
            "https://storage.example.com", "tok-abc"
        )

    def test_no_flags_passes_none_to_resolve(self):
        cfg = {"staging": {"storage_url": "https://s", "storage_token": "t"}}

        with patch(
            "kcidev.subcommands.storage.resolve_storage_config",
            return_value=("https://s", "t"),
        ) as mock_resolve, patch(
            "kcidev.subcommands.storage.check_auth",
            return_value="valid",
        ) as mock_check:
            result = _invoke(
                ["checkauth"],
                obj={"CFG": cfg, "INSTANCE": "staging"},
            )

        assert result.exit_code == 0, result.output
        mock_resolve.assert_called_once_with(cfg, "staging", None, None)
        mock_check.assert_called_once_with("https://s", "t")
