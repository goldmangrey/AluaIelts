from copy import deepcopy
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.database import get_database
from app.db.models import (
    CanonicalVocabularyStateRow,
    LearningEventRow,
    LearningQualityRow,
    ReviewResponseRow,
    StudyEventRow,
    StudyProgramRow,
)
from app.modules.study.catalog import catalog
from app.modules.vocabulary_review.lexicon_repository import get_canonical_lexicon_repository
from app.modules.vocabulary_review.models import (
    ReviewRating,
    VocabularyReviewEvent,
    VocabularyReviewState,
)
from app.modules.vocabulary_review.repository import VocabularyReviewRepository
from app.modules.vocabulary_review.scheduler import DeterministicVocabularyScheduler


class StudyService:
    def __init__(self, database=None):
        self.db = database or get_database()
        self.catalog = catalog()
        self.old_to_new = {v: k for k, v in self.catalog.legacy_links.items()}

    def _program(self, session, uid):
        existing = session.scalar(
            select(StudyProgramRow).where(StudyProgramRow.learner_id == uid).with_for_update()
        )
        diagnostic = session.get(LearningQualityRow, (uid, "diagnostic:v1"))
        level = (
            (diagnostic.payload.get("result") or {}).get("difficulty", "A1") if diagnostic else "A1"
        )
        if existing:
            if not existing.payload["introduced"] and existing.payload["level"] != level:
                payload = deepcopy(existing.payload)
                payload.update(level=level, days=self.catalog.program(level))
                existing.payload = payload
            return existing
        session.execute(
            insert(StudyProgramRow)
            .values(
                learner_id=uid,
                payload={
                    "version": self.catalog.version,
                    "level": level,
                    "days": self.catalog.program(level),
                    "introduced": {},
                    "completed": {},
                },
            )
            .on_conflict_do_nothing()
        )
        row = session.scalar(
            select(StudyProgramRow).where(StudyProgramRow.learner_id == uid).with_for_update()
        )
        # Preserve previously opened/assessed legacy vocabulary, including pre-SRS learning.
        lexicon = get_canonical_lexicon_repository()
        ids = set()
        for event in session.scalars(
            select(LearningEventRow).where(LearningEventRow.learner_id == uid)
        ):
            if event.payload.get("content_type") == "vocabulary_item":
                canonical = lexicon.resolve_id(event.payload.get("content_id", ""))
                if canonical:
                    ids.add(canonical)
        for preference in session.scalars(
            select(LearningQualityRow).where(
                LearningQualityRow.learner_id == uid, LearningQualityRow.key.startswith("item:")
            )
        ):
            if preference.payload.get("self_assessment") or preference.payload.get("hidden"):
                canonical = lexicon.resolve_id(preference.key[5:])
                if canonical:
                    ids.add(canonical)
        for item_id in ids:
            if session.get(CanonicalVocabularyStateRow, (uid, item_id)) is None:
                session.add(
                    VocabularyReviewRepository._state_row(
                        uid,
                        VocabularyReviewState(
                            schema_version=2,
                            user_id=uid,
                            lexical_item_id=item_id,
                            next_due_at=datetime.now(UTC),
                        ),
                    )
                )
        session.flush()
        return row

    @staticmethod
    def _current(p, now):
        for day in p["days"]:
            if str(day["day"]) not in p["completed"]:
                previous = p["completed"].get(str(day["day"] - 1))
                available = (
                    not previous
                    or previous < now.astimezone(ZoneInfo("Asia/Almaty")).date().isoformat()
                )
                return day, available
        return p["days"][-1], False

    def snapshot(self, uid, now=None):
        now = now or datetime.now(UTC)
        with self.db.session() as session:
            p = self._program(session, uid).payload
            day, available = self._current(p, now)
            cards = self._book(session, uid, p, now)
            done = sum(i in p["introduced"] for i in day["ids"])
            return {
                "version": p["version"],
                "day": day["day"],
                "title": day["title"],
                "processed": done,
                "available": available,
                "finished": len(p["completed"]) == 50,
                "cards": [
                    self.catalog.by_id[i].model_dump()
                    for i in day["ids"]
                    if i not in p["introduced"]
                ],
                "review_due": sum(c["status"] == "review_due" for c in cards),
                "days": [
                    {
                        **d,
                        "processed": sum(i in p["introduced"] for i in d["ids"]),
                        "complete": str(d["day"]) in p["completed"],
                    }
                    for d in p["days"]
                ],
                "book": cards,
                "topics": self.catalog.manifest["topics"],
            }

    def _book(self, session, uid, p, now):
        states = {
            self.old_to_new.get(
                r.lexical_item_id, r.lexical_item_id
            ): VocabularyReviewState.model_validate(r.payload)
            for r in session.scalars(
                select(CanonicalVocabularyStateRow).where(
                    CanonicalVocabularyStateRow.learner_id == uid
                )
            )
        }
        preferences = {
            self.old_to_new.get(r.key[5:], r.key[5:]): r.payload
            for r in session.scalars(
                select(LearningQualityRow).where(
                    LearningQualityRow.learner_id == uid, LearningQualityRow.key.startswith("item:")
                )
            )
        }
        # Actual old recall events/states are evidence of study; generated packs are not.
        ids = set(p["introduced"]) | set(states)
        legacy = get_canonical_lexicon_repository()
        result = []
        for item_id in sorted(ids):
            card = self.catalog.by_id.get(item_id)
            if card:
                value = card.model_dump()
            else:
                old = legacy.get(item_id)
                if not old:
                    continue
                value = {
                    "id": item_id,
                    "term": old.term,
                    "translation_ru": old.translation_ru,
                    "definition_en": old.definition_en or "",
                    "example_en": next(iter(old.examples), ""),
                    "example_ru": "",
                    "usage_note_ru": old.usage_ru or "",
                    "topic_ids": [],
                    "primary_topic_id": 0,
                }
            pref, state = preferences.get(item_id, {}), states.get(item_id)
            status = "introduced"
            if pref.get("verification_pending") and pref.get("self_assessment") == "known":
                status = "known_pending_review"
            if (
                state
                and state.interval_hours >= 72
                and state.last_rating == ReviewRating.GOOD
                and pref.get("spaced_successes", 0) >= 2
            ):
                status = "retained"
            if state and state.next_due_at and state.next_due_at <= now:
                status = "review_due"
            if pref.get("hidden"):
                status = "hidden"
            result.append({**value, "status": status})
        return result

    def act(self, uid, request, now=None):
        if request.learner_id is not None and request.learner_id != uid:
            raise HTTPException(409, "Learner changed")
        now = now or datetime.now(UTC)
        body = request.model_dump(mode="json")
        item_id, action = request.item_id, request.action
        state_id = self.catalog.legacy_links.get(item_id, item_id)
        with self.db.session() as session:
            row = self._program(session, uid)  # Serializes all study mutations for this learner.
            prior = session.get(StudyEventRow, (uid, str(request.event_id)))
            if prior:
                if prior.payload != body:
                    raise HTTPException(409, "Event ID already used with different content")
                return {"saved": True}
            if session.get(ReviewResponseRow, (uid, str(request.event_id))):
                raise HTTPException(409, "Event ID already used for review")
            p = deepcopy(row.payload)
            day, available = self._current(p, now)
            state_row = session.get(
                CanonicalVocabularyStateRow, (uid, state_id), with_for_update=True
            )
            introduced = item_id in p["introduced"] or state_row is not None
            if action in {"next", "known", "unknown", "hide"} and not introduced:
                pending = [i for i in day["ids"] if i not in p["introduced"]]
                if not available or not pending or pending[0] != item_id:
                    raise HTTPException(409, "Continue the current study card")
                p["introduced"][item_id] = now.isoformat()
                if all(i in p["introduced"] for i in day["ids"]):
                    p["completed"][str(day["day"])] = (
                        now.astimezone(ZoneInfo("Asia/Almaty")).date().isoformat()
                    )
            elif not introduced and action != "report":
                raise HTTPException(409, "Study this card first")
            if item_id not in self.catalog.by_id and not get_canonical_lexicon_repository().get(
                item_id
            ):
                raise HTTPException(404, "Unknown card")
            # An old state must not prevent processing its position in the new curriculum.
            if (
                introduced
                and action in {"next", "known", "unknown", "hide"}
                and item_id not in p["introduced"]
            ):
                pending = [i for i in day["ids"] if i not in p["introduced"]]
                if available and pending and pending[0] == item_id:
                    p["introduced"][item_id] = now.isoformat()
                    if all(i in p["introduced"] for i in day["ids"]):
                        p["completed"][str(day["day"])] = (
                            now.astimezone(ZoneInfo("Asia/Almaty")).date().isoformat()
                        )
            pref_row = session.get(
                LearningQualityRow,
                (uid, f"item:{state_id}"),
                with_for_update=True,
            )
            pref = deepcopy(pref_row.payload) if pref_row else {}
            state = (
                VocabularyReviewState.model_validate(state_row.payload)
                if state_row
                else VocabularyReviewState(
                    schema_version=2,
                    user_id=uid,
                    lexical_item_id=state_id,
                    last_seen_at=now,
                    next_due_at=now + timedelta(days=1),
                )
            )
            if action == "review":
                # Grade a concrete recall choice on the server, never trust a client mastery flag.
                expected = self.card(item_id)["translation_ru"]
                rating = ReviewRating.GOOD if request.answer == expected else ReviewRating.AGAIN
                updated = DeterministicVocabularyScheduler().apply(state, rating, now)
                event = VocabularyReviewEvent(
                    event_id=str(request.event_id),
                    schema_version=2,
                    review_contract_version=2,
                    pack_id="study",
                    user_id=uid,
                    session_id="study-manual",
                    lexical_item_id=state_id,
                    rating=rating,
                    reviewed_at=now,
                    previous_due_at=state.next_due_at,
                    next_due_at=updated.next_due_at,
                    source="manual",
                )
                existing = session.get(ReviewResponseRow, (uid, str(request.event_id)))
                if existing:
                    raise HTTPException(409, "Event ID already used for review")
                session.add(
                    ReviewResponseRow(
                        learner_id=uid,
                        event_id=str(request.event_id),
                        session_id=event.session_id,
                        lexical_item_id=state_id,
                        rating=rating.value,
                        occurred_at=now,
                        payload=event.model_dump(mode="json"),
                    )
                )
                if rating == ReviewRating.GOOD:
                    last = pref.get("last_success")
                    if not last or now - datetime.fromisoformat(last) >= timedelta(hours=24):
                        pref["spaced_successes"] = pref.get("spaced_successes", 0) + 1
                        pref["last_success"] = now.isoformat()
                else:
                    pref["spaced_successes"] = 0
                state = updated
                pref["verification_pending"] = False
            elif action in {"known", "unknown"}:
                pref.update(verification_pending=True, self_assessment=action)
                if action == "unknown":
                    state = state.model_copy(
                        update={
                            "next_due_at": now + timedelta(minutes=30),
                            "interval_hours": 0,
                            "last_rating": ReviewRating.AGAIN,
                        }
                    )
            elif action in {"hide", "unhide"}:
                pref["hidden"] = action == "hide"
            elif action == "report":
                session.add(
                    LearningQualityRow(
                        learner_id=uid,
                        key=f"report:{request.event_id}",
                        payload={
                            "item_id": item_id,
                            "comment": request.comment,
                            "created_at": now.isoformat(),
                        },
                    )
                )
            if action != "report":
                if pref_row:
                    pref_row.payload = pref
                else:
                    session.add(
                        LearningQualityRow(learner_id=uid, key=f"item:{state_id}", payload=pref)
                    )
                if state_row:
                    state_row.payload = state.model_dump(mode="json")
                    state_row.review_count, state_row.due_at = state.review_count, state.next_due_at
                else:
                    session.add(VocabularyReviewRepository._state_row(uid, state))
            row.payload = p
            session.add(StudyEventRow(learner_id=uid, event_id=str(request.event_id), payload=body))
        return {"saved": True}

    def card(self, item_id):
        if item_id in self.catalog.by_id:
            return self.catalog.by_id[item_id].model_dump()
        old = get_canonical_lexicon_repository().get(item_id)
        if not old:
            raise HTTPException(404, "Unknown card")
        return {"id": item_id, "term": old.term, "translation_ru": old.translation_ru}
