"""Real PostgreSQL history/AI/avatar checks; generated data and providers are test-only."""

# ruff: noqa: F811
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from PIL import Image
from sqlalchemy import func, select
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401
from test_listening import listening  # noqa: F401
from test_reading import start
from test_reading_ai import submit_payload
from test_writing import ESSAY, create

from app.modules.practice.models import SavedReviewRow, SpeakingAttemptRow
from app.modules.practice.service import PracticeService, streaks


def finish_listening(client, h):
    a = client.post(
        "/api/v1/listening/attempts",
        headers=h,
        json={"event_id": str(uuid4()), "exam_id": "cambridge-04-test-01", "reuse_active": False},
    ).json()
    base = "/api/v1/listening/attempts/" + a["id"]
    assert (
        client.post(
            base + "/sync",
            headers=h,
            json={
                "event_id": str(uuid4()),
                "expected_version": 0,
                "answers": {"cambridge-04-test-01-q01": "wrong"},
                "state": a["state"],
            },
        ).status_code
        == 200
    )
    submit = {"event_id": str(uuid4()), "expected_version": 1}
    r = client.post(base + "/submit", headers=h, json=submit)
    assert r.status_code == 200, r.text
    assert client.post(base + "/submit", headers=h, json=submit).json() == r.json()
    return a["id"]


def test_history_all_modules_ownership_and_activity(listening):
    service, client, _, _ = listening
    db = service.db
    owner = bootstrap(client, "husband")[0]
    other = bootstrap(client, "wife")[0]
    h = headers(owner)
    uid = owner["profile"]["uid"]
    first = finish_listening(client, h)
    second = finish_listening(client, h)
    assert first != second
    r, _ = start(client, h, eid="cambridge-07-test-01")
    qid = "cambridge-07-test-01-q-07"
    assert (
        client.post(
            f"/api/v1/reading/attempts/{r['id']}/submit",
            headers=h,
            json=submit_payload(r, {qid: "touch"}),
        ).status_code
        == 200
    )
    from app.modules.writing.catalog import import_tasks
    from app.modules.writing.models import WritingAttemptRow

    import_tasks(db)
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
    with db.session() as s:
        row = s.get(WritingAttemptRow, w["id"])
        row.assessment = {"estimated_band": 6.0}
        row.ai_status = "completed"
    task = json.loads(
        (Path(__file__).resolve().parents[2] / "web/src/features/speaking/content.json").read_text()
    )["questions"][0]
    body = {"event_id": str(uuid4()), "task_id": task["id"]}
    a = client.post("/api/v1/practice/speaking/attempts", headers=h, json=body)
    assert a.status_code == 201, a.text
    assert (
        client.post("/api/v1/practice/speaking/attempts", headers=h, json=body).json() == a.json()
    )
    page = client.get("/api/v1/practice/history", headers=h).json()
    assert page["total"] == 5 and {r["module"] for r in page["items"]} == {
        "listening",
        "reading",
        "writing",
        "speaking",
    }
    reading = next(r for r in page["items"] if r["module"] == "reading")
    assert reading["correct_count"] == 0 and reading["incorrect_count"] == 1
    assert reading["total_questions"] == 40 and reading["unanswered_count"] == 39
    assert client.get("/api/v1/practice/history", headers=headers(other)).json()["total"] == 0
    assert (
        client.get("/api/v1/practice/history/" + first, headers=headers(other)).status_code == 404
    )
    assert (
        client.get("/api/v1/practice/history/" + first, headers=h).json()["module"] == "listening"
    )
    assert (
        client.get("/api/v1/practice/history", headers=h, params={"limit": 2, "page": 2}).json()[
            "page"
        ]
        == 2
    )
    assert (
        client.get("/api/v1/practice/history", headers=h, params={"module": "reading"}).json()[
            "total"
        ]
        == 1
    )
    activity = client.get("/api/v1/practice/activity", headers=h).json()
    assert (
        activity["total_practice_sessions"] == 5 and sum(d["count"] for d in activity["days"]) == 5
    )
    assert activity["active_days"] == 1 and activity["current_streak"] == 1
    assert len(activity["days"]) == 365
    assert activity["days"][-1]["date"] == str(
        datetime.now(UTC).astimezone(ZoneInfo("Asia/Almaty")).date()
    )
    # Calendar days are real Almaty dates, not UTC days or number of attempts.
    from app.modules.listening.models import ListeningAttemptRow
    from app.modules.reading.models import ReadingAttemptRow

    with db.session() as s:
        for lid in (first, second):
            s.get(ListeningAttemptRow, lid).submitted_at = datetime(2026, 11, 10, tzinfo=UTC)
        s.get(ReadingAttemptRow, r["id"]).submitted_at = datetime(2026, 11, 10, tzinfo=UTC)
        s.get(WritingAttemptRow, w["id"]).completed_at = None  # legacy unknown date
        s.get(SpeakingAttemptRow, a.json()["id"]).completed_at = datetime(
            2026, 11, 14, 19, tzinfo=UTC
        )
    act = PracticeService(db).activity(uid, datetime(2026, 11, 15, 7, tzinfo=UTC))
    assert next(d for d in act["days"] if d["date"] == "2026-11-15")["count"] == 1
    assert next(d for d in act["days"] if d["date"] == "2026-11-14")["count"] == 0
    assert next(d for d in act["days"] if d["date"] == "2026-11-10")["count"] == 3
    assert act["undated_sessions"] == 1 and act["total_practice_sessions"] == 5
    with db.session() as s:
        s.get(ListeningAttemptRow, first).submitted_at = datetime(2026, 3, 10, tzinfo=UTC)
    annual = PracticeService(db).activity(uid, datetime(2026, 11, 15, 7, tzinfo=UTC))
    assert len(annual["days"]) == 365
    assert annual["days"][0]["date"] == "2025-11-16"
    assert annual["days"][-1]["date"] == "2026-11-15"
    assert next(d for d in annual["days"] if d["date"] == "2026-03-10")["count"] == 1
    assert annual["active_days"] == 2  # March practice is not a 30-day active day.
    older = client.get("/api/v1/practice/history", headers=h).json()
    assert next(x for x in older["items"] if x["module"] == "writing")["completed_at"] is None
    for aid in (r["id"], w["id"], a.json()["id"]):
        assert (
            client.get("/api/v1/practice/history/" + aid, headers=headers(other)).status_code == 404
        )


def test_saved_reviews_singleflight_failure_and_versions(listening, monkeypatch):
    service, client, _, _ = listening
    db = service.db
    owner = bootstrap(client, "husband")[0]
    other = bootstrap(client, "wife")[0]
    h = headers(owner)
    aid = finish_listening(client, h)
    base = f"/api/v1/listening/attempts/{aid}/ai-review/1"
    from app.modules.listening.ai_review import AIReview

    calls = []

    def generated(self, *args):
        calls.append(1)
        time.sleep(0.06)
        return {
            "what_happened": "QA explanation",
            "why": "QA reason",
            "next_time": "QA tip",
            "evidence": {
                "available": True,
                "part": 1,
                "quote": "QA",
                "segment_ids": ["qa"],
                "clip_start": 1,
                "clip_end": 3,
            },
            "cached": False,
        }

    monkeypatch.setattr(AIReview, "_generate", generated)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.post(base, headers=h), range(4)))
    assert all(r.status_code == 200 for r in responses) and len(calls) == 1
    read = f"/api/v1/practice/reviews/listening/{aid}"
    assert client.get(read, headers=h).json() == {"questions": ["1"]}
    assert client.get(read + "?question=1", headers=h).json()["response"]["why"] == "QA reason"
    assert client.get(read + "?question=2", headers=h).json() == {"response": None}
    assert client.get(read, headers=headers(other)).status_code == 404
    assert client.get(read).status_code == 401
    assert len(calls) == 1
    detail = client.get(f"/api/v1/practice/history/{aid}?include_reviews=false", headers=h).json()
    assert detail["saved_reviews"] == []
    lazy = client.get("/api/v1/practice/mistakes?include_reviews=false", headers=h).json()["items"][
        0
    ]
    assert lazy["saved_review"] is None and lazy["has_saved_review"] is True
    monkeypatch.setattr("app.modules.listening.ai_review.VERSION", "changed-prompt")
    assert client.post(base, headers=h).json()["cached"] is True and len(calls) == 1
    assert client.post(base, headers=headers(other)).status_code == 404
    second = finish_listening(client, h)
    assert (
        client.post(f"/api/v1/listening/attempts/{second}/ai-review/1", headers=h).status_code
        == 200
    )
    assert len(calls) == 2
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(SavedReviewRow)) == 2

    def failed(*args):
        raise ValueError("test failure")

    monkeypatch.setattr(AIReview, "_generate", failed)
    # Failure propagates without adding a successful stored response.
    from app.modules.practice.reviews import saved_review

    with pytest.raises(ValueError):
        saved_review(
            service, "listening", owner["profile"]["uid"], aid, "2", lambda: failed(), "test"
        )
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(SavedReviewRow)) == 2
    # Changed exact inputs must not reuse another answer revision.
    from app.modules.listening.models import ListeningAttemptRow

    with db.session() as s:
        row = s.get(ListeningAttemptRow, aid)
        row.answers = {**row.answers, "cambridge-04-test-01-q01": "other"}
    monkeypatch.setattr(AIReview, "_generate", generated)
    assert client.get(read + "?question=1", headers=h).json() == {"response": None}
    assert client.post(base, headers=h).status_code == 200 and len(calls) == 3


def test_avatar_binary_validation_ownership_and_reload(system):
    db, client, _ = system
    owner = bootstrap(client, "husband")[0]
    other = bootstrap(client, "wife")[0]
    h = headers(owner)
    image = io.BytesIO()
    Image.new("RGB", (400, 200), "green").save(image, "PNG")
    assert (
        client.put("/api/v1/practice/avatar", headers=h, content=b"<svg>bad</svg>").status_code
        == 422
    )
    assert (
        client.put(
            "/api/v1/practice/avatar", headers=h, content=b"x" * (2 * 1024 * 1024 + 1)
        ).status_code
        == 422
    )
    assert (
        client.put("/api/v1/practice/avatar", headers=h, content=image.getvalue()).status_code
        == 200
    )
    result = client.get("/api/v1/practice/avatar", headers=h)
    assert (
        result.headers["content-type"] == "image/webp"
        and result.content == client.get("/api/v1/practice/avatar", headers=h).content
    )
    assert Image.open(io.BytesIO(result.content)).size == (256, 256)
    assert client.get("/api/v1/practice/avatar", headers=headers(other)).status_code == 404
    assert client.get("/api/v1/practice/avatar").status_code == 401
    assert client.delete("/api/v1/practice/avatar", headers=h).status_code == 200
    assert client.get("/api/v1/practice/avatar", headers=h).status_code == 404


def test_streak_gaps_today_yesterday_and_empty():
    today = date(2026, 11, 15)
    assert streaks([], today) == (0, 0)
    assert streaks([today, today, today - timedelta(days=1)], today) == (2, 2)
    assert streaks([today - timedelta(days=1)], today) == (1, 1)
    assert streaks([today - timedelta(days=3), today - timedelta(days=4)], today) == (0, 2)


def test_continue_mistakes_and_analytics_projections(listening, monkeypatch):
    from test_writing import assessment

    from app.modules.listening.ai_review import AIReview
    from app.modules.listening.models import ListeningAttemptRow
    from app.modules.reading.models import ReadingAttemptRow
    from app.modules.writing.catalog import import_tasks
    from app.modules.writing.contract import validate_assessment
    from app.modules.writing.models import WritingAttemptRow

    service, client, _, _ = listening
    owner = bootstrap(client, "husband")[0]
    other = bootstrap(client, "wife")[0]
    h = headers(owner)
    aid = finish_listening(client, h)
    base = "/api/v1/practice"
    calls = []

    def generate(self, *args):
        calls.append(1)
        return dict(
            what_happened="QA stored explanation",
            why="QA wrong answer",
            next_time="QA tip",
            cached=False,
            evidence=dict(
                available=True, reason=None, part=1, clip_start=1, clip_end=3, quote="QA"
            ),
        )

    monkeypatch.setattr(AIReview, "_generate", generate)
    assert (
        client.post(f"/api/v1/listening/attempts/{aid}/ai-review/1", headers=h).status_code == 200
    )
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
        f"/api/v1/writing/attempts/{w['id']}", headers=h, json=dict(expected_version=0, essay=ESSAY)
    ).json()
    assert (
        client.post(
            f"/api/v1/writing/attempts/{w['id']}/submit",
            headers=h,
            json=dict(expected_version=saved["version"]),
        ).status_code
        == 200
    )
    with service.db.session() as s:
        wr = s.get(WritingAttemptRow, w["id"])
        wr.assessment = validate_assessment(assessment(), ESSAY)
        wr.ai_status = "completed"
        before = s.get(ListeningAttemptRow, aid).result.copy()
    mistakes = client.get(base + "/mistakes", headers=h)
    assert mistakes.status_code == 200, mistakes.text
    m = mistakes.json()
    assert m["total"] == 3
    assert (
        len(
            next(x for x in m["items"] if x["module"] == "writing")["feedback"][
                "assessment_criteria"
            ]
        )
        == 4
    )
    item = next(x for x in m["items"] if x["module"] == "listening")
    assert item["saved_review"]["what_happened"] == "QA stored explanation" and len(calls) == 1
    state = {k: item[k] for k in ("module", "attempt_id", "item_key")} | dict(reviewed=True)
    assert (
        client.put(base + "/mistakes/state", headers=headers(other), json=state).status_code == 404
    )
    for _ in range(2):
        assert client.put(base + "/mistakes/state", headers=h, json=state).status_code == 200
    assert (
        client.get(base + "/mistakes", headers=h, params=dict(search="wrong")).json()["total"] == 1
    )
    assert (
        client.get(base + "/mistakes", headers=h, params=dict(module="listening", limit=1)).json()[
            "items"
        ][0]["reviewed"]
        is True
    )
    stats = client.get(base + "/analytics", headers=h)
    assert stats.status_code == 200, stats.text
    stats = stats.json()
    assert stats["counts"] == dict(listening=1, reading=1, writing=1, speaking=0)
    assert stats["mistakes"] == dict(total=3, reviewed=1)
    assert len(stats["charts"]["listening"]["points"]) == 1
    assert stats["charts"]["writing"]["points"][0]["value"] == 6
    assert len(stats["writing_criteria"]) == 4
    assert stats["charts"]["writing"]["points"][0]["title"]
    assert stats["charts"]["writing"]["points"][0]["attempt_number"] >= 1
    import os

    if output := os.environ.get("ALUA_ANALYTICS_WRITING_QA_OUTPUT"):
        Path(output).write_text(json.dumps(stats))
    assert all(x["incorrect"] <= x["answered"] for x in stats["weak_areas"])
    assert stats["speaking_assessment_available"] is False and len(calls) == 1
    for path in ("/drafts", "/mistakes", "/analytics"):
        assert client.get(base + path).status_code == 401
    assert client.get(base + "/mistakes", headers=headers(other)).json()["total"] == 0
    assert (
        sum(client.get(base + "/analytics", headers=headers(other)).json()["counts"].values()) == 0
    )
    draft = client.post(
        "/api/v1/listening/attempts",
        headers=h,
        json=dict(event_id=str(uuid4()), exam_id="cambridge-04-test-01", reuse_active=False),
    ).json()
    rr, _ = start(client, h, eid="cambridge-18-test-01")
    body = dict(
        event_id=str(uuid4()),
        expected_version=0,
        answers={},
        navigation=dict(current_passage=1, current_question_id="cambridge-18-test-01-q-02"),
    )
    nav = client.post(f"/api/v1/reading/attempts/{rr['id']}/sync", headers=h, json=body)
    assert nav.status_code == 200, nav.text
    assert nav.json()["state"]["current_question_id"] == body["navigation"]["current_question_id"]
    assert (
        client.post(f"/api/v1/reading/attempts/{rr['id']}/sync", headers=h, json=body).json()
        == nav.json()
    )
    assert (
        client.post(
            f"/api/v1/reading/attempts/{rr['id']}/sync",
            headers=h,
            json={**body, "event_id": str(uuid4())},
        ).status_code
        == 409
    )
    writing_draft = create(client, h)
    active = client.get(base + "/drafts", headers=h).json()
    assert active["total"] == 3 and {x["id"] for x in active["items"]} == {
        draft["id"],
        rr["id"],
        writing_draft["id"],
    }
    assert client.get(base + "/drafts", headers=headers(other)).json()["total"] == 0
    with service.db.session() as s:
        s.get(ReadingAttemptRow, rr["id"]).deadline_at = datetime.now(UTC) - timedelta(seconds=1)
        assert s.get(ListeningAttemptRow, aid).result == before
        s.get(WritingAttemptRow, w["id"]).completed_at = None
    assert client.get(base + "/drafts", headers=h).json()["total"] == 2
    assert not client.get(base + "/analytics", headers=h).json()["charts"]["writing"]["points"]
    assert (
        client.get(base + "/analytics", headers=h, params=dict(period="all")).json()["counts"][
            "writing"
        ]
        == 1
    )


def test_history_day_filter_actual_dates_and_bounded_queries(listening):
    from sqlalchemy import event

    from app.modules.listening.models import ListeningAttemptRow

    service, client, _, _ = listening
    owner = bootstrap(client, "husband")[0]
    h = headers(owner)
    ids = [finish_listening(client, h) for _ in range(4)]
    with service.db.session() as s:
        s.get(ListeningAttemptRow, ids[0]).submitted_at = datetime(2026, 11, 1, 20, tzinfo=UTC)
        s.get(ListeningAttemptRow, ids[1]).submitted_at = datetime(2026, 11, 1, 18, tzinfo=UTC)
    result = client.get("/api/v1/practice/history?day=2026-11-02", headers=h).json()
    assert [r["id"] for r in result["items"]] == [ids[0]]
    assert client.get("/api/v1/practice/history?day=bad", headers=h).status_code == 422
    queries = []
    engine = service.db.engine

    def count(*args):
        queries.append(1)

    event.listen(engine, "before_cursor_execute", count)
    try:
        PracticeService(service.db).history(owner["profile"]["uid"])
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert len(queries) <= 4  # count + page + one module bulk read + grouped review counts


def test_analytics_attempt_metadata_and_separate_denominators(listening, tmp_path):
    """Read projection only: repeated attempts, owner isolation and honest denominators."""
    from app.modules.listening.models import ListeningAttemptRow
    from app.modules.reading.models import ReadingAttemptRow

    service, client, _, _ = listening
    owner = bootstrap(client, "husband")[0]
    h = headers(owner)
    ids = [finish_listening(client, h) for _ in range(3)]
    now = datetime.now(UTC)
    with service.db.session() as s:
        for i, aid in enumerate(ids):
            row = s.get(ListeningAttemptRow, aid)
            row.submitted_at = now - timedelta(days=65 - i * 30)
        row = s.get(ListeningAttemptRow, ids[0])
        result = dict(row.result)
        questions = [dict(q) for q in result["questions"]]
        # Fixture adds one answered but ungraded question, separate from unanswered.
        questions[1].update(user_answer="pending", correct=None)
        result["questions"] = questions
        row.result = result
    r, _ = start(client, h, eid="cambridge-07-test-01")
    response = client.post(
        f"/api/v1/reading/attempts/{r['id']}/submit",
        headers=h,
        json=submit_payload(r, {"cambridge-07-test-01-q-07": "touch"}),
    )
    assert response.status_code == 200
    snapshots = {}
    for period, expected in [("30", 1), ("90", 3), ("all", 3)]:
        response = client.get("/api/v1/practice/analytics", headers=h, params={"period": period})
        assert response.status_code == 200, response.text
        stats = response.json()
        points = stats["charts"]["listening"]["points"]
        assert len(points) == expected
        assert points[-1]["attempt_number"] == 3 and points[-1]["attempt_count"] == 3
        assert points[-1]["title"] == "Cambridge 4 · Test 1"
        assert len({p["id"] for p in points}) == expected
        assert [p["date"] for p in points] == sorted(p["date"] for p in points)
        assert stats["charts"]["listening"]["scale"] == 40
        assert stats["charts"]["writing"]["scale"] == 9
        assert stats["speaking_assessment_available"] is False
        assert all(
            a["incorrect"] <= a["answered"] and a["incorrect_attempts"] <= a["attempts"]
            for a in stats["weak_areas"]
        )
        snapshots[period] = stats
    assert sum(a["not_graded"] for a in snapshots["all"]["weak_areas"]) >= 1
    assert (
        sum(a["answered"] for a in snapshots["all"]["weak_areas"] if a["module"] == "listening")
        == 3
    )
    assert snapshots["all"]["charts"]["reading"]["points"][0]["id"] == r["id"]
    assert snapshots["all"]["charts"]["reading"]["points"][0]["title"] == "Cambridge 7 · Test 1"
    # No writes by the analytics endpoint.
    with service.db.session() as s:
        assert s.get(ListeningAttemptRow, ids[0]).result == result
        s.get(ReadingAttemptRow, r["id"]).submitted_at = None
    assert not client.get("/api/v1/practice/analytics", headers=h).json()["charts"]["reading"][
        "points"
    ]
    other = bootstrap(client, "wife")[0]
    assert not client.get("/api/v1/practice/analytics", headers=headers(other)).json()["charts"][
        "reading"
    ]["points"]
    # Optional browser QA input: actual API projections from disposable PostgreSQL.
    import os

    if output := os.environ.get("ALUA_ANALYTICS_QA_OUTPUT"):
        Path(output).write_text(json.dumps(snapshots))
