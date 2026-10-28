"""Hidden acceptance tests: written by humans, never shown to the agents."""
import os

import pytest

from app.files import read_user_file


@pytest.fixture
def root(tmp_path):
    for u in ("alice", "bob"):
        (tmp_path / u).mkdir()
        (tmp_path / u / "f.txt").write_bytes(u.encode())
    (tmp_path / "secret.txt").write_bytes(b"secret")
    return tmp_path


def test_own_file(root):
    assert read_user_file("alice", "f.txt", root=str(root)) == b"alice"


@pytest.mark.parametrize("name", ["../bob/f.txt", "../secret.txt", "../../etc/passwd", "sub/../../bob/f.txt"])
def test_dotdot_rejected(root, name):
    with pytest.raises(PermissionError):
        read_user_file("alice", name, root=str(root))


def test_absolute_path_rejected(root):
    with pytest.raises(PermissionError):
        read_user_file("alice", str(root / "secret.txt"), root=str(root))


def test_user_traversal_rejected(root):
    with pytest.raises(PermissionError):
        read_user_file("../bob", "f.txt", root=str(root))


def test_symlink_escape_rejected(root):
    os.symlink(root / "secret.txt", root / "alice" / "link.txt")
    with pytest.raises(PermissionError):
        read_user_file("alice", "link.txt", root=str(root))


def test_sibling_prefix_dir_rejected(root):
    (root / "alice2").mkdir()
    (root / "alice2" / "x.txt").write_bytes(b"x")
    with pytest.raises(PermissionError):
        read_user_file("alice", "../alice2/x.txt", root=str(root))
