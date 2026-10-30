"""Persistent regression coverage for S3 against isolated PostgreSQL."""
# ruff: noqa: F811

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401


def test_placement_isolated_resume_and_material_selection(system):
    from app.modules.learning_quality.questions import QUESTIONS
    from app.modules.vocabulary_review.router import get_vocabulary_learning_service

    db, client, _ = system
    devices = [bootstrap(client, role)[0] for role in ("husband", "wife")]
    path = "/api/v1/learning-quality/diagnostic"
    for n, device in enumerate(devices):
        h = headers(device)
        for i, q in enumerate(QUESTIONS):
            request = {"question_id": i, "choice": q[4] if n else None}
            result = client.post(path + "/answers", headers=h, json=request)
            assert result.status_code == 200, result.text
            assert client.post(path + "/answers", headers=h, json=request).json() == result.json()
            assert client.get(path, headers=h).json()["answered"] == i + 1
        assert result.json()["result"]["difficulty"] == ("C1" if n else "A1")
        assert result.json()["question"] is None
    service = get_vocabulary_learning_service()
    packs = [service.get_today(d["profile"]["uid"], "UTC").daily_pack for d in devices]
    assert all(x.cefr in {"A1", "A2"} for x in packs[0].core_words + packs[0].phrases)
    assert any(x.cefr == "C1" for x in packs[1].core_words)
    assert packs[0].core_words != packs[1].core_words
    assert client.get(path, headers=headers(devices[0])).json()["result"]["difficulty"] == "A1"


def test_card_actions_preserve_history_and_filter_future(system):
    from app.modules.learning_quality.repository import QualityRepository
    from app.modules.vocabulary_review.models import ReviewRating
    from app.modules.vocabulary_review.repository import VocabularyReviewRepository
    from app.modules.vocabulary_review.router import get_vocabulary_learning_service
    from app.modules.vocabulary_review.schemas import SubmitReviewResponseRequest

    db, client, _ = system
    husband = bootstrap(client, "husband")[0]
    wife = bootstrap(client, "wife")[0]
    uid = husband["profile"]["uid"]
    service = get_vocabulary_learning_service()
    today = service.get_today(uid, "UTC")
    session = service.get_session(uid, today.midday_session.session_id)
    item = session.cards[0].lexical_item_id
    path = f"/api/v1/learning-quality/items/{item}/actions"

    def act(kind, **kwargs):
        return client.post(
            path,
            headers=headers(husband),
            json={"event_id": str(uuid4()), "action": kind, **kwargs},
        )

    assert act("known").status_code == 200
    repo = VocabularyReviewRepository(db)
    assert repo.get_state(uid, item) is None  # self-assessment is not mastery
    assert QualityRepository(db).preferences(uid)[item]["verification_pending"]
    result = service.submit_response(
        uid,
        session.session_id,
        SubmitReviewResponseRequest(
            event_id=str(uuid4()), lexical_item_id=item, rating=ReviewRating.AGAIN
        ),
    )
    assert result.state.last_rating == ReviewRating.AGAIN
    assert act("hide").status_code == 200
    assert not QualityRepository(db).preferences(wife["profile"]["uid"])
    assert repo.get_state(uid, item) == result.state
    assert item not in {
        c.lexical_item_id for c in service.get_session(uid, session.session_id).cards
    }
    tomorrow = service.get_today(uid, "UTC", datetime.now(UTC) + timedelta(days=1))
    assert item not in {
        x.id
        for x in tomorrow.daily_pack.core_words
        + tomorrow.daily_pack.phrases
        + tomorrow.daily_pack.synonym_upgrades
    }
    report_id = str(uuid4())
    request = {
        "event_id": report_id,
        "action": "report",
        "error_type": "translation",
        "comment": "Check sense",
    }
    for _ in range(2):
        assert client.post(path, headers=headers(husband), json=request).status_code == 200
    assert QualityRepository(db).get(uid, "report:" + report_id)["item_id"] == item
    assert QualityRepository(db).get(wife["profile"]["uid"], "report:" + report_id) == {}


def test_unknown_grammar_and_topic_threshold(system):
    from sqlalchemy import select

    from app.db.models import ExerciseAnswerRow

    db, client, _ = system
    husband = bootstrap(client, "husband")[0]
    wife = bootstrap(client, "wife")[0]
    h = headers(husband)
    plan = client.post("/api/v1/daily-plans/today", headers=h, json={"timezone": "UTC"}).json()
    item = next(i for i in plan["items"] if i["content_type"] == "grammar_lesson")
    response = client.post(
        "/api/v1/exercise-sessions",
        headers=h,
        json={"local_date": plan["local_date"], "daily_plan_item_id": item["item_id"]},
    )
    assert response.status_code == 200, response.text
    session = response.json()
    assert len(session["exercises"]) >= 3
    for i, exercise in enumerate(session["exercises"][:3]):
        response = client.post(
            f"/api/v1/exercise-sessions/{session['session_id']}/exercises/{exercise['exercise_id']}/attempts",
            headers=h,
            json={"attempt_id": str(uuid4()), "unknown": True},
        )
        assert response.status_code == 200, response.text
        assert response.json()["outcome"] == 0
        assert response.json()["is_correct"] is False
        topics = client.get("/api/v1/learning-quality/grammar-topics", headers=h).json()["topics"]
        assert topics[0]["weak"] == (i >= 2)
    assert (
        client.get("/api/v1/learning-quality/grammar-topics", headers=headers(wife)).json()[
            "topics"
        ]
        == []
    )
    with db.session() as session:
        rows = session.scalars(select(ExerciseAnswerRow)).all()
        assert all(
            r.payload["topic_id"] == item["content_id"] and r.payload["answer_status"] == "unknown"
            for r in rows
        )


def test_content_gate_exhaustion_and_answer_variants():
    from datetime import date

    from app.modules.exercises.grader import normalize_answer
    from app.modules.users.models import EnglishLevel
    from app.modules.vocabulary_review.lexicon_repository import get_canonical_lexicon_repository
    from app.modules.vocabulary_review.models import ReviewCardType, VocabularyReviewCard
    from app.modules.vocabulary_review.selector import DailyVocabularySelector
    from app.modules.vocabulary_review.service import VocabularyLearningService

    vocabulary = get_canonical_lexicon_repository()
    pool = vocabulary.initial_items
    assert len(pool) == len({i.term.casefold() for i in pool}) == 300
    selector = DailyVocabularySelector(pool, vocabulary.dataset_version)
    introduced = set()
    for day in range(14):
        selection = selector.select(
            uid="test",
            local_date=date(2026, 10, 1) + timedelta(days=day),
            level=EnglishLevel.A1,
            due_count=0,
            introduced_ids=introduced,
        )
        ids = set(selection.core_word_ids + selection.phrase_ids + selection.synonym_upgrade_ids)
        assert not ids & introduced
        assert ids <= vocabulary.initial_pool.keys()
        introduced |= ids
    assert len(introduced) <= 88
    assert normalize_answer("She doesn’t work.") == normalize_answer("She does not work")
    for item in pool:
        card = VocabularyReviewCard(
            card_id="test",
            lexical_item_id=item.id,
            card_type=ReviewCardType.CONTEXT_RECALL,
            item=item,
        )
        response = VocabularyLearningService._card_response(card)
        assert "_____" in response.front_term or response.front_term == item.translation_ru
