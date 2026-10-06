"""Regression: the documented global proxy switch must actually take effect.

``DOCUTRANSLATE_PROXY_ENABLED`` was read into ``global_values.USE_PROXY`` and
``config.PROXY_ENABLED`` but never consumed by any runtime code path.
"""
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _config_value(env: dict) -> str:
    import os

    env = {**os.environ, **env}
    code = (
        "from docutranslate.config import SYSTEM_PROXY_ENABLE\n"
        "print('value=', SYSTEM_PROXY_ENABLE)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def test_global_proxy_switch_becomes_the_default():
    assert _config_value({"DOCUTRANSLATE_PROXY_ENABLED": "true"}) == "value= True"
    assert _config_value({"DOCUTRANSLATE_PROXY_ENABLED": "false"}) == "value= False"


def test_explicit_system_proxy_setting_wins():
    value = _config_value(
        {
            "DOCUTRANSLATE_PROXY_ENABLED": "true",
            "DOCUTRANSLATE_SYSTEM_PROXY_ENABLE": "false",
        }
    )
    assert value == "value= False"


@pytest.mark.parametrize("raw,expected", [("ten", "200"), ("", "200"), ("50", "50")])
def test_task_limit_env_parsing(raw, expected):
    import os

    env = {**os.environ, "DOCUTRANSLATE_TASK_MAX_COUNT": raw}
    code = "from docutranslate.config import TASK_MAX_COUNT\nprint(TASK_MAX_COUNT)\n"
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == expected
