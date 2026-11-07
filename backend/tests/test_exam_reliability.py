"""Atomic final snapshots, real PostgreSQL plus actual TS controllers over local HTTP."""

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import pytest
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401
from test_listening import listening  # noqa: F401

from app.modules.exam_integrity import answers_checksum


@pytest.mark.parametrize("count", [15, 40])
@pytest.mark.parametrize("kind", ["listening", "reading"])
def test_atomic_final_snapshot_and_replay(listening, kind, count):  # noqa: F811
    _, client, _, _ = listening
    h = headers(bootstrap(client, "husband")[0])
    root = f"/api/v1/{kind}/attempts"
    create = {
        "event_id": str(uuid4()),
        "exam_id": "cambridge-14-test-01" if kind == "listening" else "cambridge-18-test-01",
        "reuse_active": False,
    }
    if kind == "reading":
        create["mode"] = "full_exam"
    a = client.post(root, headers=h, json=create).json()
    a = client.get(root + "/" + a["id"], headers=h).json()
    if kind == "listening":
        ids = [
            q["question_id"]
            for p in a["exam"]["parts"]
            for g in p["groups"]
            for q in g["questions"]
        ]
    else:
        ids = [
            q["id"]
            for p in a["exam"]["passages"]
            for g in p["question_groups"]
            for q in g["questions"]
        ]
    answers = {id: "fixture" if n < count else "" for n, id in enumerate(ids)}
    body = {
        "event_id": str(uuid4()),
        "expected_version": 0,
        "answers": answers,
        "answers_checksum": answers_checksum(answers, ids),
        "local_revision": count,
    }
    if kind == "listening":
        body["state"] = a["state"]
    url = root + "/" + a["id"]
    missing = {**body, "answers": {id: value for id, value in answers.items() if id != ids[-1]}}
    assert client.post(url + "/submit", headers=h, json=missing).status_code == 422
    stale_version = {**body, "expected_version": 9}
    assert client.post(url + "/submit", headers=h, json=stale_version).status_code == 409
    bad = {**body, "answers_checksum": "0" * 64}
    assert client.post(url + "/submit", headers=h, json=bad).status_code == 422
    assert client.get(url, headers=h).json()["answers"] == {}
    done = client.post(url + "/submit", headers=h, json=body)
    assert done.status_code == 200, done.text
    assert done.json()["final_snapshot_accepted"] is True
    assert done.json()["answers"] == answers
    assert client.post(url + "/submit", headers=h, json=body).json() == done.json()
    changed = {**body, "answers": {**answers, ids[0]: "changed"}}
    assert client.post(url + "/submit", headers=h, json=changed).status_code == 409
    changed["event_id"] = str(uuid4())
    assert client.post(url + "/submit", headers=h, json=changed).status_code == 422
    stale = {"event_id": str(uuid4()), "expected_version": 0, "answers": {ids[0]: "stale"}}
    if kind == "listening":
        stale["state"] = a["state"]
    client.post(url + "/sync", headers=h, json=stale)
    assert client.get(url, headers=h).json()["answers"] == answers
    result = client.get(url + "/result", headers=h).json()
    assert (
        sum(bool(q["user_answer"]) for q in result.get("questions", result.get("positions")))
        == count
    )


@pytest.mark.parametrize("legacy_rejection", [False, True])
def test_real_controllers_with_delayed_sync(listening, legacy_rejection):  # noqa: F811
    _, client, _, _ = listening
    auth = headers(bootstrap(client, "husband")[0])

    rejected = set()

    class Bridge(BaseHTTPRequestHandler):
        def do_GET(self):
            self.forward(None)

        def do_POST(self):
            self.forward(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))

        def forward(self, body):
            if legacy_rejection and self.path.endswith("/submit") and self.path not in rejected:
                from pydantic import ValidationError as SchemaError
                from starlette.responses import JSONResponse

                from app.modules.listening.schemas import Mutation

                try:
                    Mutation.model_validate(body)
                    raise AssertionError("Atomic snapshot must fail the legacy strict schema")
                except SchemaError as exc:
                    rejected.add(self.path)
                    response = JSONResponse(
                        {
                            "detail": [
                                {"loc": ["body", *e["loc"]], "type": e["type"]}
                                for e in exc.errors()
                            ]
                        },
                        status_code=422,
                    )
                    self.send_response(422)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(response.body)
                    return
            response = client.request(self.command, "/api/v1" + self.path, headers=auth, json=body)
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response.content)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Bridge)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [
                "node",
                "web/scripts/check-exam-reliability.mjs",
                "--backend",
                *(["--backend-hotfix"] if legacy_rejection else []),
            ],
            cwd=Path(__file__).resolve().parents[2],
            env={**os.environ, "RELIABILITY_TEST_URL": f"http://127.0.0.1:{server.server_port}"},
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        print(result.stdout.strip())
    finally:
        server.shutdown()
        server.server_close()


def test_reading_final_snapshot_deadline_and_checked_answers(system):  # noqa: F811
    from datetime import UTC, datetime, timedelta

    from app.core.exceptions import ConflictError
    from app.modules.reading.catalog import get_catalog
    from app.modules.reading.repository import ReadingRepository
    from app.modules.reading.schemas import CheckMutation, CreateAttempt, SubmitMutation
    from app.modules.reading.service import ReadingService

    db, client, _ = system
    uid = bootstrap(client, "husband")[0]["profile"]["uid"]
    now = [datetime(2026, 11, 7, tzinfo=UTC)]
    service = ReadingService(ReadingRepository(db), get_catalog(), clock=lambda: now[0])
    attempt = service.create(
        uid, CreateAttempt(event_id=uuid4(), exam_id="cambridge-18-test-01", mode="full_exam")
    )
    a = service.get(uid, attempt["id"])
    ids = list(
        service.catalog.exams[a["exam_id"]]["passages"][0]["question_groups"][0]["questions"]
    )
    # Entire final scope, not only the first group.
    from app.modules.reading.catalog import questions

    scope = list(questions(service.catalog.exams[a["exam_id"]]))
    answers = {qid: "late" for qid in scope}
    now[0] += timedelta(hours=2)
    final = SubmitMutation(
        event_id=uuid4(),
        expected_version=0,
        answers=answers,
        answers_checksum=answers_checksum(answers, scope),
        local_revision=40,
    )
    expired = service.mutate(uid, a["id"], "submit", final)
    assert expired["status"] == "expired"
    assert expired["final_snapshot_accepted"] is False
    assert expired["rejection_reason"] == "deadline_passed"
    assert expired["answers"] == {}
    assert service.result(uid, a["id"])["unanswered_count"] == 40

    practice = service.create(
        uid,
        CreateAttempt(
            event_id=uuid4(),
            exam_id="cambridge-18-test-01",
            mode="passage_practice",
            selected_passage=1,
        ),
    )
    qid = ids[0]["id"]
    checked = service.mutate(
        uid,
        practice["id"],
        "check",
        CheckMutation(event_id=uuid4(), expected_version=0, question_ids=[qid]),
    )
    practice_ids = [
        q["id"]
        for g in service.get(uid, practice["id"])["exam"]["passages"][0]["question_groups"]
        for q in g["questions"]
    ]
    answers = {id: "" for id in practice_ids}
    changed = {**answers, qid: "changed"}
    with pytest.raises(ConflictError):
        service.mutate(
            uid,
            practice["id"],
            "submit",
            SubmitMutation(
                event_id=uuid4(),
                expected_version=checked["version"],
                answers=changed,
                answers_checksum=answers_checksum(changed, practice_ids),
                local_revision=1,
            ),
        )
    accepted = service.mutate(
        uid,
        practice["id"],
        "submit",
        SubmitMutation(
            event_id=uuid4(),
            expected_version=checked["version"],
            answers=answers,
            answers_checksum=answers_checksum(answers, practice_ids),
            local_revision=1,
        ),
    )
    assert accepted["final_snapshot_accepted"] is True
