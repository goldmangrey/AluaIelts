import logging
import re
from datetime import UTC, date, datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.learning_quality.repository import QualityRepository
from app.modules.users.models import EnglishLevel
from app.modules.users.repository import UserRepository
from app.modules.vocabulary_review.contract import (
    PACK_SCHEMA_VERSION,
    REVIEW_CONTRACT_VERSION,
    REVIEW_EVENT_SCHEMA_VERSION,
    REVIEW_SESSION_GENERATION_VERSION,
    REVIEW_SESSION_SCHEMA_VERSION,
    REVIEW_STATE_SCHEMA_VERSION,
    pack_document_id,
    session_signature,
)
from app.modules.vocabulary_review.lexicon_repository import CanonicalLexiconRepository
from app.modules.vocabulary_review.models import (
    DailyLexicalPack,
    LexicalKind,
    ReviewCardType,
    ReviewRating,
    ReviewSessionKind,
    ReviewSource,
    VocabularyReviewCard,
    VocabularyReviewEvent,
    VocabularyReviewSession,
    VocabularyReviewState,
)
from app.modules.vocabulary_review.repository import VocabularyReviewRepository
from app.modules.vocabulary_review.scheduler import DeterministicVocabularyScheduler
from app.modules.vocabulary_review.schemas import (
    CurrentRecall,
    DailyPackResponse,
    LearningWindow,
    ReviewCardResponse,
    ReviewSessionSummary,
    SubmitReviewResponseRequest,
    SubmitReviewResponseResult,
    VocabularyLearningTodayResponse,
    VocabularyReviewSessionResponse,
    WeeklyReviewResponse,
)
from app.modules.vocabulary_review.selector import DailyVocabularySelector

logger = logging.getLogger(__name__)


class VocabularyLearningService:
    def __init__(
        self,
        *,
        repository: VocabularyReviewRepository,
        vocabulary: CanonicalLexiconRepository,
        scheduler: DeterministicVocabularyScheduler,
        users: UserRepository,
    ) -> None:
        self._repository = repository
        self._vocabulary = vocabulary
        self._scheduler = scheduler
        self._users = users
        self._quality = QualityRepository(repository._database)
        self._lexical = dict(vocabulary._by_id)
        self._lexical.update({item.id: item for item in vocabulary.initial_items})
        self._selector = DailyVocabularySelector(
            vocabulary.initial_items, vocabulary.dataset_version
        )

    def get_today(
        self, uid: str, timezone_name: str, now: datetime | None = None
    ) -> VocabularyLearningTodayResponse:
        zone = self._timezone(timezone_name)
        local_now = (now or datetime.now(UTC)).astimezone(zone)
        pack = self._ensure_pack(uid, local_now.date(), timezone_name)
        states = self._current_states(uid)
        midday = self._ensure_session(uid, local_now.date(), ReviewSessionKind.MIDDAY, pack)
        evening_kind = (
            ReviewSessionKind.WEEKLY if local_now.weekday() == 6 else ReviewSessionKind.EVENING
        )
        evening = (
            self._ensure_session(uid, local_now.date(), evening_kind, pack)
            if local_now.hour >= 20
            else None
        )
        active = evening or midday
        due_count = sum(
            s.next_due_at is not None and s.next_due_at <= local_now.astimezone(UTC) for s in states
        )
        return VocabularyLearningTodayResponse(
            local_date=local_now.date(),
            learning_window=LearningWindow(),
            daily_pack=self._pack_response(pack, uid),
            review_due_count=due_count,
            midday_session=self._summary(uid, midday, time(14)),
            evening_session=(
                self._summary(uid, evening, time(20))
                if evening
                else ReviewSessionSummary(
                    session_id=self._session_id(uid, local_now.date(), evening_kind, pack),
                    kind=evening_kind,
                    card_count=40 if evening_kind == ReviewSessionKind.WEEKLY else 12,
                    completed_count=0,
                    available_at=time(20),
                )
            ),
            current_recall=self._current_recall(uid, active, local_now),
        )

    def get_session(self, uid: str, session_id: str) -> VocabularyReviewSessionResponse:
        session = self._repository.get_session(uid, session_id)
        if session is None:
            match = re.fullmatch(
                r"vocab-(\d{4}-\d{2}-\d{2})-(midday|evening|weekly)-s2-g2-[0-9a-f]{12}(?:-r\d+)?",
                session_id,
            )
            if match:
                local_date = date.fromisoformat(match.group(1))
                kind = ReviewSessionKind(match.group(2))
                packs = [p for p in self._current_packs(uid) if p.local_date == local_date]
                if packs:
                    current_pack = max(packs, key=lambda value: value.generation_revision)
                    candidate = self._ensure_session(uid, local_date, kind, current_pack)
                    session = candidate if candidate.session_id == session_id else None
        if session is None or not self._valid_session(session):
            raise NotFoundError(
                message="Current vocabulary review session not found.",
                code="review_session_not_found",
            )
        events = self._current_session_events(uid, session.session_id)
        hidden = self._hidden(uid)
        return VocabularyReviewSessionResponse(
            session_id=session.session_id,
            schema_version=session.schema_version,
            generation_version=session.generation_version,
            pack_id=session.anchor_pack_ids[-1],
            content_version=session.content_version,
            local_date=session.local_date,
            kind=session.kind,
            cards=tuple(
                self._card_response(
                    card.model_copy(update={"item": self._lexical[card.lexical_item_id]})
                )
                for card in session.cards
                if card.lexical_item_id not in hidden
            ),
            completed_lexical_item_ids=tuple(event.lexical_item_id for event in events),
        )

    def submit_response(
        self, uid: str, session_id: str, request: SubmitReviewResponseRequest
    ) -> SubmitReviewResponseResult:
        session = self._repository.get_session(uid, session_id)
        canonical_id = self._vocabulary.resolve_id(request.lexical_item_id)
        if (
            session is None
            or not self._valid_session(session)
            or canonical_id != request.lexical_item_id
            or canonical_id not in {card.lexical_item_id for card in session.cards}
        ):
            raise ValidationError(
                message="The canonical lexical item is not part of this review session.",
                code="vocabulary_review_item_mismatch",
            )
        reviewed_at = datetime.now(UTC)
        previous = self._repository.get_state(uid, canonical_id) or VocabularyReviewState(
            schema_version=REVIEW_STATE_SCHEMA_VERSION, user_id=uid, lexical_item_id=canonical_id
        )
        updated = self._scheduler.apply(previous, request.rating, reviewed_at)
        event = VocabularyReviewEvent(
            event_id=request.event_id,
            schema_version=REVIEW_EVENT_SCHEMA_VERSION,
            review_contract_version=REVIEW_CONTRACT_VERSION,
            pack_id=session.anchor_pack_ids[-1],
            user_id=uid,
            session_id=session_id,
            lexical_item_id=canonical_id,
            rating=request.rating,
            reviewed_at=reviewed_at,
            previous_due_at=previous.next_due_at,
            next_due_at=updated.next_due_at,
            source=ReviewSource(session.kind.value),
        )
        stored_event, stored_state = self._repository.apply_event(uid, event, previous, updated)
        self._quality.mutate(
            uid, f"item:{canonical_id}", lambda p: p.update(verification_pending=False)
        )
        return SubmitReviewResponseResult(event_id=stored_event.event_id, state=stored_state)

    def get_weekly(self, uid: str, timezone_name: str) -> WeeklyReviewResponse:
        zone = self._timezone(timezone_name)
        local_date = datetime.now(UTC).astimezone(zone).date()
        pack = self._ensure_pack(uid, local_date, timezone_name)
        session = self._ensure_session(uid, local_date, ReviewSessionKind.WEEKLY, pack)
        events = self._current_session_events(uid, session.session_id)
        hidden = self._hidden(uid)
        ids = tuple(
            card.lexical_item_id for card in session.cards if card.lexical_item_id not in hidden
        )
        return WeeklyReviewResponse(
            local_date=local_date,
            session=ReviewSessionSummary(
                session_id=session.session_id,
                kind=session.kind,
                card_count=len(ids),
                completed_count=sum(e.lexical_item_id in ids for e in events),
                available_at=time(20),
            ),
            week_item_count=len(ids),
            review_all_item_ids=ids,
        )

    def _ensure_pack(self, uid: str, local_date: date, timezone_name: str) -> DailyLexicalPack:
        states = self._current_states(uid)
        due_count = sum(
            s.next_due_at is not None and s.next_due_at <= datetime.now(UTC) for s in states
        )
        history = self._current_packs(uid)
        introduced = {item_id for pack in history for item_id in pack.all_item_ids}
        introduced |= self._hidden(uid)
        profile = self._users.get_by_uid(uid)
        level = profile.current_level if profile else EnglishLevel.A1
        result = self._quality.get(uid, "diagnostic:v1").get("result")
        if result:
            level = EnglishLevel(result["difficulty"])
        for revision in range(10):
            pack_id = pack_document_id(
                local_date, self._vocabulary.dataset_version, self._selector.version, revision
            )
            existing = self._repository.get_pack(uid, pack_id)
            if existing is not None:
                if self._valid_pack(existing, uid, local_date, timezone_name):
                    return existing
                logger.warning(
                    "Invalid current vocabulary pack ignored",
                    extra={
                        "local_date": local_date.isoformat(),
                        "pack_id": pack_id,
                        "content_version": str(existing.content_version),
                        "revision": revision,
                    },
                )
                continue
            if self._repository.pack_document_exists(uid, pack_id):
                logger.warning(
                    "Malformed current vocabulary pack ignored",
                    extra={"local_date": local_date.isoformat(), "pack_id": pack_id},
                )
                continue
            selected = self._selector.select(
                uid=uid,
                local_date=local_date,
                level=level,
                due_count=due_count,
                introduced_ids=introduced,
            )
            pack = DailyLexicalPack(
                pack_id=pack_id,
                schema_version=PACK_SCHEMA_VERSION,
                selection_algorithm_version=self._selector.version,
                generation_revision=revision,
                user_id=uid,
                local_date=local_date,
                timezone_at_generation=timezone_name,
                content_version=self._vocabulary.dataset_version,
                core_word_ids=selected.core_word_ids,
                synonym_upgrade_ids=selected.synonym_upgrade_ids,
                phrase_ids=selected.phrase_ids,
                created_at=datetime.now(UTC),
            )
            stored = self._repository.create_pack(uid, pack)
            if self._valid_pack(stored, uid, local_date, timezone_name):
                return stored
        raise ValidationError(
            message="No valid current vocabulary pack revision could be created.",
            code="vocabulary_pack_contract_exhausted",
        )

    def _ensure_session(
        self, uid: str, local_date: date, kind: ReviewSessionKind, current_pack: DailyLexicalPack
    ) -> VocabularyReviewSession:
        source_packs: tuple[DailyLexicalPack, ...] = (current_pack,)
        if kind == ReviewSessionKind.WEEKLY:
            week_start = local_date - timedelta(days=6)
            source_packs = tuple(
                pack
                for pack in self._current_packs(uid)
                if week_start <= pack.local_date <= local_date
            )
        anchor_ids = tuple(
            pack.pack_id for pack in sorted(source_packs, key=lambda p: p.local_date)
        )
        signature = session_signature(anchor_ids)
        session_id = self._available_session_id(uid, local_date, kind, signature, anchor_ids)
        existing = self._repository.get_session(uid, session_id)
        if existing is not None:
            return existing
        states = {state.lexical_item_id: state for state in self._current_states(uid)}
        now = datetime.now(UTC)
        pack_ids = list(dict.fromkeys(i for pack in source_packs for i in pack.all_item_ids))
        due_ids = [
            item_id
            for item_id, state in states.items()
            if state.next_due_at is not None and state.next_due_at <= now
        ]
        pending = [
            i
            for i, p in self._quality.preferences(uid).items()
            if p.get("verification_pending") and i in self._vocabulary.initial_pool
        ]
        hidden = self._hidden(uid)
        candidates = [i for i in dict.fromkeys(pending + due_ids + pack_ids) if i not in hidden]
        ordered = sorted(
            candidates,
            key=lambda item_id: self._priority(states.get(item_id), now, candidates.index(item_id)),
        )
        limit = 40 if kind == ReviewSessionKind.WEEKLY else 12
        cards = tuple(
            self._make_card(item_id, index) for index, item_id in enumerate(ordered[:limit])
        )
        session = VocabularyReviewSession(
            session_id=session_id,
            schema_version=REVIEW_SESSION_SCHEMA_VERSION,
            generation_version=REVIEW_SESSION_GENERATION_VERSION,
            anchor_pack_ids=anchor_ids,
            content_version=self._vocabulary.dataset_version,
            user_id=uid,
            local_date=local_date,
            kind=kind,
            card_ids=tuple(card.card_id for card in cards),
            cards=cards,
            created_at=now,
        )
        stored = self._repository.create_session(uid, session)
        if not self._valid_session(stored, anchor_ids):
            raise ValidationError(
                message="Persisted review session violates the current contract.",
                code="vocabulary_session_contract_invalid",
            )
        return stored

    def _current_recall(
        self, uid: str, session: VocabularyReviewSession, local_now: datetime
    ) -> CurrentRecall | None:
        if not 8 <= local_now.hour < 22:
            return None
        completed = {
            event.lexical_item_id for event in self._current_session_events(uid, session.session_id)
        }
        hidden = self._hidden(uid)
        card = next(
            (
                value
                for value in session.cards
                if value.lexical_item_id not in completed and value.lexical_item_id not in hidden
            ),
            None,
        )
        if card is None:
            return None
        return CurrentRecall(
            session_id=session.session_id,
            card_id=card.card_id,
            lexical_item_id=card.lexical_item_id,
            lexical_item=self._lexical[card.lexical_item_id],
            card_type=card.card_type,
            prompt="Вспомни значение",
            mode="review",
        )

    def _current_packs(self, uid: str) -> list[DailyLexicalPack]:
        return [
            pack for pack in self._repository.list_packs(uid) if self._valid_pack_identity(pack)
        ]

    def _hidden(self, uid: str) -> set[str]:
        return {i for i, p in self._quality.preferences(uid).items() if p.get("hidden")}

    def _current_states(self, uid: str) -> list[VocabularyReviewState]:
        hidden = self._hidden(uid)
        return [
            state
            for state in self._repository.list_states(uid)
            if state.lexical_item_id not in hidden
            and state.schema_version == REVIEW_STATE_SCHEMA_VERSION
            and self._vocabulary.resolve_id(state.lexical_item_id) == state.lexical_item_id
        ]

    def _current_session_events(self, uid: str, session_id: str) -> list[VocabularyReviewEvent]:
        return [
            event
            for event in self._repository.list_events_for_session(uid, session_id)
            if event.schema_version == REVIEW_EVENT_SCHEMA_VERSION
            and event.review_contract_version == REVIEW_CONTRACT_VERSION
        ]

    def _valid_pack(
        self, pack: DailyLexicalPack, uid: str, local_date: date, timezone_name: str
    ) -> bool:
        return (
            self._valid_pack_identity(pack)
            and pack.user_id == uid
            and pack.local_date == local_date
            # The first valid timezone for a local date anchors that learning day.
            # A later equivalent-date request reuses it instead of forking history.
            and pack.pack_id
            == pack_document_id(
                local_date,
                self._vocabulary.dataset_version,
                self._selector.version,
                pack.generation_revision,
            )
        )

    def _valid_pack_identity(self, pack: DailyLexicalPack) -> bool:
        ids = pack.all_item_ids
        return (
            pack.schema_version == PACK_SCHEMA_VERSION
            and pack.selection_algorithm_version == self._selector.version
            and str(pack.content_version) == self._vocabulary.dataset_version
            and len(ids) <= 30
            and len(ids) == len(set(ids))
            and all(
                item_id in self._lexical and self._vocabulary.resolve_id(item_id) == item_id
                for item_id in ids
            )
            and all(self._lexical[i].kind == LexicalKind.WORD for i in pack.core_word_ids)
            and all(
                self._lexical[i].kind == LexicalKind.SYNONYM_UPGRADE
                for i in pack.synonym_upgrade_ids
            )
            and all(
                self._lexical[i].kind
                in {LexicalKind.PHRASE, LexicalKind.COLLOCATION, LexicalKind.PHRASAL_VERB}
                for i in pack.phrase_ids
            )
        )

    def _valid_session(
        self, session: VocabularyReviewSession, anchor_ids: tuple[str, ...] | None = None
    ) -> bool:
        ids = tuple(card.lexical_item_id for card in session.cards)
        limit = 40 if session.kind == ReviewSessionKind.WEEKLY else 12
        return (
            session.schema_version == REVIEW_SESSION_SCHEMA_VERSION
            and session.generation_version == REVIEW_SESSION_GENERATION_VERSION
            and session.content_version == self._vocabulary.dataset_version
            and (anchor_ids is None or session.anchor_pack_ids == anchor_ids)
            and len(ids) <= limit
            and len(ids) == len(set(ids))
            and all(
                item_id in self._lexical
                and self._vocabulary.resolve_id(item_id) == item_id
                and card.item.id == item_id
                for item_id, card in zip(ids, session.cards, strict=True)
            )
        )

    @staticmethod
    def _priority(
        state: VocabularyReviewState | None, now: datetime, fallback: int
    ) -> tuple[int, datetime, int]:
        distant = now + timedelta(days=3650)
        if state and state.last_rating == ReviewRating.AGAIN:
            rank = 0
        elif state and state.last_rating == ReviewRating.HARD:
            rank = 1
        elif state and state.next_due_at and state.next_due_at <= now:
            rank = 2
        else:
            rank = 3
        return rank, state.next_due_at if state and state.next_due_at else distant, fallback

    def _pack_response(self, pack: DailyLexicalPack, uid: str) -> DailyPackResponse:
        hidden = self._hidden(uid)
        return DailyPackResponse(
            pack_id=pack.pack_id,
            schema_version=pack.schema_version,
            selection_algorithm_version=pack.selection_algorithm_version,
            content_version=str(pack.content_version),
            core_words=tuple(self._lexical[i] for i in pack.core_word_ids if i not in hidden),
            synonym_upgrades=tuple(
                self._lexical[i] for i in pack.synonym_upgrade_ids if i not in hidden
            ),
            phrases=tuple(self._lexical[i] for i in pack.phrase_ids if i not in hidden),
        )

    def _summary(
        self, uid: str, session: VocabularyReviewSession, available_at: time
    ) -> ReviewSessionSummary:
        hidden = self._hidden(uid)
        visible = {c.lexical_item_id for c in session.cards if c.lexical_item_id not in hidden}
        return ReviewSessionSummary(
            session_id=session.session_id,
            kind=session.kind,
            card_count=len(visible),
            completed_count=sum(
                e.lexical_item_id in visible
                for e in self._current_session_events(uid, session.session_id)
            ),
            available_at=available_at,
        )

    def _session_id(
        self, uid: str, local_date: date, kind: ReviewSessionKind, current_pack: DailyLexicalPack
    ) -> str:
        source_packs: tuple[DailyLexicalPack, ...] = (current_pack,)
        if kind == ReviewSessionKind.WEEKLY:
            start = local_date - timedelta(days=6)
            source_packs = tuple(
                pack for pack in self._current_packs(uid) if start <= pack.local_date <= local_date
            )
        anchors = tuple(pack.pack_id for pack in sorted(source_packs, key=lambda p: p.local_date))
        signature = session_signature(anchors)
        return self._available_session_id(uid, local_date, kind, signature, anchors)

    def _available_session_id(
        self,
        uid: str,
        local_date: date,
        kind: ReviewSessionKind,
        signature: str,
        anchor_ids: tuple[str, ...],
    ) -> str:
        base = self._session_id_from_signature(local_date, kind, signature)
        for revision in range(10):
            candidate = base if revision == 0 else f"{base}-r{revision}"
            existing = self._repository.get_session(uid, candidate)
            if existing is None or self._valid_session(existing, anchor_ids):
                if existing is not None or not self._repository.session_document_exists(
                    uid, candidate
                ):
                    return candidate
                logger.warning(
                    "Malformed current vocabulary session ignored",
                    extra={"local_date": local_date.isoformat(), "session_id": candidate},
                )
                continue
            logger.warning(
                "Invalid current vocabulary session ignored",
                extra={
                    "local_date": local_date.isoformat(),
                    "session_id": candidate,
                    "content_version": existing.content_version,
                    "revision": revision,
                },
            )
        raise ValidationError(
            message="No valid current review session revision could be created.",
            code="vocabulary_session_contract_exhausted",
        )

    @staticmethod
    def _session_id_from_signature(
        local_date: date, kind: ReviewSessionKind, signature: str
    ) -> str:
        return (
            f"vocab-{local_date.isoformat()}-{kind.value}-s{REVIEW_SESSION_SCHEMA_VERSION}-"
            f"g{REVIEW_SESSION_GENERATION_VERSION}-{signature}"
        )

    def _make_card(self, item_id: str, index: int) -> VocabularyReviewCard:
        item = self._lexical[item_id]
        types = (
            ReviewCardType.PHRASE_TO_MEANING
            if item.kind in {LexicalKind.PHRASE, LexicalKind.COLLOCATION, LexicalKind.PHRASAL_VERB}
            else ReviewCardType.TERM_TO_MEANING,
            ReviewCardType.MEANING_TO_TERM,
            ReviewCardType.CONTEXT_RECALL,
        )
        card_type = types[index % len(types)]
        card_id = str(
            uuid5(
                NAMESPACE_URL, f"alua:vocab-card:v{REVIEW_CONTRACT_VERSION}:{item_id}:{card_type}"
            )
        )
        return VocabularyReviewCard(
            card_id=card_id, lexical_item_id=item_id, card_type=card_type, item=item
        )

    @staticmethod
    def _card_response(card: VocabularyReviewCard) -> ReviewCardResponse:
        front = (
            card.item.translation_ru
            if card.card_type == ReviewCardType.MEANING_TO_TERM
            else card.item.term
        )
        prompt = "English?" if card.card_type == ReviewCardType.MEANING_TO_TERM else "Что значит?"
        if card.card_type == ReviewCardType.CONTEXT_RECALL:
            example = card.item.examples[0] if card.item.examples else ""
            front, count = re.subn(
                r"(?<!\w)" + re.escape(card.item.term) + r"(?!\w)",
                "_____",
                example,
                flags=re.IGNORECASE,
            )
            if count:
                prompt = "Вспомните выражение"
            else:
                # Inflected/discontinuous expressions require authored cloze variants.
                # Fall back to meaning recall instead of exposing the answer.
                front = card.item.translation_ru
                prompt = "Как это сказать по-английски?"
        return ReviewCardResponse(
            card_id=card.card_id,
            lexical_item_id=card.lexical_item_id,
            card_type=card.card_type,
            front_term=front,
            prompt=prompt,
            item=card.item,
        )

    @staticmethod
    def _timezone(name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValidationError(
                message="A valid IANA timezone is required.", code="invalid_timezone"
            ) from exc
