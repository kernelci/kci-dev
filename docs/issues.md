+++
title = 'issues'
date = 2025-11-13T17:37:07+09:00
description = 'Fetch KernelCI Database (KCIDB) issues associated with **builds** and **boots**, and **new issues** (first‑time observations) for a specific checkout.'
+++

# `kci-dev results issues` — KCIDB Issue Fetcher

Fetch KernelCI Database (KCIDB) issues associated with **builds** and **boots**, and **new issues** (first‑time observations) for a specific checkout.

---

## Synopsis

```bash
kci-dev results issues [--builds | --boots | --new]
                       [--days <N> | --start-date <DATE> --end-date <DATE>]
                       [--arch <ARCH>] [--origin <ORIGIN>] [--latest]
                       [--giturl <URL> --branch <BRANCH> --commit <COMMIT>]
                       [--git-folder <PATH>]
```

> Use one operating mode at a time: `--builds`, `--boots`, or `--new`.

---

## Description

* **Build/boot issue fetch**: Retrieve KCIDB issues linked to a specific build/boot or across *all available trees* on the dashboard.
* **New‑issue detection**: Identify issues **observed for the first time** for a checkout (defined by `--giturl/--branch/--commit`, or discovered via `--git-folder`).
* **Scope control**: Restrict queries by architecture, time window, result recency, and data origin. Default origin is `maestro`.

---

## Common Workflows

### Inspect a specific issue version

```bash
kci-dev results issue --id 'maestro:<issue-id>' --version 0
kci-dev results issue --id 'maestro:<issue-id>' --version 0 --json
```

Omit `--version` to select the latest issue version. Associated builds and tests
are queried for the same version as the issue details. JSON output is one object
with `issue`, `builds`, and `tests` fields; absent related results are empty lists.

Checkout issue queries preserve each reported `(id, version)` pair and show it
once, even when it appears in builds, boots, and tests. `--new` selects the
version identified by the issue's first incident on that checkout. Missing
incident metadata does not establish that an issue is new.

The ordinary issue listing and checkout queries support `--json`, returning
one array, including `[]` when no issues match. `--new --json` also returns a
single array when scanning all checkouts. API failures exit unsuccessfully.

### List issues within an exact date range

```bash
kci-dev results issues --origin maestro \
  --start-date 2026-08-01T00:00:00Z \
  --end-date 2026-08-08T00:00:00Z

# Date-only boundaries mean midnight UTC, including the end boundary.
kci-dev results issues --origin maestro \
  --start-date 2026-08-01 --end-date 2026-08-08 --json
```

Both boundaries are required. Timestamps must include `Z` or a UTC offset, such
as `2026-08-01T09:00:00+09:00`. Boundaries are sent as Unix seconds without
rounding to whole days; fractional seconds are retained. The start must not be
later than the end. A date-only end is not expanded to the end of that day.

Explicit ranges apply to the issue listing, with optional `--origin` and
`--json`. They cannot be combined with `--days`, `--new`, `--missing`, checkout
selection, or the build/boot, architecture and tree options. Unsupported
combinations produce a usage error rather than silently ignoring the range.

### Detect build issues

```bash
kci-dev results issues --builds
```

### Detect build issues across all checkouts (recent window)

```bash
kci-dev results issues --builds --days 7 --origin maestro
```

### Detect failed/incomplete boot without any issue associated to them

```bash
kci-dev results issues --missing --boots
```

### Detect **new** issues for a checkout (dashboard scan)

```bash
kci-dev results issues --new --days 7 --origin maestro
```

### Detect **new** issues for an explicit checkout (git tuple)

```bash
kci-dev results issues --new \
  --giturl https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git \
  --branch main \
  --commit v6.12 \
  --origin maestro
```

### Filter to a specific architecture and pick the latest available results

```bash
kci-dev results issues --builds --arch arm64 --days 3 --latest
```

> The examples above mirror the CLI help and show the intended combinations.

---

## Options

### Mode & Targets

* `--builds`
  Fetch KCIDB issues for **builds**.
* `--boots`
  Fetch KCIDB issues for **boots**.
* `--new`
  Detect **new** KCIDB issues (first‑time observations) for a checkout.

### Dashboard Scope

* `--days <N>` *(int, default: 5)*
  Time window (in days) to consider when scanning dashboard results. For the
  issue listing, this is measured backwards from the current time in UTC.
* `--start-date <DATE>` and `--end-date <DATE>`
  Exact issue-listing boundaries. Accept `YYYY-MM-DD` (midnight UTC) or
  timezone-aware ISO 8601 timestamps. Use both together, without `--days`.
* `--origin <ORIGIN>` *(default: `maestro`)*
  KCIDB origin to query.
* `--arch <ARCH>`
  Filter results by architecture (e.g., `arm64`, `x86_64`).
* `--latest`
  Select the **latest** results available within the query.

### Checkout Specification (for `--new`)

Provide the checkout explicitly **or** let the tool infer it from a local repo.

* `--giturl <URL>`
  Git URL of the kernel tree.
* `--branch <BRANCH>`
  Branch to evaluate.
* `--commit <COMMIT>`
  Commit SHA or tag (e.g., `v6.12`).
* `--git-folder <PATH>`
  Path to a local **git repository**. Must exist and be a directory. When provided, the tool may derive `giturl/branch/commit` from the local checkout.

---

## Examples (from CLI help)

```bash
# Detect build issues
kci-dev results issues --builds
kci-dev results issues --builds --days <number-of-days> --origin <origin>

# Detect boot issues
kci-dev results issues --boots
kci-dev results issues --boots --days <number-of-days> --origin <origin>

# Detect new issues for a checkout
kci-dev results issues --new --days <number-of-days> --origin <origin>
kci-dev results issues --new --giturl <git-url> --branch <git-branch> --commit <commit> --origin <origin>
```

---

## Troubleshooting

* **No results**: Check your `--days` window, `--origin`, and that the target builds/boots are *failed* or *inconclusive*.
* **Checkout not resolved**: When using `--new`, ensure the `--giturl/--branch/--commit` tuple is provided, or pass `--git-folder` that points to a valid git repo.
* **Architecture filter too narrow**: Try removing `--arch` or broadening it.

---
