#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click

from kcidev.libs.common import *


@click.command(
    help="""Run an MCP (Model Context Protocol) server exposing KernelCI.

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
    server.run(transport="stdio" if transport == "stdio" else "streamable-http")
