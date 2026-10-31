import math


def finite_number(value: object) -> float:
    """Returns `value` as a float, or raises ValueError if it is not a finite number."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError(f"expected a finite number, got {value!r}")
    return float(value)
