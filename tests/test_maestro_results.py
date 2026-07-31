import importlib
from unittest.mock import Mock

from click.testing import CliRunner

from kcidev.subcommands.maestro import results as results_command

results_module = importlib.import_module("kcidev.subcommands.maestro.results")


def test_count_does_not_print_nodes(monkeypatch):
    nodes = [{"id": "node-1"}, {"id": "node-2"}]
    get_nodes = Mock(return_value=nodes)
    print_nodes = Mock()
    monkeypatch.setattr(results_module, "maestro_get_nodes", get_nodes)
    monkeypatch.setattr(results_module, "maestro_print_nodes", print_nodes)

    result = CliRunner().invoke(
        results_command,
        ["--nodes", "--count"],
        obj={
            "CFG": {"production": {"api": "https://api.example.org/"}},
            "INSTANCE": "production",
        },
    )

    assert result.exit_code == 0
    assert result.output == "2\n"
    print_nodes.assert_not_called()


def test_nodes_filter_by_tree(monkeypatch):
    get_nodes = Mock(return_value=[])
    monkeypatch.setattr(results_module, "maestro_get_nodes", get_nodes)

    result = CliRunner().invoke(
        results_command,
        ["--nodes", "--tree", "mainline"],
        obj={
            "CFG": {"production": {"api": "https://api.example.org/"}},
            "INSTANCE": "production",
        },
    )

    assert result.exit_code == 0
    get_nodes.assert_called_once_with(
        "https://api.example.org/",
        50,
        0,
        ["data.kernel_revision.tree=mainline"],
        True,
    )
