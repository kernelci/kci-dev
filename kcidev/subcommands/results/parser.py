import gzip
import json
import re

import requests
import yaml

from kcidev.libs.common import *
from kcidev.libs.dashboard import dashboard_fetch_tree_list
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
    kci_msg_green(f"{n_pass}") if n_pass else kci_msg_nonl(f"{n_pass}", nl=False)
    kci_msg_nonl("/")
    kci_msg_red(f"{n_fail}") if n_fail else kci_msg_nonl(f"{n_fail}", nl=False)
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
        "dashboard": f"https://dashboard.kernelci.org/build/{build['id']}",
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
    return {
        "test_path": test["path"],
        "hardware": test["environment_misc"]["platform"],
        "compatibles": test.get("environment_compatible", []),
        "config": config_name,
        "arch": test["architecture"],
        "status": test_status,
        "start_time": test["start_time"],
        "log": log_path,
        "id": test["id"],
        "dashboard": f"https://dashboard.kernelci.org/build/{test['id']}",
    }


def cmd_summary(data, use_json):
    summary = data["summary"]

    builds = summary["builds"]["status"]
    inconclusive_builds, pass_builds, fail_builds = get_command_summary(builds)

    boots = summary["boots"]["status"]
    inconclusive_boots, pass_boots, fail_boots = get_command_summary(boots)

    tests = summary["tests"]["status"]
    inconclusive_tests, pass_tests, fail_tests = get_command_summary(tests)

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


def cmd_list_trees(origin, use_json, days):
    trees = dashboard_fetch_tree_list(origin, use_json, days)
    if use_json:
        kci_msg(json.dumps(list(map(lambda t: create_tree_json(t), trees))))
        return
    for t in trees:
        kci_msg_green(f"- {t['tree_name']}/{t['git_repository_branch']}:")
        kci_msg(f"  giturl: {t['git_repository_url']}")
        kci_msg(f"  latest: {t['git_commit_hash']} ({t['git_commit_name']})")
        kci_msg(f"  latest: {t['start_time']}")


def cmd_builds(
    data, commit, download_logs, status, compiler, config, git_branch, count, use_json
):
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

    filtered_builds = 0
    builds = []
    for build in data["builds"]:
        if not filter_set.matches(build):
            continue

        log_path = build["log_url"]
        if download_logs:
            try:
                log_file = f"{build['config_name']}-{build['architecture']}-{build['compiler']}-{commit}.log"
                log_path = download_logs_to_file(build["log_url"], log_file)
            except:
                kci_err(f"Failed to fetch log {build['log_url']}.")
                pass
        if count:
            filtered_builds += 1
        elif use_json:
            builds.append(create_build_json(build, log_path))
        else:
            print_build(build, log_path)
    if count and use_json:
        kci_msg(f'{{"count":{filtered_builds}}}')
    elif count:
        kci_msg(filtered_builds)
    elif use_json:
        kci_msg(json.dumps(builds))


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
    kci_msg(f"  dashboard: https://dashboard.kernelci.org/build/{build['id']}")
    kci_msg("")


# Legacy filter functions have been replaced by the unified filter system
# See kcidev.libs.filters for the new implementation


def filter_array2regex(filter_array):
    return f"^({'|'.join(filter_array)})$".replace(".", r"\.").replace("*", ".*")


def parse_filter_file(filter):
    filter_data = yaml.safe_load(filter) if filter else None
    if filter_data is None:
        return None
    parsed_filter = {}
    if "hardware" in filter_data:
        parsed_filter["hardware"] = filter_array2regex(filter_data["hardware"])
    if "test" in filter_data:
        parsed_filter["test"] = filter_array2regex(filter_data["test"])
    if "tree" in filter_data:
        parsed_filter["tree"] = filter_array2regex(filter_data["tree"])
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
):
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
            log_path = download_logs_to_file(test["log_url"], log_file)
        if count:
            filtered_tests += 1
        elif use_json:
            tests.append(create_test_json(test, log_path))
        else:
            print_test(test, log_path)
    if count and use_json:
        kci_msg(f'{{"count":{filtered_tests}}}')
    elif count:
        kci_msg(filtered_tests)
    elif use_json:
        kci_msg(json.dumps(tests))


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
    kci_msg(f"  id: {test['id']}")
    kci_msg(f"  dashboard: https://dashboard.kernelci.org/test/{test['id']}")
    kci_msg("")


def cmd_single_test(test, download_logs, use_json):
    log_path = test["log_url"]
    if download_logs:
        log_file = f"{test['environment_misc']['platform']}__{test['path']}__{test['config_name']}-{test['architecture']}-{test['compiler']}-{test['id']}.log"
        log_path = download_logs_to_file(test["log_url"], log_file)
    if use_json:
        kci_msg(create_test_json(test, log_path))
    else:
        print_test(test, log_path)


def cmd_single_build(build, download_logs, use_json):
    log_path = build["log_url"]
    if download_logs:
        log_file = log_file = (
            f"{build['config_name']}-{build['architecture']}-{build['compiler']}-{build['git_commit_hash']}-{build['id']}.log"
        )
        log_path = download_logs_to_file(build["log_url"], log_file)
    if use_json:
        kci_msg(create_build_json(build, log_path))
    else:
        print_build(build, log_path)


def cmd_hardware_list(data, use_json):
    if use_json:
        hardware = [
            {"name": hardware["hardware_name"], "compatibles": hardware["platform"]}
            for hardware in data["hardware"]
        ]
        kci_msg(hardware)
    else:
        for hardware in data["hardware"]:
            kci_msg_nonl("- name: ")
            kci_msg_cyan(hardware["hardware_name"], nl=False)
            kci_msg("")

            kci_msg_nonl("  compatibles: ")
            kci_msg_cyan(hardware["platform"], nl=False)
            kci_msg("")
            kci_msg("")
