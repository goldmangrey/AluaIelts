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


@pytest.mark.skipif(
    os.environ.get("ALUA_RUN_PRACTICE_BROWSER") != "1",
    reason="Opt-in isolated practice browser run",
)
def test_practice_history_profile_browser(listening, monkeypatch, tmp_path):  # noqa: F811
    import json
    from uuid import uuid4

    from PIL import Image
    from test_household_bootstrap import headers
    from test_reading import start
    from test_reading_ai import submit_payload
    from test_writing import ESSAY, assessment, create

    from app.modules.listening.ai_review import AIReview
    from app.modules.writing.catalog import import_tasks
    from app.modules.writing.contract import validate_assessment
    from app.modules.writing.models import WritingAttemptRow

    service, client, _, _ = listening
    device, _ = bootstrap(client, "husband")
    h = headers(device)
    from datetime import UTC, datetime, timedelta

    from test_practice import finish_listening

    from app.modules.listening.models import ListeningAttemptRow

    service.clock = lambda: datetime.now(UTC)
    old_id = finish_listening(client, h)
    with service.db.session() as s:
        s.get(ListeningAttemptRow, old_id).submitted_at = datetime.now(UTC) - timedelta(days=180)
    # Seed only the disposable database using the real completion endpoints.
    r, _ = start(client, h, eid="cambridge-07-test-01")
    assert (
        client.post(
            f"/api/v1/reading/attempts/{r['id']}/submit",
            headers=h,
            json=submit_payload(r, {"cambridge-07-test-01-q-07": "touch"}),
        ).status_code
        == 200
    )
    import_tasks(service.db)
    w = create(client, h)
    saved = client.put(
        f"/api/v1/writing/attempts/{w['id']}",
        headers=h,
        json={"expected_version": 0, "essay": ESSAY},
    ).json()
    assert (
        client.post(
            f"/api/v1/writing/attempts/{w['id']}/submit",
            headers=h,
            json={"expected_version": saved["version"]},
        ).status_code
        == 200
    )
    with service.db.session() as s:
        row = s.get(WritingAttemptRow, w["id"])
        row.assessment = validate_assessment(assessment(), ESSAY)
        row.ai_status = "completed"
        row.completed_at = None  # A legacy result must not acquire an invented date.
    # Separate dated assessment verifies a chart point; the legacy one stays undated.
    dated = create(client, h)
    draft = client.put(
        f"/api/v1/writing/attempts/{dated['id']}",
        headers=h,
        json={"expected_version": 0, "essay": ESSAY},
    ).json()
    assert (
        client.post(
            f"/api/v1/writing/attempts/{dated['id']}/submit",
            headers=h,
            json={"expected_version": draft["version"]},
        ).status_code
        == 200
    )
    with service.db.session() as s:
        row = s.get(WritingAttemptRow, dated["id"])
        row.assessment = validate_assessment(assessment(), ESSAY)
        row.ai_status = "completed"
    root = Path(__file__).resolve().parents[2]
    task = json.loads((root / "web/src/features/speaking/content.json").read_text())["questions"][0]
    assert (
        client.post(
            "/api/v1/practice/speaking/attempts",
            headers=h,
            json={"event_id": str(uuid4()), "task_id": task["id"]},
        ).status_code
        == 201
    )
    avatar = tmp_path / "avatar.png"
    Image.new("RGB", (400, 300), "#247551").save(avatar)
    calls = []

    def generated(self, *args):
        calls.append(1)
        return {
            "what_happened": "QA saved explanation",
            "why": "QA answer differs from the key.",
            "next_time": "QA listen for the complete answer.",
            "cached": False,
            "generation": {"provider": "qa-stub", "model": "counter"},
            "evidence": {
                "available": True,
                "reason": None,
                "part": 1,
                "quote": "QA fixture",
                "segment_ids": ["qa"],
                "clip_start": 1,
                "clip_end": 3,
            },
        }

    monkeypatch.setattr(AIReview, "_generate", generated)
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
        env = dict(
            os.environ,
            ALUA_LISTENING_TEST_TOKEN=device["token"],
            ALUA_PRACTICE_TEST="1",
            ALUA_LISTENING_TEST_GREP="practice history and profile",
            ALUA_PRACTICE_AVATAR=str(avatar),
        )
        subprocess.run(
            ["node", "scripts/test-listening.mjs"],
            cwd=root / "web",
            env=env,
            check=True,
            timeout=480,
        )
        # One generation per fresh attempt (desktop + mobile); reloads use the DB.
        assert len(calls) == 4
        history = client.get("/api/v1/practice/history", headers=h).json()
        assert history["total"] == 15  # 5 seed + 5 completions per browser
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()
