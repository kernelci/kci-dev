import gzip
import json
import logging
import re
from urllib.parse import urlparse

import requests
import yaml

from kcidev.libs.common import *
from kcidev.libs.dashboard import (
    DASHBOARD_API,
    DASHBOARD_URL,
    dashboard_fetch_tree_list,
)
from kcidev.libs.files import download_logs_to_file
from kcidev.libs.filters import (
    CompatibleFilter,
    CompilerFilter,
    ConfigFilter,
    DateRangeFilter,
    DurationFilter,
    FilterSet,
    GitBranchFilter,
    HardwareFilter,
    PathFilter,
    StatusFilter,
)
from kcidev.libs.job_filters import HardwareRegexFilter, TestRegexFilter, TreeFilter


def print_summary(type, n_pass, n_fail, n_inconclusive):

    kci_msg_nonl(f"{type}:\t")
    kci_msg_green(f"{n_pass}", nl=False) if n_pass else kci_msg_nonl(f"{n_pass}")
    kci_msg_nonl("/")
    kci_msg_red(f"{n_fail}", nl=False) if n_fail else kci_msg_nonl(f"{n_fail}")
    kci_msg_nonl("/")
    (
        kci_msg_yellow(f"{n_inconclusive}", nl=False)
        if n_inconclusive
        else kci_msg_nonl(f"{n_inconclusive}")
    )
    kci_msg_nonl(f"\n")


def sum_inconclusive_results(results):
    count = 0
    for status in ["ERROR", "SKIP", "MISS", "DONE", "NULL"]:
        if status in results.keys():
            count += results[status]

    return count


def create_summary_json(n_pass, n_fail, n_inconclusive):
    return {"pass": n_pass, "fail": n_fail, "inconclusive": n_inconclusive}


def create_tree_json(tree):
    tree_name = tree["tree_name"]
    if tree["tree_name"] is None:
        tree_name = "-"
    return {
        "tree": f"{tree_name}/{tree['git_repository_branch']}",
        "giturl": tree["git_repository_url"],
        "latest_commit_hash": tree["git_commit_hash"],
        "latest_commit_name": tree["git_commit_name"],
        "latest_commit_start_time": tree["start_time"],
    }


def create_build_json(build, log_path):
    return {
        "config": build["config_name"],
        "arch": build["architecture"],
        "compiler": build["compiler"],
        "status": build["status"],
        "config_url": build["config_url"],
        "log": log_path,
        "id": build["id"],
        "dashboard": f"{DASHBOARD_URL}/build/{build['id']}",
    }


def create_test_json(test, log_path):
    if test["status"] == "PASS":
        test_status = "PASS"
    elif test["status"] == "FAIL":
        test_status = "FAIL"
    else:
        test_status = f"INCONCLUSIVE (status: {test['status']})"
    config_name = "No config available"
    if "config" in test:
        config_name = test["config"]
    elif "config_name" in test:
        config_name = test["config_name"]

    runtime = None
    if "misc" in test.keys():
        runtime = test["misc"].get("runtime")

    json_output = {
        "test_path": test["path"],
        "hardware": test["environment_misc"]["platform"],
        "compatibles": test.get("environment_compatible", []),
        "config": config_name,
        "arch": test["architecture"],
        "status": test_status,
        "start_time": test["start_time"],
        "log": log_path,
        "id": test["id"],
        "dashboard": f"{DASHBOARD_URL}/build/{test['id']}",
    }

    if runtime:
        json_output["runtime"] = runtime

    return json_output


def cmd_summary(data, use_json):
    logging.info("Generating results summary")
    summary = data["summary"]

    builds = summary["builds"]["status"]
    inconclusive_builds, pass_builds, fail_builds = get_command_summary(builds)
    logging.debug(
        f"Builds summary - pass: {pass_builds}, fail: {fail_builds}, inconclusive: {inconclusive_builds}"
    )

    boots = summary["boots"]["status"]
    inconclusive_boots, pass_boots, fail_boots = get_command_summary(boots)
    logging.debug(
        f"Boots summary - pass: {pass_boots}, fail: {fail_boots}, inconclusive: {inconclusive_boots}"
    )

    tests = summary["tests"]["status"]
    inconclusive_tests, pass_tests, fail_tests = get_command_summary(tests)
    logging.debug(
        f"Tests summary - pass: {pass_tests}, fail: {fail_tests}, inconclusive: {inconclusive_tests}"
    )

    if use_json:
        builds_json = create_summary_json(pass_builds, fail_builds, inconclusive_builds)
        boots_json = create_summary_json(pass_boots, fail_boots, inconclusive_boots)
        tests_json = create_summary_json(pass_tests, fail_tests, inconclusive_tests)
        kci_msg(
            json.dumps(
                {"builds": builds_json, "boots": boots_json, "tests": tests_json}
            )
        )
    else:
        kci_msg("pass/fail/inconclusive")
        print_summary("builds", pass_builds, fail_builds, inconclusive_builds)
        print_summary("boots", pass_boots, fail_boots, inconclusive_boots)
        print_summary("tests", pass_tests, fail_tests, inconclusive_tests)


def get_command_summary(command_data):
    inconclusive_cmd = sum_inconclusive_results(command_data)
    pass_cmd = command_data["PASS"] if "PASS" in command_data.keys() else 0
    fail_cmd = command_data["FAIL"] if "FAIL" in command_data.keys() else 0
    return inconclusive_cmd, pass_cmd, fail_cmd


def cmd_list_trees(origin, use_json, days, verbose):
    logging.info(f"Listing trees for origin: {origin}")
    trees = dashboard_fetch_tree_list(origin, use_json, days)
    logging.debug(f"Found {len(trees)} trees")
    if use_json:
        kci_msg(json.dumps(list(map(lambda t: create_tree_json(t), trees))))
        return

    for t in trees:
        logging.debug(
            f"Tree: {t['tree_name']}/{t['git_repository_branch']} - {t['git_commit_hash']}"
        )
        if verbose:
            kci_msg_green(f"- {t['tree_name']}/{t['git_repository_branch']}:")
            kci_msg(f"  giturl: {t['git_repository_url']}")
            kci_msg(f"  latest: {t['git_commit_hash']} ({t['git_commit_name']})")
            kci_msg(f"  latest: {t['start_time']}")
    return trees


def cmd_builds(
    data,
    commit,
    download_logs,
    status,
    compiler,
    config,
    git_branch,
    count,
    use_json,
    verbose=True,
):
    logging.info(
        f"Processing builds with filters - status: {status}, compiler: {compiler}, config: {config}, branch: {git_branch}"
    )

    if status == "inconclusive" and use_json:
        kci_msg('{"message":"No information about inconclusive builds."}')
        return
    elif status == "inconclusive":
        kci_msg("No information about inconclusive builds.")
        return

    # Create filter set for builds
    filter_set = FilterSet()
    filter_set.add_filter(StatusFilter(status))
    filter_set.add_filter(CompilerFilter(compiler))
    filter_set.add_filter(ConfigFilter(config))
    filter_set.add_filter(GitBranchFilter(git_branch))

    logging.debug(f"Created filter set with {len(filter_set.filters)} filters")

    filtered_builds = 0
    filtered_builds_list = []
    builds = []
    total_builds = len(data["builds"])
    logging.debug(f"Processing {total_builds} builds")

    for build in data["builds"]:
        if not filter_set.matches(build):
            continue
        filtered_builds_list.append(build)
        log_path = build["log_url"]
        if download_logs:
            try:
                log_file = f"{build['config_name']}-{build['architecture']}-{build['compiler']}-{commit}.log"
                logging.debug(f"Downloading log for build {build['id']}")
                log_path = download_logs_to_file(build["log_url"], log_file)
            except Exception as e:
                logging.error(f"Failed to download log for build {build['id']}: {e}")
                kci_err(f"Failed to fetch log {build['log_url']}.")
                pass
        if count:
            filtered_builds += 1
        elif use_json:
            builds.append(create_build_json(build, log_path))
        else:
            print_build(build, log_path)
    logging.info(f"Filtered {filtered_builds} builds from {total_builds} total")

    if count and use_json:
        kci_msg(f'{{"count":{filtered_builds}}}')
    elif count and verbose:
        kci_msg(filtered_builds)
    elif use_json:
        kci_msg(json.dumps(builds))
    return filtered_builds_list


def print_build(build, log_path):
    kci_msg_nonl("- config:")
    kci_msg_cyan(build["config_name"], nl=False)
    kci_msg_nonl(" arch: ")
    kci_msg_cyan(build["architecture"], nl=False)
    kci_msg_nonl(" compiler: ")
    kci_msg_cyan(build["compiler"], nl=False)
    kci_msg("")

    kci_msg_nonl("  status:")
    if build["status"] == "PASS":
        kci_msg_green("PASS", nl=False)
    elif build["status"] == "FAIL":
        kci_msg_red("FAIL", nl=False)
    else:
        kci_msg_yellow(f"INCONCLUSIVE (status: {build['status']})", nl=False)
    kci_msg("")

    kci_msg(f"  config_url: {build['config_url']}")
    kci_msg(f"  log: {log_path}")
    kci_msg(f"  id: {build['id']}")
    kci_msg(f"  dashboard: {DASHBOARD_URL}/build/{build['id']}")
    kci_msg("")


# Legacy filter functions have been replaced by the unified filter system
# See kcidev.libs.filters for the new implementation


def filter_array2regex(filter_array):
    return f"^({'|'.join(filter_array)})$".replace(".", r"\.").replace("*", ".*")


def parse_filter_file(filter):
    if not filter:
        return None

    logging.debug("Parsing filter file")
    try:
        filter_data = yaml.safe_load(filter)
    except yaml.YAMLError as e:
        logging.error(f"Failed to parse YAML filter file: {e}")
        return None

    if filter_data is None:
        return None

    parsed_filter = {}
    if "hardware" in filter_data:
        parsed_filter["hardware"] = filter_array2regex(filter_data["hardware"])
        logging.debug(f"Hardware filter regex: {parsed_filter['hardware']}")
    if "test" in filter_data:
        parsed_filter["test"] = filter_array2regex(filter_data["test"])
        logging.debug(f"Test filter regex: {parsed_filter['test']}")
    if "tree" in filter_data:
        parsed_filter["tree"] = filter_array2regex(filter_data["tree"])
        logging.debug(f"Tree filter regex: {parsed_filter['tree']}")

    logging.info(f"Parsed filter file with {len(parsed_filter)} filter types")
    return parsed_filter


def cmd_tests(
    data,
    id,
    download_logs,
    status_filter,
    filter,
    start_date,
    end_date,
    compiler,
    config,
    hardware,
    test_path,
    git_branch,
    compatible,
    min_duration,
    max_duration,
    count,
    use_json,
    verbose=True,
):
    logging.info("Processing tests with filters")
    logging.debug(
        f"Test filters - status: {status_filter}, hardware: {hardware}, path: {test_path}"
    )
    logging.debug(
        f"Date range: {start_date} to {end_date}, duration: {min_duration}-{max_duration}s"
    )

    # Create filter set for tests
    filter_set = FilterSet()
    filter_set.add_filter(StatusFilter(status_filter))
    filter_set.add_filter(DateRangeFilter(start_date, end_date))
    filter_set.add_filter(CompilerFilter(compiler))
    filter_set.add_filter(ConfigFilter(config))
    filter_set.add_filter(HardwareFilter(hardware))
    filter_set.add_filter(PathFilter(test_path))
    filter_set.add_filter(GitBranchFilter(git_branch))
    filter_set.add_filter(CompatibleFilter(compatible))
    filter_set.add_filter(DurationFilter(min_duration, max_duration))

    # Parse YAML filter file if provided
    filter_data = parse_filter_file(filter)
    if filter_data:
        if "hardware" in filter_data:
            filter_set.add_filter(HardwareRegexFilter(filter_data["hardware"]))
        if "test" in filter_data:
            filter_set.add_filter(TestRegexFilter(filter_data["test"]))
        if "tree" in filter_data:
            filter_set.add_filter(TreeFilter(filter_data["tree"]))

    filtered_tests = 0
    tests = []
    total_tests = len(data)
    logging.debug(f"Processing {total_tests} tests")

    for test in data:
        if not filter_set.matches(test):
            continue

        log_path = test["log_url"]
        if download_logs:
            platform = (
                test["environment_misc"]["platform"]
                if "environment_misc" in test
                else "(Unknown platform)"
            )
            log_file = f"{platform}__{test['path']}__{test['config']}-{test['architecture']}-{test['compiler']}-{id}.log"
            try:
                logging.debug(f"Downloading log for test {test['id']} on {platform}")
                log_path = download_logs_to_file(test["log_url"], log_file)
            except Exception as e:
                logging.error(f"Failed to download log for test {test['id']}: {e}")
        if count:
            filtered_tests += 1
        elif use_json:
            tests.append(create_test_json(test, log_path))
        else:
            print_test(test, log_path)
    logging.info(f"Filtered {filtered_tests} tests from {total_tests} total")

    if count and use_json:
        kci_msg(f'{{"count":{filtered_tests}}}')
    elif count and verbose:
        kci_msg(filtered_tests)
    elif use_json:
        kci_msg(json.dumps(tests))
    return data


def print_test(test, log_path):
    kci_msg_nonl("- test path: ")
    kci_msg_cyan(test["path"], nl=False)
    kci_msg("")

    kci_msg_nonl("  hardware: ")
    kci_msg_cyan(test["environment_misc"]["platform"], nl=False)
    kci_msg("")

    if test["environment_compatible"]:
        kci_msg_nonl("  compatibles: ")
        kci_msg_cyan(" | ".join(test["environment_compatible"]), nl=False)
        kci_msg("")

    kci_msg_nonl("  config: ")
    if "config" in test:
        kci_msg_cyan(test["config"], nl=False)
    elif "config_name" in test:
        kci_msg_cyan(test["config_name"], nl=False)
    else:
        kci_msg_cyan("No config available", nl=False)
    kci_msg_nonl(" arch: ")
    kci_msg_cyan(test["architecture"], nl=False)
    kci_msg_nonl(" compiler: ")
    kci_msg_cyan(test["compiler"], nl=False)
    kci_msg("")

    kci_msg_nonl("  status:")
    if test["status"] == "PASS":
        kci_msg_green("PASS", nl=False)
    elif test["status"] == "FAIL":
        kci_msg_red("FAIL", nl=False)
    else:
        kci_msg_yellow(f"INCONCLUSIVE (status: {test['status']})", nl=False)
    kci_msg("")

    kci_msg(f"  log: {log_path}")
    kci_msg(f"  start time: {test['start_time']}")

    if "misc" in test.keys():
        runtime = test["misc"].get("runtime")
        kci_msg_nonl("  runtime: ")
        kci_msg_cyan(runtime, nl=False)
        kci_msg("")

    kci_msg(f"  id: {test['id']}")
    kci_msg(f"  dashboard: {DASHBOARD_URL}/test/{test['id']}")
    kci_msg("")


def cmd_single_test(test, download_logs, use_json):
    logging.info(f"Processing single test {test['id']} - {test['path']}")
    log_path = test["log_url"]
    if download_logs:
        log_file = f"{test['environment_misc']['platform']}__{test['path']}__{test['config_name']}-{test['architecture']}-{test['compiler']}-{test['id']}.log"
        try:
            logging.debug(f"Downloading log for test {test['id']}")
            log_path = download_logs_to_file(test["log_url"], log_file)
        except Exception as e:
            logging.error(f"Failed to download log: {e}")
    if use_json:
        kci_msg(create_test_json(test, log_path))
    else:
        print_test(test, log_path)


def cmd_single_build(build, download_logs, use_json):
    logging.info(f"Processing single build {build['id']} - {build['config_name']}")
    log_path = build["log_url"]
    if download_logs:
        log_file = log_file = (
            f"{build['config_name']}-{build['architecture']}-{build['compiler']}-{build['git_commit_hash']}-{build['id']}.log"
        )
        try:
            logging.debug(f"Downloading log for build {build['id']}")
            log_path = download_logs_to_file(build["log_url"], log_file)
        except Exception as e:
            logging.error(f"Failed to download log: {e}")
    if use_json:
        kci_msg(create_build_json(build, log_path))
    else:
        print_build(build, log_path)


def cmd_hardware_list(data, use_json):
    hardware_count = len(data["hardware"])
    logging.info(f"Listing {hardware_count} hardware platforms")

    if use_json:
        hardware = [
            {
                "name": hardware.get("hardware") or hardware["platform"],
                "compatibles": hardware["platform"],
            }
            for hardware in data["hardware"]
        ]
        kci_msg(json.dumps(hardware))
    else:
        for hardware in data["hardware"]:
            hardware_name = hardware.get("hardware") or hardware["platform"]
            logging.debug(f"Hardware: {hardware_name} - {hardware['platform']}")
            kci_msg_nonl("- name: ")
            kci_msg_cyan(hardware_name, nl=False)
            kci_msg("")

            kci_msg_nonl("  compatibles: ")
            kci_msg_cyan(hardware["platform"], nl=False)
            kci_msg("")
            kci_msg("")


def format_colored_summary(pass_count, fail_count, inconclusive_count):
    """Format pass/fail/inconclusive with colors like print_summary"""
    import click

    # Format with colors using click.style directly for table display
    pass_str = (
        click.style(str(pass_count), fg="green") if pass_count else str(pass_count)
    )
    fail_str = click.style(str(fail_count), fg="red") if fail_count else str(fail_count)
    inconclusive_str = (
        click.style(str(inconclusive_count), fg="yellow")
        if inconclusive_count
        else str(inconclusive_count)
    )

    return f"{pass_str}/{fail_str}/{inconclusive_str}"


def cmd_commits_history(data, use_json):
    """Display commit history data from /commits endpoint"""
    logging.info("Displaying commit history")

    if use_json:
        kci_msg(json.dumps(data))
    else:
        # Handle both list and dict responses
        if isinstance(data, list):
            commits = data
        else:
            commits = data.get("commits", [])

        if not commits:
            kci_msg("No commits found")
            return

        # Format as table with shortened pass/fail/inconclusive format
        from tabulate import tabulate

        table_data = []

        for commit in commits:
            # Get summaries
            builds = commit.get("builds", {})
            boots = commit.get("boots", {})
            tests = commit.get("tests", {})

            # Calculate totals in same format as regular summary
            builds_pass = builds.get("PASS", 0)
            builds_fail = builds.get("FAIL", 0)
            builds_inconclusive = (
                builds.get("ERROR", 0)
                + builds.get("SKIP", 0)
                + builds.get("MISS", 0)
                + builds.get("DONE", 0)
                + builds.get("NULL", 0)
            )

            boots_pass = boots.get("pass", 0)
            boots_fail = boots.get("fail", 0)
            boots_inconclusive = (
                boots.get("miss", 0)
                + boots.get("error", 0)
                + boots.get("null", 0)
                + boots.get("skip", 0)
                + boots.get("done", 0)
            )

            tests_pass = tests.get("pass", 0)
            tests_fail = tests.get("fail", 0)
            tests_inconclusive = (
                tests.get("error", 0)
                + tests.get("skip", 0)
                + tests.get("miss", 0)
                + tests.get("done", 0)
                + tests.get("null", 0)
            )

            # Get tags or fallback to empty string if no tags
            tags = commit.get("git_commit_tags", [])
            tags_str = ", ".join(tags) if tags else ""

            table_data.append(
                [
                    commit.get("git_commit_hash", "unknown"),
                    tags_str,
                    format_colored_summary(
                        builds_pass, builds_fail, builds_inconclusive
                    ),
                    format_colored_summary(boots_pass, boots_fail, boots_inconclusive),
                    format_colored_summary(tests_pass, tests_fail, tests_inconclusive),
                ]
            )

        headers = ["Commit", "Tags", "Builds", "Boots", "Tests"]
        # Use click.secho to preserve colors in the table
        import click

        click.secho(tabulate(table_data, headers=headers, tablefmt="grid"), color=True)


def cmd_compare(origin, giturl, branch, commits, use_json):
    """Find regressions (PASS->FAIL transitions) between commits"""
    logging.info("Analyzing regressions between commits")

    if commits is None:
        # Get latest commits from history
        from kcidev.libs.dashboard import dashboard_fetch_commits_history
        from kcidev.libs.git_repo import set_giturl_branch_commit

        # Get latest commit for history query
        giturl_resolved, branch_resolved, latest_commit = set_giturl_branch_commit(
            origin, giturl, branch, None, True, None
        )

        history_data = dashboard_fetch_commits_history(
            origin, giturl_resolved, branch_resolved, latest_commit, False
        )

        # Handle both list and dict responses
        if isinstance(history_data, list):
            commits_list = history_data
        else:
            commits_list = history_data.get("commits", [])

        if len(commits_list) < 2:
            kci_msg("Not enough commits in history for regression analysis")
            return

        # Use latest two commits
        latest_commit = commits_list[0]["git_commit_hash"]
        previous_commit = commits_list[1]["git_commit_hash"]

        kci_msg(f"Analyzing latest commits from history:")
        kci_msg(
            f"  Latest:   {latest_commit[:12]} ({commits_list[0].get('git_commit_name', 'unknown')})"
        )
        kci_msg(
            f"  Previous: {previous_commit[:12]} ({commits_list[1].get('git_commit_name', 'unknown')})"
        )

    else:
        if len(commits) != 2:
            kci_err("Exactly 2 commits required for regression analysis")
            raise click.Abort()

        previous_commit, latest_commit = commits

    def build_key(build):
        """Create unique key for build comparison"""
        config = build.get("config_name", "unknown")
        arch = build.get("architecture", "unknown")
        compiler = build.get("compiler", "unknown")
        return f"{config}|{arch}|{compiler}"

    def test_key(test):
        """Create unique key for test comparison"""
        test_path = test.get("test_path", test.get("path", "unknown"))
        hardware = test.get(
            "hardware", test.get("environment_misc", {}).get("platform", "unknown")
        )
        config = test.get("config", test.get("config_name", "unknown"))
        arch = test.get("arch", test.get("architecture", "unknown"))
        return f"{test_path}|{hardware}|{config}|{arch}"

    def get_all_data(commit_hash):
        """Get builds, boots, and tests for a commit"""
        from kcidev.libs.dashboard import (
            dashboard_fetch_boots,
            dashboard_fetch_builds,
            dashboard_fetch_tests,
        )

        try:
            builds_data = dashboard_fetch_builds(
                origin, giturl, branch, commit_hash, None, None, None, None, False
            )
            boots_data = dashboard_fetch_boots(
                origin, giturl, branch, commit_hash, None, None, None, None, False
            )
            tests_data = dashboard_fetch_tests(
                origin, giturl, branch, commit_hash, None, None, None, None, False
            )

            builds = builds_data.get("builds", [])
            boots = boots_data.get("boots", [])
            tests = tests_data.get("tests", [])

            return builds, boots, tests
        except Exception as e:
            kci_msg(f"Error fetching data for {commit_hash[:12]}: {e}")
            return [], [], []

    # Get all data for both commits
    kci_msg(f"Fetching builds, boots, and tests for commit {latest_commit[:12]}...")
    latest_builds, latest_boots, latest_tests = get_all_data(latest_commit)

    kci_msg(f"Fetching builds, boots, and tests for commit {previous_commit[:12]}...")
    previous_builds, previous_boots, previous_tests = get_all_data(previous_commit)

    if not any([latest_builds, latest_boots, latest_tests]) or not any(
        [previous_builds, previous_boots, previous_tests]
    ):
        kci_msg("Could not fetch data for one or both commits")
        return

    # Calculate summary statistics for both commits
    def calculate_summary_stats(builds, boots, tests):
        """Calculate pass/fail/inconclusive counts for builds, boots, tests"""
        # Builds
        build_pass = sum(1 for b in builds if b.get("status") == "PASS")
        build_fail = sum(1 for b in builds if b.get("status") == "FAIL")
        build_inconclusive = len(builds) - build_pass - build_fail

        # Boots
        boot_pass = sum(1 for b in boots if b.get("status") == "PASS")
        boot_fail = sum(1 for b in boots if b.get("status") == "FAIL")
        boot_inconclusive = len(boots) - boot_pass - boot_fail

        # Tests
        test_pass = sum(1 for t in tests if t.get("status") == "PASS")
        test_fail = sum(1 for t in tests if t.get("status") == "FAIL")
        test_inconclusive = len(tests) - test_pass - test_fail

        return (
            build_pass,
            build_fail,
            build_inconclusive,
            boot_pass,
            boot_fail,
            boot_inconclusive,
            test_pass,
            test_fail,
            test_inconclusive,
        )

    latest_stats = calculate_summary_stats(latest_builds, latest_boots, latest_tests)
    previous_stats = calculate_summary_stats(
        previous_builds, previous_boots, previous_tests
    )

    # Display summary comparison in table format
    kci_msg(f"\nSummary comparison:")

    import click
    from tabulate import tabulate

    # Create table data with colored pass/fail/inconclusive format
    table_data = [
        [
            "builds",
            format_colored_summary(latest_stats[0], latest_stats[1], latest_stats[2]),
            format_colored_summary(
                previous_stats[0], previous_stats[1], previous_stats[2]
            ),
        ],
        [
            "boots",
            format_colored_summary(latest_stats[3], latest_stats[4], latest_stats[5]),
            format_colored_summary(
                previous_stats[3], previous_stats[4], previous_stats[5]
            ),
        ],
        [
            "tests",
            format_colored_summary(latest_stats[6], latest_stats[7], latest_stats[8]),
            format_colored_summary(
                previous_stats[6], previous_stats[7], previous_stats[8]
            ),
        ],
    ]

    headers = [
        "Type",
        f"Latest ({latest_commit[:12]})",
        f"Previous ({previous_commit[:12]})",
    ]

    click.secho(tabulate(table_data, headers=headers, tablefmt="grid"), color=True)

    def find_regressions(latest_items, previous_items, key_func, item_type):
        """Find PASS->FAIL regressions for any item type"""
        latest_lookup = {key_func(item): item for item in latest_items}
        previous_lookup = {key_func(item): item for item in previous_items}

        regressions = []
        for key, latest_item in latest_lookup.items():
            if key in previous_lookup:
                previous_item = previous_lookup[key]
                previous_status = previous_item.get("status", "UNKNOWN")
                latest_status = latest_item.get("status", "UNKNOWN")

                if previous_status == "PASS" and latest_status == "FAIL":
                    regressions.append(
                        {"item": latest_item, "type": item_type, "key": key}
                    )

        return regressions

    # Find regressions for each category
    build_regressions = find_regressions(
        latest_builds, previous_builds, build_key, "build"
    )
    boot_regressions = find_regressions(latest_boots, previous_boots, test_key, "boot")
    test_regressions = find_regressions(latest_tests, previous_tests, test_key, "test")

    total_regressions = (
        len(build_regressions) + len(boot_regressions) + len(test_regressions)
    )

    # Output results
    if use_json:

        def format_item_json(regression):
            item = regression["item"]
            item_type = regression["type"]

            if item_type == "build":
                return {
                    "type": "build",
                    "config": item.get("config_name", "unknown"),
                    "arch": item.get("architecture", "unknown"),
                    "compiler": item.get("compiler", "unknown"),
                    "id": item.get("id", "unknown"),
                    "dashboard": f"{DASHBOARD_URL}/build/{item.get('id', 'unknown')}",
                    "log": item.get("log_url", ""),
                }
            else:  # boot or test
                return {
                    "type": item_type,
                    "test_path": item.get("test_path", item.get("path", "unknown")),
                    "hardware": item.get(
                        "hardware",
                        item.get("environment_misc", {}).get("platform", "unknown"),
                    ),
                    "config": item.get("config", item.get("config_name", "unknown")),
                    "arch": item.get("arch", item.get("architecture", "unknown")),
                    "id": item.get("id", "unknown"),
                    "dashboard": f"{DASHBOARD_URL}/test/{item.get('id', 'unknown')}",
                    "log": item.get("log_url", ""),
                }

        result = {
            "total_regressions": total_regressions,
            "build_regressions": len(build_regressions),
            "boot_regressions": len(boot_regressions),
            "test_regressions": len(test_regressions),
            "regressions": {
                "builds": [format_item_json(reg) for reg in build_regressions],
                "boots": [format_item_json(reg) for reg in boot_regressions],
                "tests": [format_item_json(reg) for reg in test_regressions],
            },
        }
        kci_msg(json.dumps(result))
    else:
        kci_msg(
            f"\nRegression analysis: {previous_commit[:12]} -> {latest_commit[:12]}"
        )
        kci_msg(f"Total regressions (PASS->FAIL): {total_regressions}")

        if build_regressions:
            kci_msg(f"\nBuild regressions ({len(build_regressions)}):")
            for regression in build_regressions:
                build = regression["item"]
                kci_msg_nonl("- config: ")
                kci_msg_cyan(build.get("config_name", "unknown"), nl=False)
                kci_msg_nonl(" arch: ")
                kci_msg_cyan(build.get("architecture", "unknown"), nl=False)
                kci_msg_nonl(" compiler: ")
                kci_msg_cyan(build.get("compiler", "unknown"), nl=False)
                kci_msg("")
                kci_msg(
                    f"  dashboard: {DASHBOARD_URL}/build/{build.get('id', 'unknown')}"
                )
                kci_msg("")

        if boot_regressions:
            kci_msg(f"\nBoot regressions ({len(boot_regressions)}):")
            for regression in boot_regressions:
                boot = regression["item"]
                test_path = boot.get("test_path", boot.get("path", "unknown"))
                hardware = boot.get(
                    "hardware",
                    boot.get("environment_misc", {}).get("platform", "unknown"),
                )
                config = boot.get("config", boot.get("config_name", "unknown"))

                kci_msg_nonl("- test path: ")
                kci_msg_cyan(test_path, nl=False)
                kci_msg("")
                kci_msg_nonl("  hardware: ")
                kci_msg_cyan(hardware, nl=False)
                kci_msg("")
                kci_msg_nonl("  config: ")
                kci_msg_cyan(config, nl=False)
                kci_msg("")
                kci_msg(
                    f"  dashboard: {DASHBOARD_URL}/test/{boot.get('id', 'unknown')}"
                )
                kci_msg("")

        if test_regressions:
            kci_msg(f"\nTest regressions ({len(test_regressions)}):")
            for regression in test_regressions:
                test = regression["item"]
                test_path = test.get("test_path", test.get("path", "unknown"))
                hardware = test.get(
                    "hardware",
                    test.get("environment_misc", {}).get("platform", "unknown"),
                )
                config = test.get("config", test.get("config_name", "unknown"))

                kci_msg_nonl("- test path: ")
                kci_msg_cyan(test_path, nl=False)
                kci_msg("")
                kci_msg_nonl("  hardware: ")
                kci_msg_cyan(hardware, nl=False)
                kci_msg("")
                kci_msg_nonl("  config: ")
                kci_msg_cyan(config, nl=False)
                kci_msg("")
                kci_msg(
                    f"  dashboard: {DASHBOARD_URL}/test/{test.get('id', 'unknown')}"
                )
                kci_msg("")

        if total_regressions == 0:
            kci_msg("✅ No regressions found - all status changes are expected")


def print_issue_information(issue, dashboard_url, new_tag=False):
    """Extract and print issue information"""

    if not isinstance(issue, dict):
        kci_err("Please provide issue dictionary to extract information")
        return

    if new_tag:
        kci_msg_nonl("- ")
        kci_msg_red("[NEW] ", nl=False)
        kci_msg_bold(f"{issue.get('comment')}")
    else:
        kci_msg_bold(f"- {issue.get('comment')}")
    kci_msg(f"  {dashboard_url}/issue/{issue.get('id')}")
    kci_msg(f"  origin: {issue.get('origin')}")
    kci_msg(f"  version: {issue.get('version')}")
    kci_msg(f"  field_timestamp: {issue.get('field_timestamp')}")

    for field in ["culprit_code", "culprit_tool", "culprit_harness"]:
        if not issue.get(field):
            continue
        if issue[field]:
            kci_msg_nonl(f"  {field}: ")
            kci_msg_red(issue[field])
        else:
            kci_msg(f"  {field}: {issue[field]}")

    if issue.get("categories"):
        kci_msg_nonl("  categories:")
        kci_msg(issue["categories"])


def print_issue(issue, new_tag=False):
    """Print issue information
    issue (dict): KCIDB issue dictionary"""

    print_issue_information(issue, DASHBOARD_URL, new_tag)

    extra = issue.get("extra")
    if not extra:
        kci_msg("")
        return
    if extra.get(issue["id"]):
        incident = extra.get(issue["id"]).get("first_incident")
        if incident:
            tree_branch = (
                f'{incident.get("tree_name")}/{incident.get("git_repository_branch")}'
            )
            kci_msg_nonl("  First incident seen on ")
            kci_msg_bold(tree_branch)
    kci_msg("")


def print_issues(data):
    """Print a list of issues with formatting
    data (dict): provide dictionary with 'issues' and 'extras' keys"""

    if not data.get("issues") or not data.get("extras"):
        kci_err("Please provide dictionary with 'issues' and 'extras' keys")
        return

    issues = data["issues"]
    extras = data["extras"]
    for issue in issues:
        print_issue_information(issue, DASHBOARD_URL)

        extra = extras.get(issue.get("id"))
        if extra:
            tree_branch = (
                f'{extra.get("tree_name")}/{extra.get("git_repository_branch")}'
            )
            kci_msg_nonl("  First incident seen on ")
            kci_msg_bold(tree_branch)
        kci_msg("")


def print_missing_data(item_type, data):
    """Print builds/tests for which KCIDB issues are missing"""
    from collections import defaultdict

    tree_groups = defaultdict(list)

    for row in data:
        try:
            tree_branch = row[0]
            commit = row[1]
            missing_ids = row[2]
        except IndexError:
            kci_msg_red("Failed to extract data for list view")
            continue
        tree_groups[tree_branch].append({"commit": commit, "missing_ids": missing_ids})

    if item_type == "builds":
        endpoint = "build"
    else:
        endpoint = "test"
    for tree_branch, commits in tree_groups.items():
        kci_msg_bold(f"{tree_branch}: ")
        for commit in commits:
            kci_msg(f"  - Commit:{commit['commit']}")
            for item in missing_ids:
                for item_id, status in item.items():
                    kci_msg_nonl(f"  {DASHBOARD_URL}/{endpoint}/{item_id}  status: ")
                    kci_msg_red(f"{status}")
        kci_msg(data)


def sum_tree_report_inconclusive_results(results):
    count = 0
    for status in [
        "error_count",
        "skip_count",
        "miss_count",
        "done_count",
        "null_count",
    ]:
        if status in results.keys():
            count += results[status]

    return count


def get_tree_report_summary(command_data):
    inconclusive_cmd = sum_tree_report_inconclusive_results(command_data)
    pass_cmd = command_data["pass_count"] if "pass_count" in command_data.keys() else 0
    fail_cmd = command_data["fail_count"] if "fail_count" in command_data.keys() else 0
    return inconclusive_cmd, pass_cmd, fail_cmd


def status_mapping(status):
    if status == "PASS":
        return "✅"
    if status == "FAIL":
        return "❌"
    if status in ["ERROR", "SKIP", "MISS", "DONE", "NULL", None]:
        return "⚠️"


def cmd_tree_report(data, use_json):
    """Parse tree report and print information"""
    if use_json:
        kci_msg_json(data)
        return

    kci_msg_nonl("Tree: ")
    kci_msg_bold(data["dashboard_url"])
    kci_msg(f"Commit: {data['commit_hash']}")
    kci_msg_nonl("Origin: ")
    kci_msg_cyan(data["origin"])
    kci_msg(f"Checkout start time: {data['checkout_start_time']}")
    kci_msg("")

    builds = data["build_status_summary"]
    inconclusive_builds, pass_builds, fail_builds = get_command_summary(builds)

    boots = data["boot_status_summary"]
    inconclusive_boots, pass_boots, fail_boots = get_tree_report_summary(boots)

    tests = data["test_status_summary"]
    inconclusive_tests, pass_tests, fail_tests = get_tree_report_summary(tests)

    kci_msg_bold("Summary: (pass/fail/inconclusive)")
    print_summary("builds", pass_builds, fail_builds, inconclusive_builds)
    print_summary("boots", pass_boots, fail_boots, inconclusive_boots)
    print_summary("tests", pass_tests, fail_tests, inconclusive_tests)
    kci_msg("")

    parsed = urlparse(data["dashboard_url"])
    parsed_dashboard_url = f"{parsed.scheme}://{parsed.netloc}"

    categories = {
        "possible_regressions": "Possible regressions:",
        "fixed_regressions": "Fixed regressions:",
        "unstable_tests": "Unstable tests:",
    }
    for category, name in categories.items():
        if data[category]:
            kci_msg_bold(f"{name}")
        for platform, configs in data[category].items():
            kci_msg_nonl("Platform: ")
            kci_msg_cyan(platform)
            for config, arch_compilers in configs.items():
                kci_msg_nonl("> Config: ")
                kci_msg_cyan(config)
                for arch_compiler, paths in arch_compilers.items():
                    kci_msg_nonl(" - Architecture/compiler: ")
                    kci_msg_cyan(arch_compiler)
                    for path, tests in paths.items():
                        kci_msg_nonl("   - Test path: ")
                        kci_msg_cyan(path)
                        kci_msg(
                            f"   last run: {parsed_dashboard_url}/test/{tests[0]['id']}"
                        )
                        history = []
                        for test in tests:
                            status = status_mapping(test["status"])
                            history.append(status)
                        kci_msg("   history:" + " > ".join(history[::-1]))
                        kci_msg("")

    build_issues = data["issues"]["builds"]
    if build_issues:
        kci_msg_bold("Build issues:")
    for issue in build_issues:
        if issue["is_new_issue"]:
            kci_msg_nonl("- ")
            kci_msg_red("[NEW] ", nl=False)
            kci_msg(f"{parsed_dashboard_url}/issue/{issue.get('issue_id')}")
        else:
            kci_msg(f"- {parsed_dashboard_url}/issue/{issue.get('issue_id')}")

        kci_msg_nonl("  Comment: ")
        kci_msg_cyan(f"{issue.get('comment')}")
        kci_msg(f"  Build: {parsed_dashboard_url}/build/{issue.get('build_id')}")
        kci_msg(f"  version: {issue.get('version')}")
        kci_msg(f"  Report URL: {issue.get('report_url')}")
        kci_msg(f"  First seen: {issue.get('first_seen')}")
        for field in ["culprit_code", "culprit_tool", "culprit_harness"]:
            if not issue.get(field):
                continue
            if issue[field]:
                kci_msg_nonl(f"  {field}: ")
                kci_msg_red(issue[field])
            else:
                kci_msg(f"  {field}: {issue[field]}")
        kci_msg("")
