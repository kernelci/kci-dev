+++
title = 'mcp'
date = 2026-07-01T00:00:00+00:00
description = 'Run an MCP server exposing KernelCI data and actions to AI agents.'
+++

This command runs an MCP (Model Context Protocol) server so AI agents and
automation tools can query KernelCI results and drive Maestro jobs.

> **Experimental**: tool names, parameters and response formats may
> change between releases. Please report any issues on the
> [issue tracker](https://github.com/kernelci/kci-dev/issues).

MCP support is an optional extra:

```sh
pip install kci-dev[mcp]
```

Read-only dashboard query tools (trees, builds, boots, tests, logs,
hardware, known issues) are always available and need no configuration.
Maestro
node lookup tools are enabled when the configured instance has an `api`
URL, and job retry/checkout trigger tools when it also has a `pipeline`
URL and a `token`. See the [config file](../config_file.md) documentation.
Use the top-level `--instance` option (`kci-dev --instance staging mcp`) to
select which configured instance the server uses.

Run with the default stdio transport for local agents:

```sh
kci-dev mcp
```

Example Claude Code registration:

```sh
claude mcp add kernelci -- kci-dev mcp
```

Run as an HTTP server (streamable HTTP transport):

```sh
kci-dev mcp --transport http --host 127.0.0.1 --port 8000
```

The HTTP transport has no authentication layer: anyone who can reach the
port can call the exposed tools, including the job-triggering ones, using
the token from your configuration. Keep it bound to 127.0.0.1, prefer the
stdio transport for local use, and do not expose the port beyond hosts you
trust.

Tools that change state (`retry_job`, `trigger_checkout`) are annotated
as non-read-only so MCP clients can ask for confirmation before calling
them.

Responses are sized for context-limited clients: `get_summary` returns
compact aggregates unless `detail=true` is passed, and the list tools
paginate (default `limit` of 20) and accept a `fields` list to return
only the named keys per entry. Prefer `status`/`arch` filters, small
limits and field projection when exploring large trees.

## Querying a single lab

To look at one lab (test runtime) rather than a whole tree, start from
`list_labs`, which returns the labs reporting to KernelCI with their
build, boot and test counts for the last N days. Those names are then
usable as:

- the `lab` filter of `list_builds`, `list_boots` and `list_tests`,
  which narrows a commit's results to that lab;
- the `data.runtime` filter of `list_nodes`, for example
  `list_nodes(filters=["kind=job", "data.runtime=lava-collabora",
  "data.platform__re=^qcom"])`. Maestro applies this filter server-side,
  so it is the cheapest way to ask what one lab is doing with a family
  of boards.

For the status of a lab rather than its individual results, `get_summary`
and `get_hardware_summary` both carry a per-lab breakdown of pass/fail
counts under `summary.<section>.labs`, which answers "how is this tree or
platform doing in lab X" in a single call.

The dashboard has no server-side lab filter, so the `lab` option of the
list tools is applied to the fetched page after the request. It shrinks
the response, not the query: `total` counts entries before filtering and
`matched` after.

## Analytics logging

The server writes newline-delimited JSON analytics to stderr by default,
without requiring `--debug`. To collect analytics in a separate file:

```sh
kci-dev mcp --transport http --log-file /var/log/kci-dev-mcp.jsonl
```

The file is opened in append mode; its parent directory must exist and be
writable. File rotation and retention are managed externally. Other diagnostic
messages continue to use stderr, and stdio protocol output stays on stdout.

Each `tool_call` event includes a UTC `timestamp`, a generated unique `call_id`,
`tool`, configured `instance` (or null), `outcome` (`success`, `error`, or
`cancelled`), and `duration_ms`. Duration covers validation and tool execution.
Invalid arguments and unknown tools count as errors. These records support
tool usage counts, error rates, and latency percentiles. Calls are logged when
they finish; a process killed abruptly cannot log its unfinished calls.

`server_start` and `server_stop` events include the transport and instance.
Analytics records omit arguments, results, credentials, and exception messages.
This does not change the contents of existing diagnostic logs. When embedding
`create_server()` in Python, configure the `kcidev.mcp.analytics` logger at INFO
to collect the tool events through your application's logging setup.
