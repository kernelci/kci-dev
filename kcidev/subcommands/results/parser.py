import gzip
import json

import requests
import yaml
from libs.dashboard import dashboard_fetch_tree_list
from libs.files import download_logs_to_file

from kcidev.libs.common import *


def print_summary(type, n_pass, n_fail, n_inconclusive):

    kci_msg_nonl(f"{type}:\t")
    kci_msg_green_nonl(f"{n_pass}") if n_pass else kci_msg_nonl(f"{n_pass}")
    kci_msg_nonl("/")
    kci_msg_red_nonl(f"{n_fail}") if n_fail else kci_msg_nonl(f"{n_fail}")
    kci_msg_nonl("/")
    (
        kci_msg_yellow_nonl(f"{n_inconclusive}")
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


def cmd_list_trees(origin, use_json):
    trees = dashboard_fetch_tree_list(origin)
    if use_json:
        kci_msg(json.dumps(list(map(lambda t: create_tree_json(t), trees))))
        return
    for t in trees:
        kci_msg_green_nonl(f"- {t['tree_name']}/{t['git_repository_branch']}:\n")
        kci_msg(f"  giturl: {t['git_repository_url']}")
        kci_msg(f"  latest: {t['git_commit_hash']} ({t['git_commit_name']})")
        kci_msg(f"  latest: {t['start_time']}")


def cmd_builds(data, commit, download_logs, status, count, use_json):
    if status == "inconclusive" and use_json:
        kci_msg('{"message":"No information about inconclusive builds."}')
        return
    elif status == "inconclusive":
        kci_msg("No information about inconclusive builds.")
        return
    filtered_builds = 0
    builds = []
    for build in data["builds"]:
        if not status == "all":
            if build["status"] != "FAIL" and status == "fail":
                continue

            if build["status"] != "PASS" and status == "pass":
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
    kci_msg_cyan_nonl(build["config_name"])
    kci_msg_nonl(" arch: ")
    kci_msg_cyan_nonl(build["architecture"])
    kci_msg_nonl(" compiler: ")
    kci_msg_cyan_nonl(build["compiler"])
    kci_msg("")

    kci_msg_nonl("  status:")
    if build["status"] == "PASS":
        kci_msg_green_nonl("PASS")
    elif build["status"] == "FAIL":
        kci_msg_red_nonl("FAIL")
    else:
        kci_msg_yellow_nonl(f"INCONCLUSIVE (status: {build['status']})")
    kci_msg("")

    kci_msg(f"  config_url: {build['config_url']}")
    kci_msg(f"  log: {log_path}")
    kci_msg(f"  id: {build['id']}")
    kci_msg(f"  dashboard: https://dashboard.kernelci.org/build/{build['id']}")
    kci_msg("")


def filter_out_by_status(status, filter):
    if filter == "all":
        return False

    if filter == status.lower():
        return False

    elif filter == "inconclusive" and status in [
        "ERROR",
        "SKIP",
        "MISS",
        "DONE",
        "NULL",
    ]:
        return False

    return True


def filter_out_by_hardware(test, filter_data):
    # Check if the hardware name is in the list
    hardware_list = filter_data["hardware"]
    if test["environment_misc"]["platform"] in hardware_list:
        return False

    if test["environment_compatible"]:
        for compatible in test["environment_compatible"]:
            if compatible in hardware_list:
                return False

    return True


def filter_out_by_test(test, filter_data):
    # Check if the test name is in the list
    test_list = filter_data["test"]
    if test["path"] in test_list:
        return False

    return True


def cmd_tests(data, commit, download_logs, status_filter, filter, count, use_json):
    filter_data = yaml.safe_load(filter) if filter else None
    filtered_tests = 0
    tests = []
    for test in data:
        if filter_out_by_status(test["status"], status_filter):
            continue

        if filter_data and filter_out_by_hardware(test, filter_data):
            continue

        if filter_data and filter_out_by_test(test, filter_data):
            continue

        log_path = test["log_url"]
        if download_logs:
            platform = (
                test["environment_misc"]["platform"]
                if "environment_misc" in test
                else "(Unknown platform)"
            )
            log_file = f"{platform}__{test['path']}__{test['config']}-{test['architecture']}-{test['compiler']}-{commit}.log"
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
    kci_msg_cyan_nonl(test["path"])
    kci_msg("")

    kci_msg_nonl("  hardware: ")
    kci_msg_cyan_nonl(test["environment_misc"]["platform"])
    kci_msg("")

    if test["environment_compatible"]:
        kci_msg_nonl("  compatibles: ")
        kci_msg_cyan_nonl(" | ".join(test["environment_compatible"]))
        kci_msg("")

    kci_msg_nonl("  config: ")
    if "config" in test:
        kci_msg_cyan_nonl(test["config"])
    elif "config_name" in test:
        kci_msg_cyan_nonl(test["config_name"])
    else:
        kci_msg_cyan_nonl("No config available")
    kci_msg_nonl(" arch: ")
    kci_msg_cyan_nonl(test["architecture"])
    kci_msg_nonl(" compiler: ")
    kci_msg_cyan_nonl(test["compiler"])
    kci_msg("")

    kci_msg_nonl("  status:")
    if test["status"] == "PASS":
        kci_msg_green_nonl("PASS")
    elif test["status"] == "FAIL":
        kci_msg_red_nonl("FAIL")
    else:
        kci_msg_yellow_nonl(f"INCONCLUSIVE (status: {test['status']})")
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
            kci_msg_cyan_nonl(hardware["hardware_name"])
            kci_msg("")

            kci_msg_nonl("  compatibles: ")
            kci_msg_cyan_nonl(hardware["platform"])
            kci_msg("")
            kci_msg("")
