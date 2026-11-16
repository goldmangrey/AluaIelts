"""Opt-in browser QA of My Mistakes using disposable PostgreSQL and synthetic media."""

import copy
import os
import subprocess
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import uvicorn
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401
from test_listening import listening  # noqa: F401
from test_practice import finish_listening
from test_reading import start
from test_reading_ai import fake_stream, model_for, submit_payload
from test_writing import ESSAY, assessment, create


@pytest.mark.skipif(
    os.environ.get("ALUA_RUN_MISTAKES_BROWSER") != "1", reason="Isolated browser QA only"
)
def test_minimal_mistakes_real_review(listening, monkeypatch, tmp_path):  # noqa: F811
    from app.core.config import get_settings
    from app.modules.listening.ai_review import AIReview
    from app.modules.listening.models import ListeningAttemptRow
    from app.modules.reading import ai_review as reading_ai
    from app.modules.writing.catalog import import_tasks
    from app.modules.writing.contract import validate_assessment
    from app.modules.writing.models import WritingAttemptRow

    service, client, _, _ = listening
    device, _ = bootstrap(client, "husband")
    h = headers(device)
    original = finish_listening(client, h)
    listening_calls = []

    def generated(self, *args):
        listening_calls.append(1)
        return dict(
            what_happened="Saved listening explanation",
            why="The saved answer differs from the key.",
            next_time="Listen for the complete answer.",
            cached=True,
            evidence=dict(
                available=True,
                reason=None,
                part=1,
                quote="Synthetic audio fixture",
                segment_ids=["qa"],
                clip_start=1,
                clip_end=3,
            ),
        )

    monkeypatch.setattr(AIReview, "_generate", generated)
    assert (
        client.post(f"/api/v1/listening/attempts/{original}/ai-review/1", headers=h).status_code
        == 200
    )
    # Repeat saved attempts in the isolated fixture only. Production results are untouched.
    with service.db.session() as session:
        row = session.get(ListeningAttemptRow, original)
        saved_result = copy.deepcopy(row.result)
        for i in range(103):
            values = {c.name: copy.deepcopy(getattr(row, c.name)) for c in row.__table__.columns}
            values.update(id=str(uuid4()), submitted_at=datetime.now(UTC) - timedelta(days=i + 2))
            if i == 102:
                values["submitted_at"] = None
            session.add(ListeningAttemptRow(**values))
    reading, _ = start(client, h, eid="cambridge-07-test-01")
    qid = "cambridge-07-test-01-q-07"
    assert (
        client.post(
            f"/api/v1/reading/attempts/{reading['id']}/submit",
            headers=h,
            json=submit_payload(reading, {qid: "touch"}),
        ).status_code
        == 200
    )
    endpoint = f"/api/v1/reading/attempts/{reading['id']}/ai-review/{qid}"
    context = client.get(endpoint + "/context", headers=h).json()
    raw, reading_calls = model_for(context), []
    monkeypatch.setattr(get_settings(), "reading_ai_cache_root", str(tmp_path / "reading-cache"))
    monkeypatch.setattr(
        reading_ai.httpx,
        "stream",
        lambda *a, **kw: fake_stream(context, raw, reading_calls, *a, **kw),
    )
    response = client.post(endpoint, headers=h)
    assert response.status_code == 200, response.text
    import_tasks(service.db)
    writing = create(client, h)
    saved = client.put(
        f"/api/v1/writing/attempts/{writing['id']}",
        headers=h,
        json=dict(expected_version=0, essay=ESSAY),
    ).json()
    assert (
        client.post(
            f"/api/v1/writing/attempts/{writing['id']}/submit",
            headers=h,
            json=dict(expected_version=saved["version"]),
        ).status_code
        == 200
    )
    with service.db.session() as session:
        row = session.get(WritingAttemptRow, writing["id"])
        row.assessment = validate_assessment(assessment(), ESSAY)
        row.ai_status = "completed"
    page = client.get(
        "/api/v1/practice/mistakes?order=newest&include_reviews=false", headers=h
    ).json()
    assert page["total"] >= 106
    # The browser uses the real server/API and real original review components.
    server = uvicorn.Server(
        uvicorn.Config(client.app, host="127.0.0.1", port=3403, log_level="warning", lifespan="off")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        env = dict(
            os.environ,
            ALUA_MISTAKES_TEST_TOKEN=device["token"],
            ALUA_MISTAKES_TEST_UID=device["profile"]["uid"],
            ALUA_MISTAKES_TOTAL=str(page["total"]),
        )
        subprocess.run(
            ["node", "../work/mistakes-ui-20261116/browser-qa.cjs"],
            cwd=Path(__file__).resolve().parents[2] / "web",
            env=env,
            check=True,
            timeout=240,
        )
        assert len(listening_calls) == len(reading_calls) == 1
        with service.db.session() as session:
            assert session.get(ListeningAttemptRow, original).result == saved_result
    finally:
        server.should_exit = True
        thread.join(timeout=10)
