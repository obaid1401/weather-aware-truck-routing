import subprocess
import sys
from pathlib import Path

import pytest

from shared.validation import finite_number

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(("value", "expected"), [(0, 0.0), (3, 3.0), (-2.5, -2.5)])
def test_finite_numbers_are_returned_as_floats(value: object, expected: float) -> None:
    result = finite_number(value)

    assert result == expected
    assert isinstance(result, float)


@pytest.mark.parametrize("value", [None, "1", True, False, float("nan"), float("inf"), [1]])
def test_non_numbers_are_rejected(value: object) -> None:
    with pytest.raises(ValueError):
        finite_number(value)


def test_geometry_helpers_do_not_import_http_code() -> None:
    # Run in a fresh interpreter so modules imported by other tests do not interfere.
    check = (
        "import sys, shared.geo; sys.exit('httpx' in sys.modules or 'shared.http' in sys.modules)"
    )

    result = subprocess.run(
        [sys.executable, "-c", check], cwd=BACKEND_DIR, capture_output=True, check=False
    )

    assert result.returncode == 0, result.stderr.decode()
