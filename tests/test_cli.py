import os
from pathlib import Path
from typer.testing import CliRunner

import pytest

import embykeeper
from embykeeper.cli import app, should_start_notifier

runner = CliRunner()


@pytest.fixture()
def in_temp_dir(tmp_path: Path):
    current = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(current)


def test_version():
    result = runner.invoke(app, ["--version"])
    assert embykeeper.__version__ in result.stdout
    assert result.exit_code == 0


def test_create_config(in_temp_dir: Path):
    result = runner.invoke(app, ["--example-config"])
    assert "这是一个配置文件范例" in result.stdout
    assert result.exit_code == 0


@pytest.mark.parametrize(
    ("once", "noexit", "notifier_enabled", "notifier_once", "expected"),
    [
        (False, False, False, False, True),
        (True, False, False, False, False),
        (True, False, True, False, False),
        (True, False, True, True, True),
        (True, True, False, False, True),
    ],
)
def test_should_start_notifier(once, noexit, notifier_enabled, notifier_once, expected):
    assert (
        should_start_notifier(
            once,
            noexit=noexit,
            notifier_enabled=notifier_enabled,
            notifier_once=notifier_once,
        )
        is expected
    )
