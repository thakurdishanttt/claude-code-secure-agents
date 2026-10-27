import pytest

from app.service import ValidationError, create_todo, delete_todo, list_todos
from app.store import TodoStore


def test_create_and_list():
    s = TodoStore()
    create_todo(s, "alice", "buy milk")
    create_todo(s, "bob", "walk dog")
    assert [t.title for t in list_todos(s, "alice")] == ["buy milk"]


def test_title_validation():
    with pytest.raises(ValidationError):
        create_todo(TodoStore(), "alice", "   ")


def test_delete():
    s = TodoStore()
    t = create_todo(s, "alice", "x")
    assert delete_todo(s, "alice", t.id)
