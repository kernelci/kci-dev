#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import errno
import json
import time

import click
import requests

from kcidev.libs.common import *


def maestro_print_api_call(host, data=None):
    kci_info("maestro api endpoint: " + host)
    if data:
        kci_info(json.dumps(data, indent=4))


def maestro_api_error(response):
    kci_err(f"API response error code: {response.status_code}")
    try:
        kci_err(response.json())
    except json.decoder.JSONDecodeError:
        kci_warning(f"No JSON response. Plain text: {response.text}")
    except Exception as e:
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
    maestro_print_api_call(url)
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        kci_err(ex.response.json().get("detail"))
        sys.exit(errno.ENOENT)
    except Exception as ex:
        kci_err(ex)
        sys.exit(errno.ENOENT)

    return response.json()


def maestro_get_nodes(url, limit, offset, filter):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    url = url + "latest/nodes/fast?limit=" + str(limit) + "&offset=" + str(offset)
    maestro_print_api_call(url)
    if filter:
        for f in filter:
            # TBD: We need to add translate filter to API
            # if we need anything more complex than eq(=)
            url = url + "&" + f

    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        kci_err(ex.response.json().get("detail"))
        sys.exit(errno.ENOENT)
    except Exception as ex:
        kci_err(ex)
        sys.exit(errno.ENOENT)

    return response.json()


def maestro_check_node(node):
    """
    Node can be defined RUNNING/DONE/FAIL based on the state
    Simplify, as our current state model suboptimal
    """
    name = node["name"]
    state = node["state"]
    result = node["result"]
    if name == "checkout":
        if state == "running":
            return "RUNNING"
        elif state == "available" or state == "closing":
            return "DONE"
        elif state == "done" and result == "pass":
            return "DONE"
        else:
            return "FAIL"
    else:
        if state == "running":
            return "RUNNING"
        elif state == "done" and (result == "pass" or result == "fail"):
            return "DONE"
        else:
            return "FAIL"


def maestro_retrieve_treeid_nodes(baseurl, token, treeid):
    url = baseurl + "latest/nodes/fast?treeid=" + treeid
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"{token}",
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
    except requests.exceptions.RequestException as e:
        click.secho(f"API connection error: {e}, retrying...", fg="yellow")
        return None
    except Exception as e:
        click.secho(f"API connection error: {e}, retrying...", fg="yellow")
        return None

    if response.status_code >= 400:
        maestro_api_error(response)
        return None

    return response.json()


def maestro_node_result(node):
    result = node["result"]
    if node["kind"] == "checkout":
        if (
            result == "available"
            or result == "closing"
            or result == "done"
            or result == "pass"
        ):
            kci_msg_green_nonl("PASS")
        elif result == None:
            kci_msg_green_nonl("PASS")
        else:
            kci_msg_red_nonl("FAIL")
    else:
        if node["result"] == "pass":
            kci_msg_green_nonl("PASS")
        elif node["result"] == "fail":
            kci_msg_red_nonl("FAIL")
        else:
            kci_msg_yellow_nonl(node["result"])

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
            kci_warning("No nodes found. Retrying...")
            time.sleep(5)
            continue
        if previous_nodes == nodes:
            kci_msg_nonl(".")
            time.sleep(30)
            continue

        time_local = time.localtime()
        kci_info(f"\nCurrent time: {time.strftime('%Y-%m-%d %H:%M:%S', time_local)}")

        # Tricky part in watch is that we might have one item in job_filter (job, test),
        # but it might spawn multiple nodes with same name
        test_result = None
        jobs_done_ts = None
        for node in nodes:
            if node["name"] == test:
                test_result = node["result"]
            if node["name"] in job_filter:
                status = maestro_check_node(node)
                if status == "DONE":
                    if job_info[node["name"]]["running"]:
                        kci_msg("")
                        job_info[node["name"]]["running"] = False
                    if not job_info[node["name"]]["done"]:
                        maestro_node_result(node)
                        job_info[node["name"]]["done"] = True
                    if isinstance(joblist, list) and node["name"] in joblist:
                        joblist.remove(node["name"])
                elif status == "RUNNING":
                    job_info[node["name"]]["running"] = True
                    inprogress += 1
                else:
                    if isinstance(joblist, list) and node["name"] in joblist:
                        joblist.remove(node["name"])
                    # if test is same as job, dont indicate infra-failure if test job fail
                    if test and test != node["name"]:
                        # if we have a test, and prior job failed, we should indicate that
                        kci_err(f"Job {node['name']} failed, test can't be executed")
                        sys.exit(2)
        if isinstance(joblist, list) and len(joblist) == 0 and inprogress == 0:
            kci_info("All jobs completed")
            if not test:
                return
            else:
                if not jobs_done_ts:
                    jobs_done_ts = time.time()
                # if all jobs done, usually test results must be available
                # max within 60s. Safeguard in case of test node is not available
                if not test_result and time.time() - jobs_done_ts < 60:
                    continue

                if test_result and test_result == "pass":
                    sys.exit(0)
                elif test_result:
                    sys.exit(1)

        running = True
        kci_msg_nonl(f"\rRunning job...")
        previous_nodes = nodes
        time.sleep(30)
