import json
import urllib
from datetime import datetime, timedelta
from functools import wraps

import requests

from kcidev.libs.common import *

DASHBOARD_API = "https://dashboard.kernelci.org/api/"


def _dashboard_request(func):
    @wraps(func)
    def wrapper(endpoint, params, use_json, body=None, max_retries=3):
        base_url = urllib.parse.urljoin(DASHBOARD_API, endpoint)
        url = "{}?{}".format(base_url, urllib.parse.urlencode(params))
        retries = 0

        # Status codes that should trigger a retry
        RETRY_STATUS_CODES = [429, 500, 502, 503, 504, 507]

        while retries <= max_retries:
            try:
                r = func(url, params, use_json, body)
                if r.status_code in RETRY_STATUS_CODES:
                    retries += 1
                    if retries <= max_retries:
                        continue
                    else:
                        kci_err(f"Failed after {max_retries} retries with 500 error.")
                        raise click.Abort()

                r.raise_for_status()

                data = r.json()
                if "error" in data:
                    if use_json:
                        kci_msg(data)
                    else:
                        kci_msg("json error: " + str(data["error"]))
                    raise click.Abort()
                return data

            except requests.exceptions.RequestException as e:
                kci_err(f"Failed to fetch from {DASHBOARD_API}: {str(e)}.")
                raise click.Abort()

        kci_err("Unexpected failure in API request")
        raise click.Abort()

    return wrapper


@_dashboard_request
def dashboard_api_post(endpoint, params, use_json, body, max_retries=3):
    return requests.post(endpoint, json=body)


@_dashboard_request
def dashboard_api_fetch(endpoint, params, use_json, max_retries=3):
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
    return dashboard_api_fetch(endpoint, params, use_json)


def dashboard_fetch_builds(origin, giturl, branch, commit, arch, use_json):
    endpoint = f"tree/{commit}/builds"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
    }
    if arch is not None:
        params["filter_architecture"] = arch
    return dashboard_api_fetch(endpoint, params, use_json)


def dashboard_fetch_boots(origin, giturl, branch, commit, arch, use_json):
    endpoint = f"tree/{commit}/boots"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
    }
    if arch is not None:
        params["filter_architecture"] = arch
    return dashboard_api_fetch(endpoint, params, use_json)


def dashboard_fetch_tests(origin, giturl, branch, commit, arch, use_json):
    endpoint = f"tree/{commit}/tests"
    params = {
        "origin": origin,
        "git_url": giturl,
        "git_branch": branch,
    }
    if arch is not None:
        params["filter_architecture"] = arch
    return dashboard_api_fetch(endpoint, params, use_json)


def dashboard_fetch_test(test_id, use_json):
    endpoint = f"test/{test_id}"
    return dashboard_api_fetch(endpoint, {}, use_json)


def dashboard_fetch_build(build_id, use_json):
    endpoint = f"build/{build_id}"
    return dashboard_api_fetch(endpoint, {}, use_json)


def dashboard_fetch_tree_list(origin, use_json):
    params = {
        "origin": origin,
    }
    return dashboard_api_fetch("tree-fast", params, use_json)


def dashboard_fetch_hardware_list(origin, use_json):
    # TODO: add date filter
    now = datetime.today()
    last_week = now - timedelta(days=7)
    params = {
        "origin": origin,
        "endTimeStampInSeconds": int(now.timestamp()),
        "startTimestampInSeconds": int(last_week.timestamp()),
    }
    return dashboard_api_fetch("hardware/", params, use_json)


def dashboard_fetch_hardware_summary(name, origin, use_json):
    # TODO: add extra filters: Commits, date, filter, origin
    now = datetime.today()
    last_week = now - timedelta(days=7)
    body = {
        "origin": origin,
        "endTimestampInSeconds": str(int(now.timestamp())),
        "startTimestampInSeconds": str(int(last_week.timestamp())),
        "selectedCommits": {},
        "filter": {},
    }
    return dashboard_api_post(
        f"hardware/{urllib.parse.quote_plus(name)}/summary", {}, use_json, body
    )
