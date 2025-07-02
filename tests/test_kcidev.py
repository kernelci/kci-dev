import os
import shutil
from subprocess import PIPE, run

import git
import pytest

from kcidev.subcommands.config import add_config


@pytest.fixture(scope="session")
def kcidev_config(tmpdir_factory):
    file = tmpdir_factory.mktemp("config").join(".kci-dev.toml")
    # prepare enviroment
    command = ["poetry", "run", "kci-dev", "config", "--file-path", file]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    return file


def test_kcidev_help():
    command = ["poetry", "run", "kci-dev", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_commit_help(kcidev_config):
    command = [
        "poetry",
        "run",
        "kci-dev",
        "--settings",
        kcidev_config,
        "commit",
        "--help",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_results_help(kcidev_config):
    command = [
        "poetry",
        "run",
        "kci-dev",
        "--settings",
        kcidev_config,
        "maestro",
        "results",
        "--help",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_testretry_help(kcidev_config):
    command = [
        "poetry",
        "run",
        "kci-dev",
        "--settings",
        kcidev_config,
        "testretry",
        "--help",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_checkout_help(kcidev_config):
    command = [
        "poetry",
        "run",
        "kci-dev",
        "--settings",
        kcidev_config,
        "checkout",
        "--help",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_results_tests(kcidev_config):
    command = [
        "poetry",
        "run",
        "kci-dev",
        "--settings",
        kcidev_config,
        "--instance",
        "staging",
        "maestro-results",
        "--nodeid",
        "65a1355ee98651d0fe81e41d",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)


def test_create_repo():
    repo_dir = os.path.join("my-new-repo")
    file_name = os.path.join(repo_dir, "new-file")
    file_name2 = os.path.join(repo_dir, "new-file2")
    r = git.Repo.init(repo_dir)
    open(file_name, "wb").close()
    r.index.add("new-file")
    r.index.commit("initial commit")
    test_branch = r.create_head("test")
    r.head.reference = test_branch
    open(file_name2, "wb").close()
    r.index.add("new-file2")
    r.index.commit("test")


def test_kcidev_commit(kcidev_config):
    command = [
        "poetry",
        "run",
        "kci-dev",
        "--settings",
        kcidev_config,
        "--instance",
        "staging",
        "commit",
        "--repository",
        "linux-next",
        "--origin",
        "master",
        "--branch",
        "test",
        "--path",
        "my-new-repo",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_main():
    from kcidev.subcommands.commit import api_connection

    print(api_connection("test"))

    pass


def test_kcidev_results_summary_history_help():
    """Test the --history flag appears in results summary help"""
    command = ["poetry", "run", "kci-dev", "results", "summary", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0
    assert "--history" in result.stdout
    assert "Show commit history data" in result.stdout


def test_kcidev_results_summary_history_import():
    """Test that history functionality can be imported without errors"""
    from kcidev.libs.dashboard import dashboard_fetch_commits_history
    from kcidev.subcommands.results.parser import (
        cmd_commits_history,
        format_colored_summary,
    )

    # Test that functions exist and are callable
    assert callable(cmd_commits_history)
    assert callable(format_colored_summary)
    assert callable(dashboard_fetch_commits_history)

    # Test format_colored_summary with sample data
    result = format_colored_summary(10, 5, 2)
    assert isinstance(result, str)
    assert "/" in result  # Should contain separators


def test_kcidev_results_hardware_list():
    """Test that hardware list command works and returns expected output format"""
    command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "hardware",
        "list",
        "--origin",
        "maestro",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)

    # Test should succeed
    assert result.returncode == 0

    # Should contain hardware entries with expected format
    output_lines = result.stdout.strip().split("\n")

    # Should have at least some hardware entries
    assert len(output_lines) > 0

    # Check format: lines should contain "- name:" and "compatibles:"
    name_lines = [line for line in output_lines if line.strip().startswith("- name:")]
    compatible_lines = [
        line for line in output_lines if line.strip().startswith("compatibles:")
    ]

    # Should have matching number of name and compatible lines
    assert len(name_lines) > 0
    assert len(compatible_lines) > 0
    assert len(name_lines) == len(compatible_lines)


def test_kcidev_results_hardware_list_json():
    """Test that hardware list command works with JSON output"""
    command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "hardware",
        "list",
        "--origin",
        "maestro",
        "--json",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
    print("#### stderr ####")
    print(result.stderr)

    # Test should succeed
    assert result.returncode == 0

    # Should be valid JSON
    import json

    try:
        data = json.loads(result.stdout)
        assert isinstance(data, list)

        # Should have at least some hardware entries
        assert len(data) > 0

        # Each entry should have 'name' and 'compatibles' fields
        for entry in data[:5]:  # Check first 5 entries
            assert "name" in entry
            assert "compatibles" in entry
            assert isinstance(entry["name"], str)
            assert isinstance(entry["compatibles"], str)

    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")


def test_kcidev_results_compare_help():
    """Test that compare command help works and contains expected information"""
    command = ["poetry", "run", "kci-dev", "results", "compare", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode == 0
    assert "Compare test results" in result.stdout
    assert "summary statistics" in result.stdout
    assert "--giturl" in result.stdout
    assert "--branch" in result.stdout
    assert "--latest" in result.stdout


def test_kcidev_results_compare_import():
    """Test that compare functionality can be imported without errors"""
    from kcidev.subcommands.results.parser import cmd_compare

    # Test that function exists and is callable
    assert callable(cmd_compare)


def test_kcidev_results_trees_help():
    """Test that trees command help works and contains expected information"""
    command = ["poetry", "run", "kci-dev", "results", "trees", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode == 0
    assert "List trees from a give origin" in result.stdout
    assert "--origin" in result.stdout
    assert "--days" in result.stdout
    assert "--verbose" in result.stdout
    assert "--json" in result.stdout


def test_kcidev_results_trees_import():
    """Test that trees functionality can be imported without errors"""
    from kcidev.subcommands.results.parser import cmd_list_trees

    # Test that function exists and is callable
    assert callable(cmd_list_trees)


def test_kcidev_results_trees_default_params():
    """Test that trees command accepts default parameters"""
    command = ["poetry", "run", "kci-dev", "results", "trees", "--origin", "maestro", "--days", "1", "--json"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=30)
    # Command should execute without syntax errors (may fail due to network/API issues)
    assert result.returncode in [0, 1]  # 0 for success, 1 for API/network errors


def test_clean():
    # clean enviroment
    shutil.rmtree("my-new-repo/")
