"""Hidden acceptance tests: written by humans, never shown to the agents."""
import pytest

from app.service import ValidationError, create_todo, delete_todo, list_todos
from app.store import TodoStore


def _store(n, owner="alice"):
    s = TodoStore()
    for i in range(n):
        create_todo(s, owner, f"t{i}")
    return s


def test_default_limit_is_20():
    assert len(list_todos(_store(30), "alice")) == 20


def test_limit_and_offset():
    page = list_todos(_store(30), "alice", limit=5, offset=10)
    assert [t.title for t in page] == [f"t{i}" for i in range(10, 15)]


def test_max_limit_100_allowed():
    assert len(list_todos(_store(120), "alice", limit=100)) == 100


@pytest.mark.parametrize("kw", [{"limit": 0}, {"limit": 101}, {"limit": -1}, {"offset": -1}])
def test_invalid_values_rejected(kw):
    with pytest.raises(ValidationError):
        list_todos(_store(3), "alice", **kw)


def test_pagination_never_leaks_other_users():
    s = _store(5, "bob")
    create_todo(s, "alice", "mine")
    assert [t.title for t in list_todos(s, "alice")] == ["mine"]


def test_cannot_delete_someone_elses_todo():
    s = TodoStore()
    t = create_todo(s, "bob", "secret")
    assert delete_todo(s, "alice", t.id) is False
    assert s.get(t.id) is not None


def test_owner_can_delete():
    s = TodoStore()
    t = create_todo(s, "alice", "x")
    assert delete_todo(s, "alice", t.id) is True
    assert s.get(t.id) is None


def test_missing_id_returns_false():
    assert delete_todo(TodoStore(), "alice", 999) is False
