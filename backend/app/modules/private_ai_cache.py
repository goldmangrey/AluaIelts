"""Small private, bounded on-disk cache; no browser plaintext or external service."""

import json
import os
import tempfile
import time
from pathlib import Path

TTL = 30 * 86400


def directory(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    st = root.lstat()
    if root.is_symlink() or not root.is_dir() or st.st_uid != os.geteuid() or st.st_mode & 0o077:
        raise OSError("AI cache must be a private owned directory")
    return root


def load(path):
    path = Path(path)
    directory(path.parent)
    try:
        st = path.lstat()
        if (
            path.is_symlink()
            or st.st_uid != os.geteuid()
            or st.st_mode & 0o077
            or st.st_size > 20000
            or st.st_mtime < time.time() - TTL
        ):
            return None
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def save(path, data):
    path = Path(path)
    root = directory(path.parent)
    encoded = json.dumps(data, ensure_ascii=False)
    if len(encoded.encode()) > 20000:
        raise OSError("AI cache payload too large")
    files = sorted(root.glob("[0-9a-f]" * 64 + ".json"), key=lambda p: p.stat().st_mtime)
    for old in files[: max(0, len(files) - 999)]:
        old.unlink(missing_ok=True)
    fd, temporary = tempfile.mkstemp(dir=root, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as file:
            file.write(encoded)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
