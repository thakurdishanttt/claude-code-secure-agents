from app.files import read_user_file


def test_reads_own_file(tmp_path):
    (tmp_path / "alice").mkdir()
    (tmp_path / "alice" / "a.txt").write_bytes(b"hi")
    assert read_user_file("alice", "a.txt", root=str(tmp_path)) == b"hi"
