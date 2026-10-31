import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_rate_limit_history() -> None:
    """Rate-limit counters live in the cache; start every API test with none recorded."""
    cache.clear()
