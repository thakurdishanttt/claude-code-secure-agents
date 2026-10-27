"""Serve files that users uploaded to their own folder."""
from __future__ import annotations

import os

UPLOAD_ROOT = os.environ.get("UPLOAD_ROOT", "/srv/uploads")


def read_user_file(user: str, name: str, root: str = UPLOAD_ROOT) -> bytes:
    path = os.path.join(root, user, name)
    with open(path, "rb") as fh:
        return fh.read()
