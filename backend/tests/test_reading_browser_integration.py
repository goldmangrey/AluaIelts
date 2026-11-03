"""Opt-in local HTTP/browser integration, never a configured or production database."""
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from test_household_bootstrap import bootstrap, postgres_url, system  # noqa: F401


@pytest.mark.skipif(os.environ.get("ALUA_RUN_READING_BROWSER") != "1",
                    reason="Opt-in browser integration: ALUA_RUN_READING_BROWSER=1")
def test_real_local_reading_browser_lifecycle(system):  # noqa: F811
    _, client, _ = system
    device, _ = bootstrap(client, "husband")
    # Same app, services, auth and PostgreSQL as the normal integration fixture.
    config = uvicorn.Config(client.app, host="127.0.0.1", port=3400,
                            log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started, "Isolated API could not start on 127.0.0.1:3400"
        env = dict(os.environ, ALUA_RELEASE_API_URL="http://127.0.0.1:3400/api/v1",
                   ALUA_RELEASE_INTEGRATION_TOKEN=device["token"])
        web = Path(__file__).resolve().parents[2] / "web"
        subprocess.run(["node", "scripts/test-reading-integration.mjs"], cwd=web,
                       env=env, check=True, timeout=240)
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive(), "Isolated API did not stop"
