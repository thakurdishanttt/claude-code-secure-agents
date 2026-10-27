"""Business logic for todos."""
from __future__ import annotations

from app.store import Todo, TodoStore

MAX_TITLE = 200


class ValidationError(ValueError):
    pass


def create_todo(store: TodoStore, user: str, title: str) -> Todo:
    title = title.strip()
    if not title or len(title) > MAX_TITLE:
        raise ValidationError("title must be 1-200 characters")
    return store.add(user, title)


def list_todos(store: TodoStore, user: str) -> list[Todo]:
    return [t for t in store.all() if t.owner == user]


def delete_todo(store: TodoStore, user: str, todo_id: int) -> bool:
    return store.remove(todo_id)
