#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mcp.server.fastmcp import FastMCP

from kcidev.mcp import tools_dashboard, tools_maestro

SERVER_INSTRUCTIONS = """KernelCI MCP server.

Query KernelCI build, boot and test results and known issues from the
web dashboard, inspect Maestro nodes, and, when a token is configured,
retry jobs or trigger custom checkouts. Start with list_trees to
discover tree, branch and commit values, then get_summary for an
overview of a commit's results.
"""


def create_server(cfg=None, instance=None, host="127.0.0.1", port=8000):
    server = FastMCP("kci-dev", instructions=SERVER_INSTRUCTIONS, host=host, port=port)
    tools_dashboard.register_tools(server)
    icfg = (cfg or {}).get(instance) or {}
    tools_maestro.register_tools(
        server, icfg.get("api"), icfg.get("pipeline"), icfg.get("token")
    )
    return server
