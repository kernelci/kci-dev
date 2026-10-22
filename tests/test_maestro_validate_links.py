import importlib

import pytest
from click.testing import CliRunner

COMMIT = "a" * 40


def _stats():
    return ["mainline/master", COMMIT, 2, 1, "❌", ["missing"], ["mismatch"]]


@pytest.fixture
def validate_cli(monkeypatch):
    for kind, stats_name in [
        ("builds", "get_build_stats"),
        ("boots", "get_boot_stats"),
    ]:
        module = importlib.import_module(f"kcidev.subcommands.maestro.validate.{kind}")
        monkeypatch.setattr(
            module,
            "set_giturl_branch_commit",
            lambda origin, giturl, branch, commit, latest, git_folder: (
                giturl,
                branch,
                commit,
            ),
        )
        monkeypatch.setattr(module, "get_tree_name", lambda *args: "mainline")
        monkeypatch.setattr(module, stats_name, lambda *args: _stats())
        if kind == "builds":
            monkeypatch.setattr(
                module, "get_builds_history_stats", lambda *args: [_stats()]
            )

    def forbid_network(*args, **kwargs):
        pytest.fail("Validation output tests must not make network requests")

    monkeypatch.setattr("requests.sessions.Session.request", forbid_network)
    return importlib.import_module("kcidev.main").get_cli()


@pytest.mark.parametrize(
    "kind,extra", [("builds", []), ("builds", ["--history"]), ("boots", [])]
)
@pytest.mark.parametrize(
    "api_url",
    [
        "https://api.kernelci.org/",
        "https://staging.example.test:9000/",
        "https://staging.example.test:9000",
        "https://ci.example.test/maestro/",
        "https://ci.example.test/maestro",
    ],
)
@pytest.mark.parametrize("explicit_instance", [False, True])
def test_validation_links_use_selected_instance(
    validate_cli, tmp_path, kind, extra, api_url, explicit_instance
):
    settings = tmp_path / "kci-dev.toml"
    default_instance = "other" if explicit_instance else "selected"
    settings.write_text(
        f'default_instance = "{default_instance}"\n'
        f'[selected]\napi = "{api_url}"\n'
        '[other]\napi = "https://unused.example.test/"\n',
        encoding="utf-8",
    )
    args = ["--settings", str(settings)]
    if explicit_instance:
        args += ["--instance", "selected"]
    args += [
        "maestro",
        "validate",
        kind,
        "--giturl",
        "https://example.test/linux.git",
        "--branch",
        "master",
        "--commit",
        COMMIT,
    ] + extra

    result = CliRunner().invoke(validate_cli, args)

    assert result.exit_code == 0, result.output
    links = [line.strip() for line in result.output.splitlines() if "viewer?" in line]
    assert links == [
        f"- {api_url.rstrip('/')}/viewer?node_id=missing",
        f"- {api_url.rstrip('/')}/viewer?node_id=mismatch",
    ]


@pytest.mark.parametrize("kind", ["builds", "boots"])
def test_table_output_does_not_require_link_configuration(validate_cli, kind):
    module = importlib.import_module(f"kcidev.subcommands.maestro.validate.{kind}")
    result = CliRunner().invoke(
        getattr(module, kind),
        [
            "--giturl",
            "https://example.test/linux.git",
            "--branch",
            "master",
            "--commit",
            COMMIT,
            "--table-output",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "mainline/master" in result.output
    assert "viewer?" not in result.output
