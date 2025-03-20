import urllib

import requests

from kcidev.libs.common import *

DASHBOARD_API = "https://dashboard.kernelci.org/api/"


def dashboard_api_fetch(endpoint, params, use_json, max_retries=3):
    base_url = urllib.parse.urljoin(DASHBOARD_API, endpoint)
    url = "{}?{}".format(base_url, urllib.parse.urlencode(params))
    retries = 0

    # Status codes that should trigger a retry
    RETRY_STATUS_CODES = [429, 500, 502, 503, 504, 507]

    while retries <= max_retries:
        try:
            r = requests.get(url)

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
