"""Stage 3 end-to-end coverage using an isolated PostgreSQL cluster."""

# ruff: noqa: F811
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401


def test_catalog_and_program():
    from app.modules.study.catalog import catalog

    c = catalog()
    for level in ["A1", "B2", None]:
        days = c.program(level)
        assert len(days) == 50
        assert all(len(d["ids"]) == 30 for d in days)
        assert len({i for d in days for i in d["ids"]}) == 1500
    assert all(c.by_id[i].cefr_level in {"A1", "A2"} for i in c.program("A1")[0]["ids"])
    assert all(c.by_id[i].cefr_level == "B2" for i in c.program("B2")[0]["ids"])


def test_study_lifecycle(system):
    from app.db.models import ReviewResponseRow, StudyEventRow
    from app.modules.study.router import StudyAction
    from app.modules.study.service import StudyService

    db, client, _ = system
    a, b = [bootstrap(client, role)[0] for role in ("husband", "wife")]
    uid = a["profile"]["uid"]
    service = StudyService(db)
    now = datetime(2026, 11, 1, 5, tzinfo=UTC)
    initial = service.snapshot(uid, now)
    ids = initial["days"][0]["ids"]
    assert service.snapshot(b["profile"]["uid"], now)["processed"] == 0
    requests = []
    for i in ids[:10]:
        request = StudyAction(event_id=uuid4(), item_id=i, action="next")
        requests.append(request)
        service.act(uid, request, now)
        service.act(uid, request, now)
    resumed = StudyService(db).snapshot(uid, now + timedelta(days=4))
    assert resumed["day"] == 1 and resumed["processed"] == 10
    assert resumed["cards"][0]["id"] == ids[10]
    assert len(resumed["book"]) == 10
    for i in ids[10:]:
        service.act(
            uid, StudyAction(event_id=uuid4(), item_id=i, action="known"), now + timedelta(days=4)
        )
    done = service.snapshot(uid, now + timedelta(days=4))
    assert done["days"][0]["complete"] and not done["available"]
    assert done["day"] == 2
    tomorrow = service.snapshot(uid, now + timedelta(days=5))
    assert tomorrow["day"] == 2 and tomorrow["available"] and len(tomorrow["book"]) == 30
    h = headers(a)
    card = service.catalog.by_id[ids[0]]
    for q in (card.term, card.translation_ru):
        found = client.get("/api/v1/study/book", headers=h, params={"q": q})
        assert found.status_code == 200, found.text
        assert ids[0] in [c["id"] for c in found.json()["cards"]]
    review = StudyAction(event_id=uuid4(), item_id=ids[0], action="review", answer=None)
    service.act(uid, review, now + timedelta(days=5))
    service.act(uid, review, now + timedelta(days=5))
    state = service.snapshot(uid, now + timedelta(days=5))
    assert state["processed"] == 0
    assert next(c for c in state["book"] if c["id"] == ids[0])["status"] != "retained"
    service.act(uid, StudyAction(event_id=uuid4(), item_id=ids[0], action="hide"), now)
    assert (
        next(c for c in service.snapshot(uid, now)["book"] if c["id"] == ids[0])["status"]
        == "hidden"
    )
    service.act(uid, StudyAction(event_id=uuid4(), item_id=ids[0], action="unhide"), now)
    assert len(service.snapshot(uid, now)["book"]) == 30
    assert service.snapshot(b["profile"]["uid"], now)["processed"] == 0
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(ReviewResponseRow)) == 1
        assert session.scalar(select(func.count()).select_from(StudyEventRow)) == 33
    mismatch = requests[0].model_copy(update={"action": "known"})
    assert (
        client.post(
            "/api/v1/study/actions", headers=h, json=mismatch.model_dump(mode="json")
        ).status_code
        == 409
    )


def test_fifty_days_and_legacy(system):
    from app.modules.study.router import StudyAction
    from app.modules.study.service import StudyService
    from app.modules.vocabulary_review.models import VocabularyReviewState
    from app.modules.vocabulary_review.repository import VocabularyReviewRepository

    db, client, _ = system
    device = bootstrap(client, "husband")[0]
    uid = device["profile"]["uid"]
    service = StudyService(db)
    now = datetime(2026, 11, 1, tzinfo=UTC)
    old = "upgrade_ambiguous"
    with db.session() as session:
        session.add(
            VocabularyReviewRepository._state_row(
                uid,
                VocabularyReviewState(
                    schema_version=2,
                    user_id=uid,
                    lexical_item_id=old,
                    review_count=1,
                    next_due_at=now,
                ),
            )
        )
    days = service.snapshot(uid, now)["days"]
    for day in days:
        for item in day["ids"]:
            service.act(uid, StudyAction(event_id=uuid4(), item_id=item, action="next"), now)
        now += timedelta(days=1)
    end = service.snapshot(uid, now)
    assert end["finished"] and len(end["book"]) >= 1500
    assert any(c["id"] == old for c in end["book"])
    service.act(uid, StudyAction(event_id=uuid4(), item_id=old, action="review", answer=None), now)
    assert service.snapshot(uid, now)["review_due"] > 0


def test_concurrent_answers_and_spaced_retention(system):
    from concurrent.futures import ThreadPoolExecutor

    from app.db.models import CanonicalVocabularyStateRow, StudyEventRow
    from app.modules.study.router import StudyAction
    from app.modules.study.service import StudyService

    db, client, _ = system
    device = bootstrap(client, "husband")[0]
    uid = device["profile"]["uid"]
    service = StudyService(db)
    now = datetime(2026, 11, 1, tzinfo=UTC)
    card = service.snapshot(uid, now)["cards"][0]
    request = StudyAction(event_id=uuid4(), item_id=card["id"], action="known")
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: StudyService(db).act(uid, request, now), range(4)))
    assert service.snapshot(uid, now)["processed"] == 1
    assert service.snapshot(uid, now)["book"][0]["status"] == "known_pending_review"
    for offset in (0, 0, 2):
        review = StudyAction(
            event_id=uuid4(), item_id=card["id"], action="review", answer=card["translation_ru"]
        )
        service.act(uid, review, now + timedelta(days=offset))
        status = service.snapshot(uid, now + timedelta(days=offset))["book"][0]["status"]
        assert (status == "retained") == (offset == 2)
    assert (
        client.post(
            "/api/v1/study/actions",
            headers=headers(device),
            json={**request.model_dump(mode="json"), "learner_id": "another-person"},
        ).status_code
        == 409
    )
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(StudyEventRow)) == 4
        assert session.scalar(select(func.count()).select_from(CanonicalVocabularyStateRow)) == 1


def test_legacy_learning_event_import_and_link(system):
    from app.db.models import CanonicalVocabularyStateRow, LearningEventRow
    from app.modules.study.router import StudyAction
    from app.modules.study.service import StudyService

    db, client, _ = system
    device = bootstrap(client, "husband")[0]
    uid = device["profile"]["uid"]
    service = StudyService(db)
    new, old = next(iter(service.catalog.legacy_links.items()))
    with db.session() as session:
        session.add(
            LearningEventRow(
                learner_id=uid,
                event_id=str(uuid4()),
                server_received_at=datetime.now(UTC),
                event_type="vocabulary_item_opened",
                payload={"content_type": "vocabulary_item", "content_id": old},
            )
        )
    snapshot = service.snapshot(uid)
    assert new in {c["id"] for c in snapshot["book"]}
    service.act(uid, StudyAction(event_id=uuid4(), item_id=new, action="review", answer=None))
    with db.session() as session:
        assert session.get(CanonicalVocabularyStateRow, (uid, old)).review_count == 1
        assert session.get(CanonicalVocabularyStateRow, (uid, new)) is None


def test_placement_before_start_then_order_frozen(system):
    from app.modules.learning_quality.repository import QualityRepository
    from app.modules.study.router import StudyAction
    from app.modules.study.service import StudyService

    db, client, _ = system
    device = bootstrap(client, "wife")[0]
    uid = device["profile"]["uid"]
    service = StudyService(db)
    first = service.snapshot(uid)
    QualityRepository(db).mutate(
        uid, "diagnostic:v1", lambda p: p.update(result={"difficulty": "B2"})
    )
    advanced = service.snapshot(uid)
    assert advanced["days"] != first["days"]
    assert advanced["cards"][0]["cefr_level"] == "B2"
    service.act(
        uid, StudyAction(event_id=uuid4(), item_id=advanced["cards"][0]["id"], action="next")
    )
    QualityRepository(db).mutate(
        uid, "diagnostic:v1", lambda p: p.update(result={"difficulty": "A1"})
    )
    assert [d["ids"] for d in service.snapshot(uid)["days"]] == [d["ids"] for d in advanced["days"]]


def test_quick_recall_read_is_not_an_answer_and_replay_is_idempotent(system):
    from app.db.models import ReviewResponseRow
    from app.modules.study.router import StudyAction
    from app.modules.study.service import StudyService

    db, client, _ = system
    device = bootstrap(client, "husband")[0]
    uid = device["profile"]["uid"]
    service = StudyService(db)
    card = service.snapshot(uid)["cards"][0]
    service.act(uid, StudyAction(event_id=uuid4(), item_id=card["id"], action="next"))
    h = headers(device)
    for _ in range(2):
        assert client.get("/api/v1/study/today", headers=h).status_code == 200
        assert (
            client.get("/api/v1/study/book", headers=h, params={"q": card["term"]}).status_code
            == 200
        )
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(ReviewResponseRow)) == 0
    payload = {
        "learner_id": uid,
        "event_id": str(uuid4()),
        "item_id": card["id"],
        "action": "review",
        "answer": card["translation_ru"],
    }
    for _ in range(2):
        response = client.post("/api/v1/study/actions", headers=h, json=payload)
        assert response.status_code == 200, response.text
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(ReviewResponseRow)) == 1
    assert service.snapshot(uid)["processed"] == 1
