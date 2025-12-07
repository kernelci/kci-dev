+++
title = 'maestro-validate'
date = 2024-01-14T07:07:07+01:00
description = 'Validate KernelCI dashboard results against Mestro.'
+++

# `kci-dev maestro validate` — Maestro/Dashboard Consistency Checker

Validate KernelCI dashboard results against Maestro pipeline outputs.

This command group compares **builds** and **boots** recorded in the KernelCI dashboard with the corresponding Maestro results (KCIDB origin `maestro` by default). It flags count mismatches, lists missing IDs, and detects status mismatches.

---

## TL;DR

```bash
# Validate latest builds for all trees seen in the last N days
kci-dev maestro validate builds --all-checkouts --days 7

# Validate latest boots for all trees seen in the last N days
kci-dev maestro validate boots  --all-checkouts --days 7

# Validate a specific checkout (builds)
kci-dev maestro validate builds --giturl <url> --branch <branch> --commit <commit>

# Validate a specific checkout (boots)
kci-dev maestro validate boots  --giturl <url> --branch <branch> --commit <commit>

# Compare build history across multiple checkouts for the same tree/branch
kci-dev maestro validate builds --history --giturl <url> --branch <branch> --days 14

# Show results as a table (otherwise prints a simple list)
kci-dev maestro validate builds --table-output ...
kci-dev maestro validate boots  --table-output ...
```

---

## Usage

```text
kci-dev maestro validate [SUBCOMMAND]

Subcommands:
  builds   Validate build results
  boots    Validate boot results
```

Invoking `kci-dev maestro validate` without a subcommand prints help and exits with code `0`.

---

## Shared Concepts

* **Origin**: KCIDB origin to pull dashboard “trees” from. Defaults to `maestro`.
* **All checkouts vs specific checkout**:

  * `--all-checkouts` validates the **latest** results for all trees observed in the last `--days` days.
  * A **specific checkout** is identified by `--giturl`, `--branch`, and `--commit`.
    If not provided, the tool can infer from `--git-folder` (or use `--latest`).
* **Arch filter**: `--arch <arch>` narrows both Maestro and dashboard queries.
* **Output modes**:

  * **Simple list (default)**: concise, includes per-commit links to missing items.
  * **Table**: `--table-output` renders a grid with counts, flags, and IDs.

---

## Status Mapping & Mismatch Rules

### Builds

* Maestro `result` → Dashboard `status`

  * `pass` → `PASS`
  * `fail` → `FAIL`
  * `incomplete` → `ERROR`
* Retries excluded unless `retry_counter == 3` (to avoid counting transient retries).
* A **status mismatch** is reported if the mapped status doesn’t match the dashboard.

### Boots

* Maestro `result`:

  * `pass` → `PASS`
  * `fail` → `FAIL`
  * `incomplete` → mapped using `data.error_code`:

    * **MISS** if error_code ∈ {`Bug`, `Configuration`, `invalid_job_params`, `Job`, `job_generation_error`, `ObjectNotPersisted`, `RequestBodyTooLarge`, `submit_error`, `Unexisting permission codename.`, `kbuild_internal_error`}
    * **ERROR** if error_code ∈ {`Canceled`, `Infrastructure`, `LAVATimeout`, `MultinodeTimeout`, `Test`}
* Boot retries excluded unless `retry_counter == 3`.
* A **status mismatch** is reported when the mapped result disagrees with the dashboard.

---

## Subcommand: `builds`

Validate dashboard build results against Maestro.

```bash
kci-dev maestro validate builds [OPTIONS]
```

### Options

| Option            | Type |   Default | Description                                                                                                               |
| ----------------- | ---- | --------: | ------------------------------------------------------------------------------------------------------------------------- |
| `--all-checkouts` | flag |           | Validate latest builds for all available trees within `--days`. **Mutually exclusive** with `--giturl/--branch/--commit`. |
| `--days`          | int  |       `7` | Time window (days) for selecting trees/checkouts.                                                                         |
| `--origin`        | str  | `maestro` | KCIDB origin for tree discovery.                                                                                          |
| `--giturl`        | str  |           | Kernel tree Git URL.                                                                                                      |
| `--branch`        | str  |           | Branch name.                                                                                                              |
| `--commit`        | str  |           | Commit SHA or tag.                                                                                                        |
| `--git-folder`    | path |           | Local repo path used to infer missing Git params.                                                                         |
| `--latest`        | flag |           | Use the latest available results (when not specifying `--commit`).                                                        |
| `--arch`          | str  |           | Architecture filter.                                                                                                      |
| `--history`       | flag |           | Validate **build count consistency across multiple checkouts** for the same tree/branch within `--days`.                  |
| `--verbose`       | flag |   `false` | Print detailed lists of missing items (JSON).                                                                             |
| `--table-output`  | flag |   `false` | Show a table (otherwise prints a simple list).                                                                            |

> ❗ `--all-checkouts` **cannot** be combined with `--giturl`, `--branch`, or `--commit`.
> If `--history` is used with `--all-checkouts`, history is computed for **each tree** seen within `--days`.
> If `--history` is used without `--all-checkouts`, you must specify the tree via `--giturl` and `--branch`.

### Output (Builds)

* **Counts**: Maestro vs Dashboard, with a comparison flag:

  * `✅` counts match
  * `❌` counts differ
* **Missing IDs**: Item IDs present on one side but not the other.
  Missing dashboard items are printed as viewer links:

  ```
  https://api.kernelci.org/viewer?node_id=<id>
  ```
* **Status mismatches**: List of build IDs where the mapped Maestro status != Dashboard status.

#### Example: Table Output

```text
+------------------+------------------------------------------+---------+------------+-------------------------+---------------------+-------------------------------+
| tree/branch      | Commit                                   | Maestro | Dashboard  | Build count             | Missing build IDs   | Builds with                   |
|                  |                                          | builds  | builds     | comparison              |                     | status mismatch               |
+==================+==========================================+=========+============+=========================+=====================+===============================+
| linux/mainline   | 1a2b3c4d5e6f...                           | 120     | 120        | ✅                      | []                  | []                            |
| linux/stable-6.6 | f00baa...                                 | 118     | 116        | ❌                      | [<ids>...]          | [<ids>...]                    |
+------------------+------------------------------------------+---------+------------+-------------------------+---------------------+-------------------------------+
```

#### Example: Simple List (default)

```text
• linux/mainline: ✅
  Commit: 1a2b3c4d5e6f...

• linux/stable-6.6: ❌
  Commit: f00baa...
  Missing builds: 2
  - https://api.kernelci.org/viewer?node_id=<id1>
  - https://api.kernelci.org/viewer?node_id=<id2>
```

---

## Subcommand: `boots`

Validate dashboard boot results against Maestro.

```bash
kci-dev maestro validate boots [OPTIONS]
```

### Options

| Option            | Type |   Default | Description                                                                                                              |
| ----------------- | ---- | --------: | ------------------------------------------------------------------------------------------------------------------------ |
| `--all-checkouts` | flag |           | Validate latest boots for all available trees within `--days`. **Mutually exclusive** with `--giturl/--branch/--commit`. |
| `--days`          | int  |       `7` | Time window (days) for selecting trees/checkouts.                                                                        |
| `--origin`        | str  | `maestro` | KCIDB origin for tree discovery.                                                                                         |
| `--giturl`        | str  |           | Kernel tree Git URL.                                                                                                     |
| `--branch`        | str  |           | Branch name.                                                                                                             |
| `--commit`        | str  |           | Commit SHA or tag.                                                                                                       |
| `--git-folder`    | path |           | Local repo path used to infer missing Git params.                                                                        |
| `--latest`        | flag |           | Use the latest available results (when not specifying `--commit`).                                                       |
| `--arch`          | str  |           | Architecture filter.                                                                                                     |
| `--verbose`       | flag |   `false` | Print detailed lists of missing items (JSON).                                                                            |
| `--table-output`  | flag |   `false` | Show a table (otherwise prints a simple list).                                                                           |

### Output (Boots)

* **Counts**: Maestro vs Dashboard boots, with `✅/❌` flag.
* **Missing boot IDs** with viewer links (same format as builds).
* **Status mismatches** using the boot-specific mapping (including `MISS`/`ERROR` for `incomplete` with known `error_code` categories).

---

## History Mode (Builds Only)

`--history` evaluates **count consistency across multiple recent checkouts** of the same tree/branch within `--days`.
Output summarizes each commit under the tree/branch and flags commits where counts differ, along with missing IDs.

Example (simple list):

```text
linux/mainline:
  Commit 1a2b3c4d5e6f: ✅
  Commit 9c8d7e6f5a4b: ❌
  Missing builds: 3
  - https://api.kernelci.org/viewer?node_id=<idA>
  - https://api.kernelci.org/viewer?node_id=<idB>
  - https://api.kernelci.org/viewer?node_id=<idC>
```

---

## Inference Helpers

When `--giturl/--branch/--commit` are omitted:

* `--git-folder` can be used to infer values from a local clone.
* `--latest` selects the latest available results for the inferred tree/branch.

---

## Exit & Error Behavior

* Running `kci-dev maestro validate` without a subcommand prints help and exits `0`.
* If dashboard queries fail or are aborted, the tool prints an error and **skips** stats for that item.
* If a dashboard responds with “No builds/boots available,” the tool treats the dashboard count as `0` for that checkout.

---

## Examples (Copy/Paste)

```bash
# All builds for all trees in last 3 days (table view)
kci-dev maestro validate builds --all-checkouts --days 3 --table-output

# Specific checkout (boots) for x86_64 only
kci-dev maestro validate boots \
  --giturl https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git \
  --branch master \
  --commit <sha> \
  --arch x86_64

# Build history for a stable branch over the last 14 days
kci-dev maestro validate builds --history \
  --giturl https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git \
  --branch linux-6.6.y \
  --days 14 \
  --table-output

# Infer from local repo, pick latest
kci-dev maestro validate builds --git-folder /path/to/linux --latest
```

---

## Notes & Gotchas

* **Mutual exclusion**: `--all-checkouts` cannot be combined with any of `--giturl/--branch/--commit`.
* **Retries**: To avoid double-counting, build/boot retries are excluded unless `retry_counter == 3`.
* **Viewer links**: Missing items are printed with `https://api.kernelci.org/viewer?node_id=<id>` for quick inspection.
* **Verbose JSON**: Use `--verbose` to print the full JSON of missing items for debugging.
* **Formats**: The table view uses `tabulate`’s `simple_grid` format with reasonable column width caps.

---

## See Also

* `kci-dev results` (for raw result listing and filtering)
* `kci-dev maestro validate builds --help`
* `kci-dev maestro validate boots  --help`

> This page documents the CLI behavior surfaced by `kcidev.subcommands.maestro.validate.{builds,boots}` and their helpers.
