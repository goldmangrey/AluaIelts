"""Authenticate only server-to-server assessment mutations, in addition to learner auth."""

import hashlib
import hmac
import os
import time
from pathlib import Path

from fastapi import Request

from app.core.exceptions import ForbiddenError


def bridge_key():
    key = os.environ.get("WRITING_BRIDGE_SECRET", "")
    if not key and os.environ.get("ALUA_LOCAL_STACK") == "true":
        path = Path.home() / ".local/share/alua/local-stack/writing-bridge.key"
        if path.is_file() and not path.is_symlink() and not path.stat().st_mode & 0o077:
            key = path.read_text().strip()
    if len(key) < 32:
        raise ForbiddenError("Writing server bridge is unavailable.")
    return key


async def verify_bridge(request: Request):
    stamp = request.headers.get("x-writing-time", "")
    if not stamp.isdigit() or abs(time.time() - int(stamp)) > 60:
        raise ForbiddenError("Server assessment authorization required.")
    body = await request.body()
    message = stamp + "\n" + request.url.path + "\n" + body.decode()
    expected = hmac.new(bridge_key().encode(), message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("x-writing-signature", "")):
        raise ForbiddenError("Server assessment authorization required.")


def initialize_local_bridge():
    if os.environ.get("ALUA_LOCAL_STACK") != "true":
        return
    import secrets

    path = Path.home() / ".local/share/alua/local-stack/writing-bridge.key"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        bridge_key()
        return
    with os.fdopen(fd, "w") as handle:
        handle.write(secrets.token_hex(32))
