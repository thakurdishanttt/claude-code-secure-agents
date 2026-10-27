"""Small helpers."""
from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def chunk(items: list[T], size: int) -> list[list[T]]:
    """Split items into lists of at most `size` elements."""
    if size < 1:
        raise ValueError("size must be >= 1")
    return [items[i:i + size] for i in range(0, len(items) - size + 1, size)]
