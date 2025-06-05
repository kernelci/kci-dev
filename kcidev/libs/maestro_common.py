#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import errno
import json
import logging
import time

import click
import requests

from kcidev.libs.common import *


def maestro_print_api_call(host, data=None):
    kci_info("maestro api endpoint: " + host)
    if data:
        kci_info(json.dumps(data, indent=4))


def maestro_api_error(response):
    logging.error(
        f"Maestro API error - Status: {response.status_code}, URL: {response.url}"
    )
    kci_err(f"API response error code: {response.status_code}")
    try:
        error_data = response.json()
        logging.error(f"API error response: {json.dumps(error_data, indent=2)}")
        kci_err(response.json())
    except json.decoder.JSONDecodeError:
        logging.warning(f"No JSON in error response: {response.text}")
        kci_warning(f"No JSON response. Plain text: {response.text}")
    except Exception as e:
        logging.error(f"Error parsing API response: {e}")
        kci_err(f"API response error: {e}: {response.text}")
    return


def maestro_print_nodes(nodes, field):
    res = []
    if not isinstance(nodes, list):
        nodes = [nodes]
    for node in nodes:
        if field:
            data = {}
            for f in field:
                data[f] = node.get(f)
            res.append(data)
        else:
            res.append(node)
        kci_msg(json.dumps(res, sort_keys=True, indent=4))


def maestro_get_node(url, nodeid):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    url = url + "latest/node/" + nodeid
    logging.info(f"Fetching Maestro node: {nodeid}")
    logging.debug(f"Node URL: {url}")
    maestro_print_api_call(url)

    try:
        response = requests.get(url, headers=headers)
        logging.debug(f"Node request status: {response.status_code}")
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        logging.error(f"HTTP error fetching node {nodeid}: {ex}")
        kci_err(ex.response.json().get("detail"))
        sys.exit(errno.ENOENT)
    except Exception as ex:
        logging.error(f"Unexpected error fetching node {nodeid}: {ex}")
        kci_err(ex)
        sys.exit(errno.ENOENT)

    node_data = response.json()
    logging.debug(
        f"Node {nodeid} data received, state: {node_data.get('state', 'unknown')}"
    )
    return node_data


def maestro_get_nodes(url, limit, offset, filter, paginate):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }

    if paginate:
        url = url + "latest/nodes/fast?limit=" + str(limit) + "&offset=" + str(offset)
        logging.info(f"Fetching Maestro nodes - limit: {limit}, offset: {offset}")
        if filter:
            for f in filter:
                logging.debug(f"Applying filters: {filter}")
                # TBD: We need to add translate filter to API
                # if we need anything more complex than eq(=)
                url = url + "&" + f

    else:
        url = url + "latest/nodes/fast"
        if filter:
            url = url + "?"
            for f in filter:
                # TBD: We need to add translate filter to API
                # if we need anything more complex than eq(=)
                url = url + "&" + f
    logging.debug(f"Full nodes URL: {url}")
    maestro_print_api_call(url)

    try:
        response = requests.get(url, headers=headers)
        logging.debug(f"Nodes request status: {response.status_code}")
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        logging.error(f"HTTP error fetching nodes: {ex}")
        kci_err(ex.response.json().get("detail"))
        sys.exit(errno.ENOENT)
    except Exception as ex:
        logging.error(f"Unexpected error fetching nodes: {ex}")
        kci_err(ex)
        sys.exit(errno.ENOENT)

    nodes_data = response.json()
    logging.info(f"Retrieved {len(nodes_data)} nodes")
    return nodes_data


def maestro_check_node(node):
    """
    Node can be defined RUNNING/DONE/FAIL based on the state
    Simplify, as our current state model suboptimal
    """
    name = node["name"]
    state = node["state"]
    result = node["result"]

    logging.debug(
        f"Checking node status - name: {name}, state: {state}, result: {result}"
    )

    if name == "checkout":
        if state == "running":
            status = "RUNNING"
        elif state == "available" or state == "closing":
            status = "DONE"
        elif state == "done" and result == "pass":
            status = "DONE"
        else:
            status = "FAIL"
    else:
        if state == "running":
            status = "RUNNING"
        elif state == "done" and (result == "pass" or result == "fail"):
            status = "DONE"
        else:
            status = "FAIL"

    logging.debug(f"Node {name} status determined: {status}")
    return status


def maestro_retrieve_treeid_nodes(baseurl, token, treeid):
    url = baseurl + "latest/nodes/fast?treeid=" + treeid
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"{token}",
    }

    logging.info(f"Retrieving nodes for tree ID: {treeid}")
    logging.debug(f"Tree nodes URL: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        logging.debug(f"Tree nodes request status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.warning(f"Request exception retrieving tree nodes: {e}")
        click.secho(f"API connection error: {e}, retrying...", fg="yellow")
        return None
    except Exception as e:
        logging.error(f"Unexpected error retrieving tree nodes: {e}")
        click.secho(f"API connection error: {e}, retrying...", fg="yellow")
        return None

    if response.status_code >= 400:
        logging.error(f"API error response for tree {treeid}: {response.status_code}")
        maestro_api_error(response)
        return None

    nodes = response.json()
    logging.info(f"Retrieved {len(nodes)} nodes for tree {treeid}")
    return nodes


def maestro_node_result(node):
    result = node["result"]
    if node["kind"] == "checkout":
        if (
            result == "available"
            or result == "closing"
            or result == "done"
            or result == "pass"
        ):
            kci_msg_green("PASS", nl=False)
        elif result == None:
            kci_msg_green("PASS", nl=False)
        else:
            kci_msg_red("FAIL", nl=False)
    else:
        if node["result"] == "pass":
            kci_msg_green("PASS", nl=False)
        elif node["result"] == "fail":
            kci_msg_red("FAIL", nl=False)
        else:
            kci_msg_yellow(node["result"])

    if node["kind"] == "checkout":
        kci_msg_nonl(" branch checkout")
    else:
        kci_msg_nonl(f" {node['kind']}: ")

    if node["kind"] != "checkout":
        kci_msg_nonl(f"{node['name']}")

    kci_msg(f" - node_id:{node['id']} ({node['updated']})")


def maestro_watch_jobs(baseurl, token, treeid, job_filter, test):
    # we need to add to job_filter "checkout" node
    job_filter = list(job_filter)
    job_filter.append("checkout")
    kci_log(f"job_filter: {', '.join(job_filter)}")
    logging.info(f"Starting job watch for tree {treeid}")
    logging.debug(f"Watching jobs: {job_filter}, test: {test}")
    previous_nodes = None
    running = False

    job_info = {}
    for job in job_filter:
        job_info[job] = {"done": False, "running": False}

    while True:
        inprogress = 0
        joblist = job_filter.copy()
        nodes = maestro_retrieve_treeid_nodes(baseurl, token, treeid)
        if not nodes:
            logging.warning("No nodes found for tree, will retry")
            kci_warning("No nodes found. Retrying...")
            time.sleep(5)
            continue
        if previous_nodes == nodes:
            logging.debug("No changes in nodes, waiting...")
            kci_msg_nonl(".")
            time.sleep(30)
            continue

        time_local = time.localtime()
        kci_info(f"\nCurrent time: {time.strftime('%Y-%m-%d %H:%M:%S', time_local)}")

        # Tricky part in watch is that we might have one item in job_filter (job, test),
        # but it might spawn multiple nodes with same name
        test_result = None
        jobs_done_ts = None
        logging.debug(f"Processing {len(nodes)} nodes")
        for node in nodes:
            if node["name"] == test:
                test_result = node["result"]
                logging.debug(f"Test node {test} result: {test_result}")
            if node["name"] in job_filter:
                status = maestro_check_node(node)
                if status == "DONE":
                    if job_info[node["name"]]["running"]:
                        kci_msg("")
                        job_info[node["name"]]["running"] = False
                    if not job_info[node["name"]]["done"]:
                        logging.info(
                            f"Job {node['name']} completed with result: {node['result']}"
                        )
                        maestro_node_result(node)
                        job_info[node["name"]]["done"] = True
                    if isinstance(joblist, list) and node["name"] in joblist:
                        joblist.remove(node["name"])
                elif status == "RUNNING":
                    logging.debug(f"Job {node['name']} is running")
                    job_info[node["name"]]["running"] = True
                    inprogress += 1
                else:
                    logging.warning(f"Job {node['name']} failed with status: {status}")
                    if isinstance(joblist, list) and node["name"] in joblist:
                        joblist.remove(node["name"])
                    # if test is same as job, dont indicate infra-failure if test job fail
                    if test and test != node["name"]:
                        # if we have a test, and prior job failed, we should indicate that
                        logging.error(
                            f"Job {node['name']} failed, test cannot be executed"
                        )
                        kci_err(f"Job {node['name']} failed, test can't be executed")
                        sys.exit(2)
        if isinstance(joblist, list) and len(joblist) == 0 and inprogress == 0:
            logging.info(
                f"All jobs completed. Remaining in queue: {len(joblist)}, in progress: {inprogress}"
            )
            kci_info("All jobs completed")
            if not test:
                return
            else:
                if not jobs_done_ts:
                    jobs_done_ts = time.time()
                    logging.debug("All jobs done, waiting for test results")
                # if all jobs done, usually test results must be available
                # max within 60s. Safeguard in case of test node is not available
                if not test_result and time.time() - jobs_done_ts < 60:
                    logging.debug(
                        f"Waiting for test results ({int(time.time() - jobs_done_ts)}s elapsed)"
                    )
                    continue

                if test_result and test_result == "pass":
                    logging.info(f"Test {test} passed")
                    sys.exit(0)
                elif test_result:
                    logging.info(f"Test {test} failed with result: {test_result}")
                    sys.exit(1)

        running = True
        kci_msg_nonl(f"\rRunning job...")
        previous_nodes = nodes
        time.sleep(30)
