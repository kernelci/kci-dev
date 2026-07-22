"""Repository-wide smoke coverage for kcidev scripts.

These tests intentionally walk every Python module under kcidev/subcommands and
kcidev/libs so newly added command or helper scripts cannot fall out of the
pytest chain unnoticed.
"""

import importlib
import pkgutil

import click
import pytest
from click.testing import CliRunner

from kcidev.main import get_cli

PACKAGES_UNDER_TEST = ("kcidev.subcommands", "kcidev.libs")


def _walk_modules(package_name):
    package = importlib.import_module(package_name)
    yield package.__name__
    for module_info in pkgutil.walk_packages(
        package.__path__, prefix=f"{package.__name__}."
    ):
        yield module_info.name


ALL_SCRIPT_MODULES = sorted(
    {module for package in PACKAGES_UNDER_TEST for module in _walk_modules(package)}
)


@pytest.mark.parametrize("module_name", ALL_SCRIPT_MODULES)
def test_every_kcidev_script_imports(module_name):
    """Every script under kcidev/subcommands and kcidev/libs imports cleanly."""
    module = importlib.import_module(module_name)
    assert module.__name__ == module_name


def _click_command_paths(command, prefix=()):
    yield prefix, command
    if isinstance(command, click.Group):
        for name, child in sorted(command.commands.items()):
            yield from _click_command_paths(child, prefix + (name,))


CLI_COMMAND_PATHS = list(_click_command_paths(get_cli()))


@pytest.mark.parametrize(
    "path,command",
    CLI_COMMAND_PATHS,
    ids=lambda value: " ".join(value) if isinstance(value, tuple) else None,
)
def test_every_registered_cli_command_has_working_help(path, command, tmp_path):
    """Every registered kci-dev command and subgroup must render --help."""
    settings = tmp_path / "kci-dev.toml"
    settings.write_text(
        'default_instance = "staging"\n'
        '[staging]\napi = "https://api.example.org/"\n'
        'pipeline = "https://pipeline.example.org/"\n'
        'token = "secret"\n',
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(get_cli(), ["--settings", str(settings), *path, "--help"])

    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output


def test_registered_cli_exposes_expected_top_level_commands():
    """Protect against accidentally dropping a kcidev subcommand from main.py."""
    cli = get_cli()
    assert set(cli.commands) >= {
        "bisect",
        "checkout",
        "commit",
        "config",
        "maestro",
        "mcp",
        "results",
        "storage",
        "submit",
        "testretry",
        "watch",
    }
