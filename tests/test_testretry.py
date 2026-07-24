from unittest.mock import patch

from click.testing import CliRunner

from kcidev.subcommands.testretry import testretry as retry_command

OBJ = {
    "CFG": {"staging": {"pipeline": "https://example.test/", "token": "t"}},
    "INSTANCE": "staging",
}


def _invoke():
    return CliRunner().invoke(retry_command, ["--nodeid", "n1"], obj=dict(OBJ))


def test_testretry_success_prints_message():
    with patch(
        "kcidev.subcommands.testretry.send_jobretry", return_value={"message": "OK"}
    ):
        result = _invoke()
    assert result.exit_code == 0
    assert "OK" in result.output


def test_testretry_failure_exits_nonzero():
    with patch("kcidev.subcommands.testretry.send_jobretry", return_value=None):
        result = _invoke()
    assert result.exit_code != 0
    assert "No response message" not in result.output
