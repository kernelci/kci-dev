#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

import click

from kcidev.libs.common import kci_msg, kci_msg_cyan, kci_msg_green, kci_msg_nonl
from kcidev.libs.maestro_common import maestro_get_nodes
from kcidev.subcommands.maestro.results import results
from kcidev.subcommands.maestro.validate import validate


@click.group(
    help="""Maestro-specific commands for interacting with KernelCI's Maestro API.

This command group provides access to various Maestro operations including
querying test results and in the future will include other maestro-specific
commands.

\b
Examples:
  # Query test results
  kci-dev maestro results --nodeid <NODE_ID>
  kci-dev maestro results --nodes --limit 10
""",
    invoke_without_command=True,
)
@click.pass_context
def maestro(ctx):
    """Maestro-specific commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        sys.exit(0)


def print_bar_graph(data):
    """Create bar graph for coverage data"""

    import math
    import webbrowser

    import matplotlib.pyplot as plt
    import mplcursors
    import numpy as np

    # Calculate for subplots layout (one subplot per branch)
    branches = list(data.keys())
    num_branches = len(branches)
    ncols = 2
    nrows = math.ceil(num_branches / ncols)

    # Generate grid for subplots
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(16, 5 * nrows), constrained_layout=True
    )
    axes = axes.flatten()

    all_bars = []

    for i, branch in enumerate(branches):
        ax = axes[i]
        coverage_data = data[branch]

        full_commit_ids = [entry["commit"] for entry in coverage_data]
        short_commit_ids = [c[:6] for c in full_commit_ids]  # truncate to 6 chars

        func_coverage = [entry["function_coverage"] for entry in coverage_data]
        line_coverage = [entry["line_coverage"] for entry in coverage_data]

        # Create position on x-axis
        x = np.arange(len(short_commit_ids))
        # Width of bar
        width = 0.35

        # Create function coverage bar
        func_bars = ax.bar(
            x - width / 2,
            func_coverage,
            width,
            label="Function Coverage",
            color="royalblue",
        )

        # Create line coverage bar
        line_bars = ax.bar(
            x + width / 2, line_coverage, width, label="Line Coverage", color="orange"
        )

        for idx, bar in enumerate(func_bars):
            bar.commit_id = full_commit_ids[idx]
            bar.coverage_report_url = coverage_data[idx]["coverage_report_url"]
            all_bars.append(bar)

        for idx, bar in enumerate(line_bars):
            bar.commit_id = full_commit_ids[idx]
            bar.coverage_report_url = coverage_data[idx]["coverage_report_url"]
            all_bars.append(bar)

        ax.set_title(f"Coverage for {branch}", fontsize=14)
        ax.set_xlabel("Commit ID")
        ax.set_ylabel("Coverage (%)")
        ax.set_xticks(x)
        ax.set_xticklabels(short_commit_ids, rotation=0, ha="center", fontsize=9)
        ax.set_ylim(0, max(func_coverage + line_coverage) + 5)
        ax.legend()

        def add_labels(bars):
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 0.5,
                    f"{height:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        # Add coverage % lables above each bar
        add_labels(func_bars)
        add_labels(line_bars)

    cursor = mplcursors.cursor(all_bars, hover=True)

    # Hover on the bar will show coverage report URL
    @cursor.connect("add")
    def on_add(sel):
        bar = sel.artist
        coverage_report_url = getattr(bar, "coverage_report_url", None)
        if coverage_report_url:
            sel.annotation.set_text(coverage_report_url)
            sel.annotation.get_bbox_patch().set(fc="white", ec="black")

    # Click on the bar will open coverage report URL
    def on_click(event):
        if event.inaxes:
            for bar in all_bars:
                if bar.contains(event)[0]:
                    coverage_report_url = getattr(bar, "coverage_report_url", None)
                    if coverage_report_url:
                        webbrowser.open_new_tab(coverage_report_url)
                    break

    fig.canvas.mpl_connect("button_press_event", on_click)

    # Hide unused axes
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.show()


@maestro.command(
    name="coverage",
    help="""Fetch coverage information for maestro results on chromiumos tree
\b
Examples:
  # Get coverage information
  kci-dev maestro coverage
  # Use command with filters
  kci-dev maestro coverage --start-date 2025-09-02
""",
)
@click.option(
    "--branch",
    help="Filter results by branch name",
)
@click.option(
    "--commit",
    help="Commit to get results for",
)
@click.option(
    "--limit",
    default=1000,
    help="Maximum number of nodes to retrieve (default: 1000)",
)
@click.option(
    "--offset",
    default=0,
    help="Starting position for pagination (default: 0)",
)
@click.option(
    "--start-date",
    help="Filter results after this date (ISO format: YYYY-MM-DD or full timestamp)",
)
@click.option(
    "--end-date",
    help="Filter results before this date (ISO format: YYYY-MM-DD or full timestamp)",
)
@click.option(
    "--graph-output",
    is_flag=True,
    default=False,
    help="Display results in bar graph format instead of simple list",
)
@click.pass_context
def coverage(ctx, branch, commit, limit, offset, start_date, end_date, graph_output):
    """Get coverage handler"""
    config_data = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    api_url = config_data[instance]["api"]
    filters = [
        "kind=kbuild",
        "state=done",
        "result=pass",
        "data.kernel_revision.tree=chromiumos",
    ]
    if branch:
        filters.append(f"data.kernel_revision.branch={branch}")
    if commit:
        filters.append(f"data.kernel_revision.commit={commit}")
    if start_date:
        filters.append(f"created__gt={start_date}")
    if end_date:
        filters.append(f"created__lt={end_date}")
    if graph_output:
        aggregate_data = {}
    build_nodes = maestro_get_nodes(api_url, limit, offset, filters, True)
    for build_node in build_nodes:
        child_nodes = maestro_get_nodes(
            api_url,
            limit,
            offset,
            [f"parent={build_node['id']}", "kind=process", "state=done", "result=pass"],
            True,
        )
        for child in child_nodes:
            if not child["name"].startswith("coverage-report"):
                continue
            artifacts = child.get("artifacts")
            if artifacts:
                coverage_tests = maestro_get_nodes(
                    api_url, 50, 0, [f"parent={child['id']}", "kind=test"], True
                )
                if not coverage_tests:
                    continue
                b = child["data"].get("kernel_revision", {}).get("branch")
                c = child["data"].get("kernel_revision", {}).get("commit")
                func_coverage = None
                line_coverage = None
                for test in coverage_tests:
                    if test["name"] == "coverage.functions":
                        func_coverage = test["data"].get("misc", {}).get("measurement")
                    if test["name"] == "coverage.lines":
                        line_coverage = test["data"].get("misc", {}).get("measurement")

                if graph_output:
                    data = {
                        "commit": c,
                        "function_coverage": func_coverage,
                        "line_coverage": line_coverage,
                        "coverage_report_url": artifacts.get("coverage_report"),
                    }
                    if aggregate_data.get(f"chromiumos/{b}"):
                        aggregate_data[f"chromiumos/{b}"].append(data)
                    else:
                        aggregate_data[f"chromiumos/{b}"] = [data]
                else:
                    kci_msg_nonl("- Tree/branch: ")
                    kci_msg_cyan(f"chromiumos/{b}")
                    kci_msg(f"  Commit: {c}")
                    kci_msg(f"  Build: {api_url}viewer?node_id={build_node['id']}")
                    kci_msg_nonl("  Function coverage: ")
                    kci_msg_green(f"{func_coverage}%")
                    kci_msg_nonl("  Line coverage: ")
                    kci_msg_green(f"{line_coverage}%")
                    kci_msg(f"  Coverage report: {artifacts.get('coverage_report')}")
                    kci_msg(f"  Coverage logs: {artifacts.get('log')}")
                    kci_msg("")
    if graph_output:
        print_bar_graph(aggregate_data)


# Add subcommands to the maestro group
maestro.add_command(results)
maestro.add_command(validate)

if __name__ == "__main__":
    from kcidev.libs.common import main_kcidev

    main_kcidev()
