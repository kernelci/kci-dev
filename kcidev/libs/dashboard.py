import json
import logging
import urllib
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse

import requests

from kcidev.libs.common import *

DASHBOARD_API = "https://dashboard.kernelci.org/api/"
_PARSED_DASHBOARD_API = urlparse(DASHBOARD_API)
DASHBOARD_URL = f"{_PARSED_DASHBOARD_API.scheme}://{_PARSED_DASHBOARD_API.netloc}"


def _dashboard_request(func):
    @wraps(func)
    def wrapper(
        endpoint, params, use_json, body=None, max_retries=3, error_verbose=True
    ):
        base_url = urllib.parse.urljoin(DASHBOARD_API, endpoint)
        url = "{}?{}".format(base_url, urllib.parse.urlencode(params))
        retries = 0

        # Status codes that should trigger a retry
        RETRY_STATUS_CODES = [429, 500, 502, 503, 504, 507]

        logging.info(f"Dashboard API request: {func.__name__} to {endpoint}")
        logging.debug(f"Full URL: {url}")
        if body:
            logging.debug(f"Request body: {json.dumps(body, indent=2)}")

        while retries <= max_retries:
            try:
                logging.debug(f"Attempt {retries + 1}/{max_retries + 1} for {endpoint}")
                r = func(url, params, use_json, body)

                logging.debug(f"Response status code: {r.status_code}")

                if r.status_code in RETRY_STATUS_CODES:
                    retries += 1
                    if retries <= max_retries:
                        logging.warning(
                            f"Retrying request due to status {r.status_code} (attempt {retries}/{max_retries})"
                        )
                        continue
                    else:
                        logging.error(
                            f"Failed after {max_retries} retries with status {r.status_code}"
                        )
                        kci_err(f"Failed after {max_retries} retries with 500 error.")
                        raise click.Abort()

                r.raise_for_status()

                data = r.json()
                logging.debug(f"Response data size: {len(json.dumps(data))} bytes")

                if "error" in data:
                    if error_verbose:
                        logging.error(f"API returned error: {data.get('error')}")
                        if use_json:
                            kci_msg(data)
                        else:
                            kci_msg("json error: " + str(data["error"]))
                    raise click.ClickException(data.get("error"))

                logging.info(f"Successfully completed {func.__name__} request")
                return data

            except requests.exceptions.RequestException as e:
                logging.error(f"Request exception for {endpoint}: {str(e)}")
                kci_err(f"Failed to fetch from {DASHBOARD_API}: {str(e)}.")
                raise click.Abort()

        logging.error("Unexpected failure in API request - exhausted all attempts")
        kci_err("Unexpected failure in API request")
        raise click.Abort()

    return wrapper


@_dashboard_request
def dashboard_api_post(endpoint, params, use_json, body, max_retries=3):
    return requests.post(endpoint, json=body)


@_dashboard_request
def dashboard_api_fetch(endpoint, params, use_json, max_retries=3, error_verbose=True):
    return requests.get(endpoint)


def dashboard_fetch_summary(origin, giturl, branch, commit, arch, use_json):
    endpoint = f"tree/{commit}/summary"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
    }
    if arch is not None:
        params["filter_architecture"] = arch

    logging.info(f"Fetching summary for commit {commit} on {branch} branch")
    logging.debug(f"Parameters: origin={origin}, git_url={giturl}, arch={arch}")
    return dashboard_api_fetch(endpoint, params, use_json)


def dashboard_fetch_commits_history(origin, giturl, branch, commit, use_json):
    """Fetch commit history data from /commits endpoint"""
    endpoint = f"tree/{commit}/commits"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
    }

    logging.info(f"Fetching commit history for commit {commit} on {branch} branch")
    logging.debug(f"Parameters: origin={origin}, git_url={giturl}")
    return dashboard_api_fetch(endpoint, params, use_json)


def dashboard_fetch_builds(
    origin,
    giturl,
    branch,
    commit,
    arch,
    tree,
    start_date,
    end_date,
    use_json,
    error_verbose=True,
):
    endpoint = f"tree/{commit}/builds"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
    }
    if arch is not None:
        params["filter_architecture"] = arch
    if tree is not None:
        params["filter_tree_name"] = tree
    if start_date is not None:
        params["filter_start_date"] = start_date
    if end_date is not None:
        params["filter_end_date"] = end_date

    logging.info(f"Fetching builds for commit {commit} on {branch} branch")
    logging.debug(
        f"Filters: arch={arch}, tree={tree}, start_date={start_date}, end_date={end_date}"
    )
    return dashboard_api_fetch(endpoint, params, use_json, error_verbose=error_verbose)


def dashboard_fetch_boots(
    origin,
    giturl,
    branch,
    commit,
    arch,
    tree,
    start_date,
    end_date,
    use_json,
    boot_origin,
    error_verbose=True,
):
    endpoint = f"tree/{commit}/boots"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
    }
    if arch is not None:
        params["filter_architecture"] = arch
    if tree is not None:
        params["filter_tree_name"] = tree
    if start_date is not None:
        params["filter_start_date"] = start_date
    if end_date is not None:
        params["filter_end_date"] = end_date
    if boot_origin:
        params["filter_boot.origin"] = boot_origin

    logging.info(f"Fetching boots for commit {commit} on {branch} branch")
    logging.debug(
        f"Filters: arch={arch}, tree={tree}, start_date={start_date}, end_date={end_date}"
    )
    return dashboard_api_fetch(endpoint, params, use_json, error_verbose=error_verbose)


def dashboard_fetch_tests(
    origin, giturl, branch, commit, arch, tree, start_date, end_date, use_json
):
    endpoint = f"tree/{commit}/tests"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
    }
    if arch is not None:
        params["filter_architecture"] = arch
    if tree is not None:
        params["filter_tree_name"] = tree
    if start_date is not None:
        params["filter_start_date"] = start_date
    if end_date is not None:
        params["filter_end_date"] = end_date

    logging.info(f"Fetching tests for commit {commit} on {branch} branch")
    logging.debug(
        f"Filters: arch={arch}, tree={tree}, start_date={start_date}, end_date={end_date}"
    )
    return dashboard_api_fetch(endpoint, params, use_json)


def dashboard_fetch_test(test_id, use_json):
    endpoint = f"test/{test_id}"
    logging.info(f"Fetching test details for test ID: {test_id}")
    return dashboard_api_fetch(endpoint, {}, use_json)


def dashboard_fetch_build(build_id, use_json):
    endpoint = f"build/{build_id}"
    logging.info(f"Fetching build details for build ID: {build_id}")
    return dashboard_api_fetch(endpoint, {}, use_json)


def dashboard_fetch_tree_list(origin, use_json, days=7):
    params = {
        "origin": origin,
        "interval_in_days": days,
    }
    logging.info(f"Fetching tree list for origin: {origin}")
    return dashboard_api_fetch("tree", params, use_json)


def dashboard_fetch_hardware_list(origin, use_json):
    # TODO: add date filter
    now = datetime.today()
    last_week = now - timedelta(days=7)
    params = {
        "origin": origin,
        "endTimestampInSeconds": str(int(now.timestamp())),
        "startTimestampInSeconds": str(int(last_week.timestamp())),
    }
    logging.info(f"Fetching hardware list for origin: {origin}")
    logging.debug(
        f"Date range: {last_week.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"
    )
    return dashboard_api_fetch("hardware/", params, use_json)


def _create_hardware_request_body(origin):
    now = datetime.today()
    last_week = now - timedelta(days=7)
    body = {
        "origin": origin,
        "endTimestampInSeconds": str(int(now.timestamp())),
        "startTimestampInSeconds": str(int(last_week.timestamp())),
        "selectedCommits": {},
        "filter": {},
    }
    return body


def dashboard_fetch_hardware_summary(name, origin, use_json):
    # TODO: add extra filters: Commits, date, filter, origin
    body = _create_hardware_request_body(origin)
    logging.info(f"Fetching hardware summary for: {name} (origin: {origin})")
    return dashboard_api_post(
        f"hardware/{urllib.parse.quote_plus(name)}/summary", {}, use_json, body
    )


def dashboard_fetch_hardware_boots(name, origin, use_json):
    body = _create_hardware_request_body(origin)
    logging.info(f"Fetching hardware boots for: {name} (origin: {origin})")
    return dashboard_api_post(
        f"hardware/{urllib.parse.quote_plus(name)}/boots", {}, use_json, body
    )


def dashboard_fetch_hardware_builds(name, origin, use_json):
    body = _create_hardware_request_body(origin)
    logging.info(f"Fetching hardware builds for: {name} (origin: {origin})")
    return dashboard_api_post(
        f"hardware/{urllib.parse.quote_plus(name)}/builds", {}, use_json, body
    )


def dashboard_fetch_hardware_tests(name, origin, use_json):
    body = _create_hardware_request_body(origin)
    logging.info(f"Fetching hardware tests for: {name} (origin: {origin})")
    return dashboard_api_post(
        f"hardware/{urllib.parse.quote_plus(name)}/tests", {}, use_json, body
    )


def dashboard_fetch_build_issues(build_id, use_json, error_verbose):
    endpoint = f"build/{build_id}/issues"
    logging.info(f"Fetching build issues for build ID: {build_id}")
    return dashboard_api_fetch(endpoint, {}, use_json, error_verbose=error_verbose)


def dashboard_fetch_boot_issues(test_id, use_json, error_verbose):
    endpoint = f"test/{test_id}/issues"
    logging.info(f"Fetching test issues for test ID: {test_id}")
    return dashboard_api_fetch(endpoint, {}, use_json, error_verbose=error_verbose)


def dashboard_fetch_issue_list(origin, days, use_json):
    params = {
        "interval_in_days": days,
    }
    if origin:
        params["filter_origin"] = origin
    logging.info(f"Fetching issue list for origin: {origin}")
    return dashboard_api_fetch("issue/", params, use_json)


def dashboard_fetch_issue(issue_id, use_json):
    logging.info(f"Fetching issue details for issue ID: {issue_id}")
    return dashboard_api_fetch(f"issue/{issue_id}", {}, use_json)


def dashboard_fetch_issue_builds(origin, issue_id, use_json, error_verbose=True):
    logging.info(f"Fetching builds for issue ID: {issue_id}")
    params = {"filter_origin": origin} if origin else {}
    return dashboard_api_fetch(
        f"issue/{issue_id}/builds", params, use_json, error_verbose=error_verbose
    )


def dashboard_fetch_issue_tests(origin, issue_id, use_json, error_verbose=True):
    logging.info(f"Fetching tests for issue ID: {issue_id}")
    params = {"filter_origin": origin} if origin else {}
    return dashboard_api_fetch(
        f"issue/{issue_id}/tests", params, use_json, error_verbose=error_verbose
    )


def dashboard_fetch_issues_extra(issues, use_json):
    """Send POST request to "issues/extras/" endpoint
    Request body parameter "issues" should be a list containing sub-lists
    with issue ID and version.
    for example:
        [
            ['maestro:11568c8c555164d721a425c3ee264932a87e9113',1],
            ['maestro:2779a206c30e0ec91f19f1df949c1b9d65fe1238',1]
        ]
    """
    body = {"issues": issues}
    return dashboard_api_post("issue/extras/", {}, use_json, body)


def dashboard_fetch_tree_report(
    origin,
    git_branch,
    git_url,
    use_json,
    test_path,
    history_size,
    max_age_in_hours,
    min_age_in_hours,
):
    """Get tree report"""
    params = [
        ("origin", origin),
        ("git_branch", git_branch),
        ("git_url", git_url),
        ("group_size", history_size),
        ("max_age_in_hours", max_age_in_hours),
        ("min_age_in_hours", min_age_in_hours),
    ]
    for path in test_path:
        params.append(("path", path))

    logging.info(f"Fetching tree report for origin: {origin}")
    return dashboard_api_fetch("tree-report", params, use_json)
