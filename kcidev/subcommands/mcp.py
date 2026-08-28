#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import contextlib
import logging
import sys

import click

from kcidev.libs.common import *


@click.command(
    help="""Run an MCP (Model Context Protocol) server exposing KernelCI.

EXPERIMENTAL: tool names, parameters and response formats may change
between releases. Please report any issues at:

\b
https://github.com/kernelci/kci-dev/issues

Read-only dashboard query tools are always available. Maestro node
lookup tools are enabled when the configured instance has an 'api' URL,
and job retry/checkout trigger tools when it also has a 'pipeline' URL
and a token.

Requires the mcp extra: pip install kci-dev[mcp]

\b
Examples:
    kci-dev mcp
    kci-dev --instance production mcp
    kci-dev mcp --transport http --port 8000
"""
)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="MCP transport: stdio for local agents, http for a hosted server",
)
@click.option("--host", default="127.0.0.1", help="Bind address for http transport")
@click.option("--port", default=8000, type=int, help="Port for http transport")
@click.pass_context
def mcp(ctx, transport, host, port):
    try:
        from kcidev.mcp import create_server
    except ImportError:
        kci_err("MCP support is not installed, install with: pip install kci-dev[mcp]")
        raise click.Abort()

    cfg = ctx.obj.get("CFG") or {}
    instance = ctx.obj.get("INSTANCE") or cfg.get("default_instance")
    if instance and instance not in cfg:
        kci_err(f"Instance {instance} not found in config")
        raise click.Abort()
    server = create_server(cfg, instance, host=host, port=port)
    logging.info(
        "Starting MCP server %s",
        "via stdio" if transport == "stdio" else f"on {host}:{port}",
    )
    import anyio

    if transport == "stdio":
        anyio.run(_run_stdio, server)
    else:
        with contextlib.redirect_stdout(sys.stderr):
            server.run(transport="streamable-http")


async def _run_stdio(server):
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        with contextlib.redirect_stdout(sys.stderr):
            await server._mcp_server.run(
                read_stream,
                write_stream,
                server._mcp_server.create_initialization_options(),
            )
