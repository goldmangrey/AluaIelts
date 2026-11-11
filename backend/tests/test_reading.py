"""Reading uses the existing disposable PostgreSQL cluster and real device enrollment."""

# ruff: noqa: F811
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401

from app.core.exceptions import ConflictError
from app.modules.reading.catalog import ReadingCatalog, get_catalog, questions
from app.modules.reading.grading import constrained_answer, estimated_band, result_for
from app.modules.reading.models import ReadingAttemptRow, ReadingMutationRow
from app.modules.reading.repository import ReadingRepository
from app.modules.reading.schemas import AnswerMutation, CreateAttempt, SubmitMutation
from app.modules.reading.service import ReadingService

EID = "cambridge-18-test-01"
BASE = "/api/v1/reading"


def event(version=0, **extra):
    return {"event_id": str(uuid4()), "expected_version": version, **extra}


def start(client, h, mode="full_exam", eid=EID, passage=1):
    payload = {"event_id": str(uuid4()), "exam_id": eid, "mode": mode}
    if mode == "passage_practice":
        payload["selected_passage"] = passage
    response = client.post(BASE + "/attempts", headers=h, json=payload)
    assert response.status_code == 201, response.text
    return response.json(), payload


def perfect(key):
    answers = {a["question_id"]: a["accepted_answers"][0] for a in key["answers"]}
    seen = set()
    for a in key["answers"]:
        if a["grading"]["mode"] == "unordered_parts":
            answers[a["question_id"]] = " ".join(p[0] for p in a["grading"]["parts"])
        group = a["grading_group"]
        if group and group["id"] not in seen:
            seen.add(group["id"])
            members = [
                k
                for k in key["answers"]
                if k["grading_group"] and k["grading_group"]["id"] == group["id"]
            ]
            for member, unit in zip(members, group["expected_units"], strict=True):
                answers[member["question_id"]] = unit[0]
    return answers


def test_catalog_and_all_grading_types():
    c = get_catalog()
    assert len(c.entries) == 72 and len(c.assets) == 60 + len(c.manifest.get("retained_assets", []))
    enabled = [e for e in c.entries.values() if e["enabled_for_private_practice"]]
    assert len(enabled) == 69
    assert all(e["content_status"] == "needs_review" and e["not_fully_proofread"] for e in enabled)
    assert not any(
        e["enabled_for_private_practice"]
        for e in c.entries.values()
        if e["content_status"] == "blocked"
    )
    types = set()
    for entry in enabled:
        eid = entry["exam_id"]
        exam, key = c.exams[eid], c.keys[eid]
        snapshot = {"exam": exam, "key": key, "metadata": entry}
        answers = perfect(key)
        result = result_for(snapshot, answers, "full_exam", None, 100, {})
        assert result["raw_score"] == 40, (
            eid,
            [p for p in result["positions"] if not p["is_correct"]],
        )
        assert result["estimated_band"] == 9
        assert sum(r["correct"] for r in result["per_passage"].values()) == 40
        assert result_for(snapshot, {}, "full_exam", None, 100, {})["raw_score"] == 0
        types.update(q[2]["type"] for q in questions(exam).values())
    assert len(types) == 15
    for score, band in [(4, 2.5), (10, 4), (15, 5), (23, 6), (26, 6), (30, 7), (35, 8), (40, 9)]:
        assert estimated_band(score) == band
    assert estimated_band(0) is None
    assert estimated_band(3) is None
    with pytest.raises(ValueError):
        estimated_band(41)


def test_alternatives_and_unordered_semantics():
    c = get_catalog()
    pairs = compounds = alternatives = 0
    for eid, exam in c.exams.items():
        key = c.keys[eid]
        snapshot = {"exam": exam, "key": key, "metadata": c.entries[eid]}
        for a in key["answers"]:
            if (
                len(a["accepted_answers"]) > 1
                and not a["grading_group"]
                and a["grading"]["mode"] == "variants"
            ):
                qid = a["question_id"]
                for value in a["accepted_answers"]:
                    result = result_for(snapshot, {qid: value.upper()}, "full_exam", None, 0, {})
                    assert next(p for p in result["positions"] if p["question_id"] == qid)[
                        "is_correct"
                    ], (eid, qid, value)
                alternatives += 1
            group = a["grading_group"]
            if group and group["mode"] == "unordered_unique":
                members = [
                    k
                    for k in key["answers"]
                    if k["grading_group"] and k["grading_group"]["id"] == group["id"]
                ]
                ids = [m["question_id"] for m in members]
                values = [unit[0] for unit in group["expected_units"]]
                reverse = dict(zip(ids, reversed(values), strict=True))
                assert result_for(snapshot, reverse, "full_exam", None, 0, {})["raw_score"] == len(
                    ids
                )
                duplicate = dict.fromkeys(ids, values[0])
                assert result_for(snapshot, duplicate, "full_exam", None, 0, {})["raw_score"] == 1
                pairs += 1
            if a["grading"]["mode"] == "unordered_parts":
                qid = a["question_id"]
                parts = [p[0] for p in a["grading"]["parts"]]
                assert (
                    result_for(
                        snapshot, {qid: " ".join(reversed(parts))}, "full_exam", None, 0, {}
                    )["raw_score"]
                    == 1
                )
                assert (
                    result_for(snapshot, {qid: parts[0]}, "full_exam", None, 0, {})["raw_score"]
                    == 0
                )
                compounds += 1
    assert pairs and compounds and alternatives
    q = {"answer_input_type": "text", "constraints": {"max_words": 1, "allow_number": False}}
    assert constrained_answer("one two", q) == ""
    assert constrained_answer("well-known", q) == "well-known"
    assert constrained_answer("100", q) == ""


def test_full_lifecycle_isolation_and_restart(system):
    db, client, _ = system
    a, b = [bootstrap(client, role)[0] for role in ("husband", "wife")]
    h, other = headers(a), headers(b)
    assert client.post("/api/v1/bootstrap", json={}).status_code == 404
    assert client.get(BASE + "/books").status_code == 401
    library = client.get(BASE + "/exams", headers=h).json()["items"]
    assert sum(e["enabled_for_private_practice"] for e in library) == 69
    assert all(e["best_estimated_band"] is None for e in library)
    assert len(client.get(BASE + "/books", headers=h).json()["items"]) == 18
    exam = client.get(BASE + "/exams/" + EID, headers=h).json()
    assert len(exam["passages"]) == 3 and len(questions(exam)) == 40
    public = json.dumps(exam).lower()
    assert not any(
        word in public for word in ["canonical_answer", "accepted_answers", "answer_key_path"]
    )
    for e in library:
        if not e["enabled_for_private_practice"]:
            assert client.get(BASE + "/exams/" + e["exam_id"], headers=h).status_code == 404
    attempt, payload = start(client, h)
    aid = attempt["id"]
    path = BASE + "/attempts/" + aid
    assert client.post(BASE + "/attempts", headers=h, json=payload).json()["id"] == aid
    assert client.get(path, headers=other).status_code == 404
    assert client.get(path + "/result", headers=h).status_code == 409
    assert client.get(path + "/result", headers=other).status_code == 404
    qid = EID + "-q-01"
    change = event(answer="first")
    assert client.put(path + "/answers/" + qid, headers=other, json=change).status_code == 404
    saved = client.put(path + "/answers/" + qid, headers=h, json=change)
    assert saved.status_code == 200 and saved.json()["version"] == 1
    assert saved.headers["cache-control"] == "no-store"
    assert client.put(path + "/answers/" + qid, headers=h, json=change).json() == saved.json()
    assert (
        client.put(
            path + "/answers/" + qid, headers=h, json=change | {"answer": "different"}
        ).status_code
        == 409
    )
    assert (
        client.put(path + "/answers/" + qid, headers=h, json=event(answer="stale")).status_code
        == 409
    )
    changed = client.put(path + "/answers/" + qid, headers=h, json=event(1, answer="new"))
    assert changed.json()["version"] == 2
    # New app and new DB connection pool: all state lives in PostgreSQL.
    from app.main import create_app

    db.engine.dispose()
    get_catalog.cache_clear()
    with TestClient(create_app()) as restarted:
        resumed = restarted.get(path, headers=h).json()
        assert resumed["answers"][qid] == "new"
        assert resumed["deadline_at"] == attempt["deadline_at"]
        assert resumed["exam"]["id"] == EID
    assert client.get(BASE + "/attempts", headers=other).json()["items"] == []
    answers = perfect(get_catalog().keys[EID])
    batch = event(2, answers=answers)
    synced = client.post(path + "/sync", headers=h, json=batch)
    assert synced.status_code == 200 and synced.json()["version"] == 3
    assert client.post(path + "/sync", headers=h, json=batch).json() == synced.json()
    submit = event(3)
    done = client.post(path + "/submit", headers=h, json=submit)
    assert done.status_code == 200, done.text
    result = done.json()["result"]
    assert result["raw_score"] == 40 and result["estimated_band"] == 9
    assert result["band_label"] == "Estimated IELTS Academic Reading Band"
    assert result["correct_count"] == 40 and result["unanswered_count"] == 0
    assert client.post(path + "/submit", headers=h, json=submit).json() == done.json()
    assert client.post(path + "/submit", headers=h, json=event()).json()["result"] == result
    assert (
        client.put(path + "/answers/" + qid, headers=h, json=event(4, answer="x")).status_code
        == 409
    )
    assert (
        client.post(path + "/sync", headers=h, json=event(4, answers={qid: "x"})).status_code == 409
    )
    assert (
        client.patch(path + "/state", headers=h, json=event(4, current_passage=1)).status_code
        == 409
    )
    assert client.get(path + "/result", headers=h).json() == result
    entry = next(
        e for e in client.get(BASE + "/exams", headers=h).json()["items"] if e["exam_id"] == EID
    )
    assert entry["completed_attempts"] == 1 and entry["best_estimated_band"] == 9
    with db.session() as s:
        assert s.scalar(select(ReadingAttemptRow)).result == result


def test_passage_checks_annotations_and_group_freeze(system):
    db, client, _ = system
    h = headers(bootstrap(client, "husband")[0])
    attempt, _ = start(client, h, "passage_practice")
    path = BASE + "/attempts/" + attempt["id"]
    resumed = client.get(path, headers=h).json()
    assert resumed["deadline_at"] is None and len(resumed["exam"]["passages"]) == 1
    p = resumed["exam"]["passages"][0]
    qids = list(questions(resumed["exam"]))
    outside = EID + "-q-40"
    assert (
        client.put(path + "/answers/" + outside, headers=h, json=event(answer="X")).status_code
        == 422
    )
    block = p["content"][0]["text"]
    annotation = {
        "id": str(uuid4()),
        "passage_id": p["id"],
        "content_hash": attempt["content_hash"],
        "block_index": 0,
        "start": 0,
        "end": 4,
        "quote": block[:4],
        "color": "yellow",
        "note": "note",
    }
    state = event(current_passage=1, annotations=[annotation])
    assert (
        client.patch(path + "/state", headers=h, json=state | {"deadline_at": "2099"}).status_code
        == 422
    )
    saved = client.patch(path + "/state", headers=h, json=state)
    assert saved.status_code == 200, saved.text
    assert client.get(path, headers=h).json()["state"]["annotations"] == [annotation]
    bad = copy.deepcopy(annotation)
    bad["content_hash"] = "0" * 64
    assert (
        client.patch(
            path + "/state", headers=h, json=event(1, current_passage=1, annotations=[bad])
        ).status_code
        == 422
    )
    answers = {qid: value for qid, value in perfect(get_catalog().keys[EID]).items() if qid in qids}
    assert client.post(path + "/sync", headers=h, json=event(1, answers=answers)).status_code == 200
    checked = client.post(path + "/check", headers=h, json=event(2, question_ids=[qids[0]]))
    assert checked.status_code == 200, checked.text
    revealed = checked.json()["checked_result"]["positions"]
    assert len(revealed) == 1 and revealed[0]["question_id"] == qids[0]
    assert (
        client.put(path + "/answers/" + qids[0], headers=h, json=event(3, answer="X")).status_code
        == 409
    )
    done = client.post(path + "/submit", headers=h, json=event(3)).json()["result"]
    assert done["raw_score"] == len(qids) and done["estimated_band"] is None
    assert done["accuracy"] == 1 and len(done["per_passage"]) == 1
    # Choose TWO is revealed/frozen atomically, other questions stay private.
    c = get_catalog()
    eid, pnum, group = next(
        (eid, p["number"], g)
        for eid, e in c.exams.items()
        if c.entries[eid]["enabled_for_private_practice"]
        for p in e["passages"]
        for g in p["question_groups"]
        if g["type"] == "multiple_choice_multiple"
    )
    attempt, _ = start(client, h, "passage_practice", eid, pnum)
    path = BASE + "/attempts/" + attempt["id"]
    qid = group["questions"][0]["id"]
    checked = client.post(path + "/check", headers=h, json=event(question_ids=[qid])).json()
    ids = {r["question_id"] for r in checked["checked_result"]["positions"]}
    assert len(ids) > 1 and ids <= set(checked["state"]["checked_question_ids"])
    assert (
        client.put(
            path + "/answers/" + next(iter(ids)), headers=h, json=event(1, answer="A")
        ).status_code
        == 409
    )


def test_deadline_and_concurrent_mutations(system):
    db, client, _ = system
    a = bootstrap(client, "husband")[0]
    uid = a["profile"]["uid"]
    now = datetime(2026, 11, 1, 10, tzinfo=UTC)
    clock = [now]
    service = ReadingService(ReadingRepository(db), get_catalog(), clock=lambda: clock[0])
    attempt = service.create(uid, CreateAttempt(event_id=uuid4(), exam_id=EID, mode="full_exam"))
    aid = attempt["id"]
    qid = EID + "-q-01"
    first = AnswerMutation(event_id=uuid4(), expected_version=0, answer="A")
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(
            pool.map(lambda _: service.mutate(uid, aid, "answer", first, question_id=qid), range(4))
        )
    assert len({v["version"] for v in values}) == 1

    def conflicting(value):
        try:
            return service.mutate(
                uid,
                aid,
                "answer",
                AnswerMutation(event_id=uuid4(), expected_version=1, answer=value),
                question_id=qid,
            )
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(conflicting, ["B", "C"]))
    assert values.count("conflict") == 1
    clock[0] = now + timedelta(seconds=3600)
    expired = service.mutate(
        uid,
        aid,
        "answer",
        AnswerMutation(event_id=uuid4(), expected_version=2, answer="late"),
        question_id=qid,
    )
    assert expired["status"] == "expired" and expired["mutation_applied"] is False
    assert expired["answers"][qid] != "late" and expired["remaining_seconds"] == 0
    assert service.result(uid, aid)["elapsed_seconds"] == 3600
    assert service.result(uid, aid)["timing_status"] == "server_deadline_enforced"
    assert (
        service.mutate(uid, aid, "submit", SubmitMutation(event_id=uuid4(), expected_version=0))[
            "status"
        ]
        == "expired"
    )
    # A GET lazily expires abandoned exams too; no worker/cron is required.
    clock[0] = now
    another = service.create(uid, CreateAttempt(event_id=uuid4(), exam_id=EID, mode="full_exam"))
    clock[0] = now + timedelta(hours=3)
    assert service.get(uid, another["id"])["status"] == "expired"
    assert service.result(uid, another["id"])["unanswered_count"] == 40
    with db.session() as s:
        events = s.scalars(
            select(ReadingMutationRow).where(ReadingMutationRow.attempt_id == aid)
        ).all()
        assert len(events) == 5  # create, one duplicate event, winning CAS, late reject, submit


def test_assets_and_request_scope(system):
    _, client, _ = system
    h = headers(bootstrap(client, "husband")[0])
    aid = next(iter(get_catalog().assets))
    path = BASE + "/assets/" + aid
    response = client.get(path, headers=h)
    assert response.status_code == 200 and response.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"].startswith("private")
    assert (
        client.get(path, headers=h | {"If-None-Match": response.headers["etag"]}).status_code == 304
    )
    assert client.get(path).status_code == 401
    for bad in ["/assets/manifest.json", "/assets/%2e%2e%2fanswer_keys", "/assets/..%2F..%2F.env"]:
        assert client.get(BASE + bad, headers=h).status_code == 404
    attempt, _ = start(client, h)
    path = BASE + "/attempts/" + attempt["id"]
    assert (
        client.post(
            path + "/check", headers=h, json=event(question_ids=[EID + "-q-01"])
        ).status_code
        == 409
    )
    assert (
        client.put(
            path + "/answers/" + EID + "-q-01",
            headers=h,
            json=event(answer="A", learner_id=str(uuid4())),
        ).status_code
        == 422
    )
    assert (
        client.post(
            BASE + "/attempts",
            headers=h,
            json={
                "event_id": str(uuid4()),
                "exam_id": EID,
                "mode": "full_exam",
                "duration_seconds": 9999,
            },
        ).status_code
        == 422
    )


def test_migration_from_previous_revision(system):
    db, _, cfg = system
    from alembic.script import ScriptDirectory

    from alembic import command

    # Existing initial migration builds current metadata. Simulate an actual 0004 DB
    # without Reading-owned tables, then run ONLY the additive upgrade under test.
    with db.engine.begin() as conn:
        ReadingMutationRow.__table__.drop(conn)
        ReadingAttemptRow.__table__.drop(conn)
        conn.execute(text("UPDATE alembic_version SET version_num='20261031_0004'"))
    command.upgrade(cfg, "head")
    with db.session() as s:
        assert (
            s.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == ScriptDirectory.from_config(cfg).get_current_head()
        )
        assert s.execute(text("SELECT count(*) FROM reading_attempts")).scalar() == 0


def test_historical_snapshot_and_band_integration(system):
    db, client, _ = system
    h = headers(bootstrap(client, "husband")[0])
    c = get_catalog()
    for count, band in [(23, 6.0), (30, 7.0), (35, 8.0)]:
        attempt, _ = start(client, h)
        path = BASE + "/attempts/" + attempt["id"]
        answers = dict(list(perfect(c.keys[EID]).items())[:count])
        assert (
            client.post(path + "/sync", headers=h, json=event(answers=answers)).status_code == 200
        )
        done = client.post(path + "/submit", headers=h, json=event(1)).json()["result"]
        assert done["raw_score"] == count and done["estimated_band"] == band
        assert done["unanswered_count"] == 40 - count
        assert done["attempt_id"] == attempt["id"]
    # Changes in a later in-memory catalog cannot rewrite an existing attempt snapshot.
    attempt, _ = start(client, h)
    path = BASE + "/attempts/" + attempt["id"]
    answers = perfect(c.keys[EID])
    client.post(path + "/sync", headers=h, json=event(answers=answers))
    later = copy.copy(c)
    later.keys = copy.deepcopy(c.keys)
    later.exams = copy.deepcopy(c.exams)
    later.keys[EID]["answers"][0]["accepted_answers"] = ["new content"]
    later.exams[EID]["passages"][0]["title"] = "changed title"
    service = ReadingService(ReadingRepository(db), later)
    uid = bootstrap(client, "wife")[0]["profile"]["uid"]
    with pytest.raises(Exception) as denied:
        service.get(uid, attempt["id"])
    assert denied.value.code == "reading_attempt_not_found"
    with db.session() as session:
        owner = session.get(ReadingAttemptRow, attempt["id"]).learner_id
    assert service.get(owner, attempt["id"])["exam"]["passages"][0]["title"] != "changed title"
    result = service.mutate(
        owner, attempt["id"], "submit", SubmitMutation(event_id=uuid4(), expected_version=1)
    )["result"]
    assert result["raw_score"] == 40
    assert result["content_hash"] == attempt["content_hash"]


def test_catalog_isolates_invalid_exam(tmp_path):
    import shutil

    from app.modules.reading.catalog import DATASET

    shutil.copytree(DATASET, tmp_path / "dataset")
    base = tmp_path / "dataset"
    manifest = json.loads((base / "manifest.json").read_text())
    entry = next(e for e in manifest["exams"] if e["id"] == EID)
    path = base / entry["exam_path"]
    exam = json.loads(path.read_text())
    exam["passages"][0]["question_groups"][0]["questions"].pop()
    path.write_text(json.dumps(exam))
    damaged = ReadingCatalog(base)
    assert not damaged.entries[EID]["enabled_for_private_practice"]
    assert "incomplete_exam" in damaged.entries[EID]["exclusion_reasons"]
    assert sum(e["enabled_for_private_practice"] for e in damaged.entries.values()) == 68
