"""Opt-in native browser integration against disposable PostgreSQL and synthetic media."""

import os
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from test_household_bootstrap import bootstrap, postgres_url, system  # noqa: F401
from test_listening import listening  # noqa: F401


@pytest.mark.skipif(
    os.environ.get("ALUA_RUN_LISTENING_BROWSER") != "1", reason="Opt-in isolated browser run"
)
def test_listening_real_browser_lifecycle(listening):  # noqa: F811
    service, client, _, _ = listening
    device, _ = bootstrap(client, "husband")
    server = uvicorn.Server(
        uvicorn.Config(client.app, host="127.0.0.1", port=3401, log_level="warning", lifespan="off")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        env = dict(os.environ, ALUA_LISTENING_TEST_TOKEN=device["token"])
        subprocess.run(
            ["node", "scripts/test-listening.mjs"],
            cwd=Path(__file__).resolve().parents[2] / "web",
            env=env,
            check=True,
            timeout=480,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()
