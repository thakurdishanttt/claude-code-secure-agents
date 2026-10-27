"""Hidden acceptance tests: written by humans, never shown to the agents."""
import pytest

from app.util import chunk


@pytest.mark.parametrize("items,size,want", [
    ([1, 2, 3], 2, [[1, 2], [3]]),
    ([1, 2, 3, 4], 2, [[1, 2], [3, 4]]),
    ([], 3, []),
    ([1], 5, [[1]]),
    ([1, 2, 3], 1, [[1], [2], [3]]),
])
def test_chunk(items, size, want):
    assert chunk(items, size) == want


def test_bad_size():
    with pytest.raises(ValueError):
        chunk([1], 0)
