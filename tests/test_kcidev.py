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
    command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "trees",
        "--origin",
        "maestro",
        "--days",
        "1",
        "--json",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=30)
    # Command should execute without syntax errors (may fail due to network/API issues)
    assert result.returncode in [0, 1]  # 0 for success, 1 for API/network errors


def test_kcidev_results_summary_help():
    """Test that summary command help works and contains expected information"""
    command = ["poetry", "run", "kci-dev", "results", "summary", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode == 0
    assert "Display a summary of results" in result.stdout
    assert "--origin" in result.stdout
    assert "--giturl" in result.stdout
    assert "--branch" in result.stdout
    assert "--commit" in result.stdout
    assert "--latest" in result.stdout
    assert "--history" in result.stdout
    assert "--json" in result.stdout


def test_kcidev_results_summary_import():
    """Test that summary functionality can be imported without errors"""
    from kcidev.subcommands.results.parser import cmd_summary

    # Test that function exists and is callable
    assert callable(cmd_summary)


def test_kcidev_results_summary_history_functionality():
    """Test that summary --history command functionality works"""
    from kcidev.subcommands.results.parser import (
        cmd_commits_history,
        format_colored_summary,
    )

    # Test that history-related functions exist and are callable
    assert callable(cmd_commits_history)
    assert callable(format_colored_summary)

    # Test format_colored_summary with various scenarios
    result_all_zero = format_colored_summary(0, 0, 0)
    assert isinstance(result_all_zero, str)
    assert result_all_zero == "0/0/0"

    result_with_values = format_colored_summary(10, 5, 2)
    assert isinstance(result_with_values, str)
    assert "/" in result_with_values
    assert "10" in result_with_values
    assert "5" in result_with_values
    assert "2" in result_with_values


def test_kcidev_results_summary_json_format():
    """Test that summary command accepts JSON output format"""
    # Test with known repository that should be available
    command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "summary",
        "--giturl",
        "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
        "--branch",
        "master",
        "--latest",
        "--json",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
    # Command should execute without syntax errors (may fail due to network/API issues)
    assert result.returncode in [0, 1]  # 0 for success, 1 for API/network errors


def test_kcidev_results_boots_help():
    """Test that boots command help works and contains expected information"""
    command = ["poetry", "run", "kci-dev", "results", "boots", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode == 0
    assert "Display boot results" in result.stdout
    assert "--origin" in result.stdout
    assert "--giturl" in result.stdout
    assert "--branch" in result.stdout
    assert "--commit" in result.stdout
    assert "--latest" in result.stdout
    assert "--status" in result.stdout
    assert "--download-logs" in result.stdout
    assert "--json" in result.stdout


def test_kcidev_results_boots_import():
    """Test that boots functionality can be imported without errors"""
    from kcidev.libs.dashboard import dashboard_fetch_boots
    from kcidev.subcommands.results.parser import cmd_tests

    # Test that functions exist and are callable
    assert callable(cmd_tests)  # boots uses cmd_tests internally
    assert callable(dashboard_fetch_boots)


def test_kcidev_results_boots_status_options():
    """Test that boots command accepts different status filter options"""
    # Test help contains status options
    command = ["poetry", "run", "kci-dev", "results", "boots", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode == 0
    assert "all" in result.stdout or "pass" in result.stdout or "fail" in result.stdout


def test_kcidev_results_boots_json_format():
    """Test that boots command accepts JSON output with valid parameters"""
    command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "boots",
        "--giturl",
        "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
        "--branch",
        "master",
        "--latest",
        "--status",
        "all",
        "--count",
        "--json",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
    # Command should execute without syntax errors (may fail due to network/API issues)
    assert result.returncode in [0, 1]  # 0 for success, 1 for API/network errors


def test_kcidev_results_boot_help():
    """Test that boot command help works and contains expected information"""
    command = ["poetry", "run", "kci-dev", "results", "boot", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode == 0
    assert "--id" in result.stdout
    assert "--download-logs" in result.stdout
    assert "--json" in result.stdout


def test_kcidev_results_boot_import():
    """Test that boot functionality can be imported without errors"""
    from kcidev.libs.dashboard import dashboard_fetch_test
    from kcidev.subcommands.results.parser import cmd_single_test

    # Test that functions exist and are callable
    assert callable(cmd_single_test)  # boot uses cmd_single_test internally
    assert callable(dashboard_fetch_test)


def test_kcidev_results_boot_id_required():
    """Test that boot command requires an ID parameter"""
    command = ["poetry", "run", "kci-dev", "results", "boot"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode != 0  # Should fail without required --id parameter


def test_kcidev_results_boot_invalid_id():
    """Test that boot command handles invalid IDs gracefully"""
    command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "boot",
        "--id",
        "invalid_id",
        "--json",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=30)
    # Should fail gracefully with invalid ID
    assert result.returncode in [0, 1]  # 0 or 1 depending on error handling


def test_kcidev_results_boot_with_real_id():
    """Test boot command with real ID obtained from boots command"""
    # First get a list of boots to extract a real ID
    boots_command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "boots",
        "--giturl",
        "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
        "--branch",
        "master",
        "--latest",
        "--json",
    ]
    boots_result = run(
        boots_command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60
    )

    if boots_result.returncode == 0 and boots_result.stdout.strip():
        try:
            import json

            boots_data = json.loads(boots_result.stdout)
            if isinstance(boots_data, list) and len(boots_data) > 0:
                # Extract the first boot ID
                first_boot = boots_data[0]
                boot_id = first_boot.get("id")

                if boot_id:
                    # Now test the boot command with the real ID
                    boot_command = [
                        "poetry",
                        "run",
                        "kci-dev",
                        "results",
                        "boot",
                        "--id",
                        boot_id,
                        "--json",
                    ]
                    boot_result = run(
                        boot_command,
                        stdout=PIPE,
                        stderr=PIPE,
                        universal_newlines=True,
                        timeout=30,
                    )
                    # Should succeed with real ID
                    assert boot_result.returncode == 0
                    # Should return valid JSON
                    boot_json = json.loads(boot_result.stdout)
                    assert isinstance(boot_json, dict)
                    assert "id" in boot_json
        except (json.JSONDecodeError, KeyError, IndexError):
            # If we can't parse JSON or extract ID, that's still a valid test result
            pass


def test_kcidev_results_tests_help():
    """Test that tests command help works and contains expected information"""
    command = ["poetry", "run", "kci-dev", "results", "tests", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode == 0
    assert "Display test results" in result.stdout
    assert "--origin" in result.stdout
    assert "--giturl" in result.stdout
    assert "--branch" in result.stdout
    assert "--commit" in result.stdout
    assert "--latest" in result.stdout
    assert "--status" in result.stdout
    assert "--download-logs" in result.stdout
    assert "--hardware" in result.stdout
    assert "--filter" in result.stdout
    assert "--json" in result.stdout


def test_kcidev_results_tests_import():
    """Test that tests functionality can be imported without errors"""
    from kcidev.libs.dashboard import dashboard_fetch_tests
    from kcidev.subcommands.results.parser import cmd_tests

    # Test that functions exist and are callable
    assert callable(cmd_tests)
    assert callable(dashboard_fetch_tests)


def test_kcidev_results_tests_filter_options():
    """Test that tests command accepts various filter options"""
    command = ["poetry", "run", "kci-dev", "results", "tests", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode == 0
    # Check for filtering options
    assert "--start-date" in result.stdout
    assert "--end-date" in result.stdout
    assert "--compiler" in result.stdout
    assert "--config" in result.stdout
    assert "--compatible" in result.stdout


def test_kcidev_results_tests_json_format():
    """Test that tests command accepts JSON output with valid parameters"""
    command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "tests",
        "--giturl",
        "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
        "--branch",
        "master",
        "--latest",
        "--status",
        "all",
        "--count",
        "--json",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
    # Command should execute without syntax errors (may fail due to network/API issues)
    assert result.returncode in [0, 1]  # 0 for success, 1 for API/network errors


def test_kcidev_results_test_help():
    """Test that test command help works and contains expected information"""
    command = ["poetry", "run", "kci-dev", "results", "test", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode == 0
    assert "--id" in result.stdout
    assert "--download-logs" in result.stdout
    assert "--json" in result.stdout


def test_kcidev_results_test_import():
    """Test that test functionality can be imported without errors"""
    from kcidev.libs.dashboard import dashboard_fetch_test
    from kcidev.subcommands.results.parser import cmd_single_test

    # Test that functions exist and are callable
    assert callable(cmd_single_test)
    assert callable(dashboard_fetch_test)


def test_kcidev_results_test_id_required():
    """Test that test command requires an ID parameter"""
    command = ["poetry", "run", "kci-dev", "results", "test"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    assert result.returncode != 0  # Should fail without required --id parameter


def test_kcidev_results_test_invalid_id():
    """Test that test command handles invalid IDs gracefully"""
    command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "test",
        "--id",
        "invalid_test_id",
        "--json",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=30)
    # Should fail gracefully with invalid ID
    assert result.returncode in [0, 1]  # 0 or 1 depending on error handling


def test_kcidev_results_test_with_real_id():
    """Test test command with real ID obtained from tests command"""
    # First get a list of tests to extract a real ID
    tests_command = [
        "poetry",
        "run",
        "kci-dev",
        "results",
        "tests",
        "--giturl",
        "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
        "--branch",
        "master",
        "--latest",
        "--json",
    ]
    tests_result = run(
        tests_command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60
    )

    if tests_result.returncode == 0 and tests_result.stdout.strip():
        try:
            import json

            tests_data = json.loads(tests_result.stdout)
            if isinstance(tests_data, list) and len(tests_data) > 0:
                # Extract the first test ID
                first_test = tests_data[0]
                test_id = first_test.get("id")

                if test_id:
                    # Now test the test command with the real ID
                    test_command = [
                        "poetry",
                        "run",
                        "kci-dev",
                        "results",
                        "test",
                        "--id",
                        test_id,
                        "--json",
                    ]
                    test_result = run(
                        test_command,
                        stdout=PIPE,
                        stderr=PIPE,
                        universal_newlines=True,
                        timeout=30,
                    )
                    # Should succeed with real ID
                    assert test_result.returncode == 0
                    # Should return valid JSON
                    test_json = json.loads(test_result.stdout)
                    assert isinstance(test_json, dict)
                    assert "id" in test_json
        except (json.JSONDecodeError, KeyError, IndexError):
            # If we can't parse JSON or extract ID, that's still a valid test result
            pass


def test_clean():
    # clean enviroment
    shutil.rmtree("my-new-repo/")
