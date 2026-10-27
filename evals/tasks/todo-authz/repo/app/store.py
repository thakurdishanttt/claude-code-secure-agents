"""In-memory todo store."""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count


@dataclass
class Todo:
    id: int
    owner: str
    title: str
    done: bool = False


@dataclass
class TodoStore:
    _items: dict[int, Todo] = field(default_factory=dict)
    _ids: count = field(default_factory=lambda: count(1))

    def add(self, owner: str, title: str) -> Todo:
        todo = Todo(id=next(self._ids), owner=owner, title=title)
        self._items[todo.id] = todo
        return todo

    def get(self, todo_id: int) -> Todo | None:
        return self._items.get(todo_id)

    def all(self) -> list[Todo]:
        return list(self._items.values())

    def remove(self, todo_id: int) -> bool:
        return self._items.pop(todo_id, None) is not None
