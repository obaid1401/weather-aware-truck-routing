"""The production server settings in backend/gunicorn.conf.py."""

import runpy
from pathlib import Path
from typing import Any

import pytest

GUNICORN_CONF = Path(__file__).resolve().parents[2] / "gunicorn.conf.py"


def load(monkeypatch: pytest.MonkeyPatch, port: str | None) -> dict[str, Any]:
    if port is None:
        monkeypatch.delenv("PORT", raising=False)
    else:
        monkeypatch.setenv("PORT", port)
    return runpy.run_path(str(GUNICORN_CONF))


def test_binds_to_the_port_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch, "10000")

    assert settings["bind"] == "0.0.0.0:10000"


def test_an_analysis_is_not_cut_short(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch, "8000")

    # The frontend waits up to 90 seconds for an analysis.
    assert settings["timeout"] > 90
    assert settings["worker_class"] == "gthread"
    assert settings["threads"] > 1


@pytest.mark.parametrize("port", [None, "", "  ", "eighty"])
def test_fails_clearly_without_a_port(monkeypatch: pytest.MonkeyPatch, port: str | None) -> None:
    with pytest.raises(RuntimeError, match="PORT is not set"):
        load(monkeypatch, port)
