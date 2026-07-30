import pytest

from kcidev.subcommands.maestro.validate import helper


@pytest.mark.parametrize(
    ("get_stats", "get_results", "item_type"),
    (
        (helper.get_build_stats, "get_builds", "build"),
        (helper.get_boot_stats, "get_boots", "boot"),
    ),
)
def test_equal_counts_with_different_ids_fail_validation(
    monkeypatch, get_stats, get_results, item_type
):
    maestro_results = [
        {
            "id": "maestro-only",
            "result": "pass",
            "retry_counter": 0,
            "data": {},
        }
    ]
    dashboard_results = [{"id": f"{item_type}:dashboard-only", "status": "PASS"}]
    monkeypatch.setattr(
        helper,
        get_results,
        lambda *args, **kwargs: (maestro_results, dashboard_results),
    )

    stats = get_stats(None, "url", "branch", "commit", "tree", False, None)

    assert stats[2:5] == [1, 1, "❌"]
    assert stats[5] == ["dashboard-only"]
