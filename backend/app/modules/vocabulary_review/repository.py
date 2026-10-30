from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, ExternalServiceError
from app.db.database import Database
from app.db.models import (
    CanonicalVocabularyStateRow,
    ReviewResponseRow,
    ReviewSessionRow,
    VocabularyPackRow,
)
from app.db.serialization import document
from app.modules.vocabulary_review.models import (
    DailyLexicalPack,
    VocabularyReviewEvent,
    VocabularyReviewSession,
    VocabularyReviewState,
)


class VocabularyReviewRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_pack(self, uid: str, pack_id: str) -> DailyLexicalPack | None:
        return self._get(VocabularyPackRow, (uid, pack_id), DailyLexicalPack)

    def pack_document_exists(self, uid: str, pack_id: str) -> bool:
        return self.get_pack(uid, pack_id) is not None

    def list_packs(self, uid: str) -> list[DailyLexicalPack]:
        return self._list(
            select(VocabularyPackRow).where(
                VocabularyPackRow.learner_id == uid,
                VocabularyPackRow.schema_version == 2,
            ),
            DailyLexicalPack,
        )

    def create_pack(self, uid: str, pack: DailyLexicalPack) -> DailyLexicalPack:
        try:
            with self._database.session() as session:
                session.add(
                    VocabularyPackRow(
                        learner_id=uid,
                        pack_id=pack.pack_id,
                        local_date=pack.local_date,
                        schema_version=pack.schema_version,
                        payload=document(pack),
                    )
                )
            return pack
        except IntegrityError:
            existing = self.get_pack(uid, pack.pack_id)
            if existing:
                return existing
            raise self._error()
        except Exception as exc:
            raise self._error() from exc

    def get_state(self, uid: str, lexical_item_id: str) -> VocabularyReviewState | None:
        value = self._get(
            CanonicalVocabularyStateRow,
            (uid, lexical_item_id),
            VocabularyReviewState,
        )
        return value if value is None or value.schema_version == 2 else None

    def list_states(self, uid: str) -> list[VocabularyReviewState]:
        return self._list(
            select(CanonicalVocabularyStateRow).where(
                CanonicalVocabularyStateRow.learner_id == uid,
                CanonicalVocabularyStateRow.schema_version == 2,
            ),
            VocabularyReviewState,
        )

    def get_session(self, uid: str, session_id: str) -> VocabularyReviewSession | None:
        return self._get(ReviewSessionRow, (uid, session_id), VocabularyReviewSession)

    def session_document_exists(self, uid: str, session_id: str) -> bool:
        return self.get_session(uid, session_id) is not None

    def create_session(self, uid: str, value: VocabularyReviewSession) -> VocabularyReviewSession:
        try:
            with self._database.session() as session:
                session.add(
                    ReviewSessionRow(
                        learner_id=uid,
                        session_id=value.session_id,
                        session_type=value.kind.value,
                        payload=document(value),
                    )
                )
            return value
        except IntegrityError:
            existing = self.get_session(uid, value.session_id)
            if existing:
                return existing
            raise self._error()
        except Exception as exc:
            raise self._error() from exc

    def get_event(self, uid: str, event_id: str) -> VocabularyReviewEvent | None:
        return self._get(ReviewResponseRow, (uid, event_id), VocabularyReviewEvent)

    def apply_event(
        self,
        uid: str,
        event: VocabularyReviewEvent,
        previous: VocabularyReviewState,
        updated: VocabularyReviewState,
    ) -> tuple[VocabularyReviewEvent, VocabularyReviewState]:
        try:
            with self._database.session() as session:
                existing_row = session.get(ReviewResponseRow, (uid, event.event_id))
                state_row = session.get(
                    CanonicalVocabularyStateRow,
                    (uid, event.lexical_item_id),
                    with_for_update=True,
                )
                if existing_row:
                    existing = VocabularyReviewEvent.model_validate(existing_row.payload)
                    self._assert_same_event(existing, event)
                    state = (
                        VocabularyReviewState.model_validate(state_row.payload)
                        if state_row
                        else previous
                    )
                    return existing, state
                current = (
                    VocabularyReviewState.model_validate(state_row.payload)
                    if state_row and state_row.schema_version == updated.schema_version
                    else previous
                )
                if current.review_count != previous.review_count:
                    raise ConflictError(
                        message="Vocabulary review state changed; reload the session.",
                        code="vocabulary_review_state_conflict",
                    )
                session.add(
                    ReviewResponseRow(
                        learner_id=uid,
                        event_id=event.event_id,
                        session_id=event.session_id,
                        lexical_item_id=event.lexical_item_id,
                        rating=event.rating.value,
                        occurred_at=event.reviewed_at,
                        payload=document(event),
                    )
                )
                if state_row is None:
                    session.add(self._state_row(uid, updated))
                else:
                    state_row.review_count = updated.review_count
                    state_row.due_at = updated.next_due_at
                    state_row.schema_version = updated.schema_version
                    state_row.payload = document(updated)
            return event, updated
        except ConflictError:
            raise
        except IntegrityError:
            recovered = self.get_event(uid, event.event_id)
            if recovered is None:
                raise self._error()
            self._assert_same_event(recovered, event)
            return recovered, self.get_state(uid, event.lexical_item_id) or previous
        except Exception as exc:
            raise self._error() from exc

    def list_events_for_session(self, uid: str, session_id: str) -> list[VocabularyReviewEvent]:
        return self._list(
            select(ReviewResponseRow).where(
                ReviewResponseRow.learner_id == uid,
                ReviewResponseRow.session_id == session_id,
            ),
            VocabularyReviewEvent,
        )

    def _get(self, row_type, key, model):  # type: ignore[no-untyped-def]
        try:
            with self._database.session() as session:
                row = session.get(row_type, key)
                return model.model_validate(row.payload) if row else None
        except PydanticValidationError:
            return None
        except Exception as exc:
            raise self._error() from exc

    def _list(self, statement, model):  # type: ignore[no-untyped-def]
        try:
            with self._database.session() as session:
                values = []
                for row in session.scalars(statement).all():
                    try:
                        values.append(model.model_validate(row.payload))
                    except PydanticValidationError:
                        continue
                return values
        except Exception as exc:
            raise self._error() from exc

    @staticmethod
    def _state_row(uid: str, value: VocabularyReviewState) -> CanonicalVocabularyStateRow:
        return CanonicalVocabularyStateRow(
            learner_id=uid,
            lexical_item_id=value.lexical_item_id,
            review_count=value.review_count,
            due_at=value.next_due_at,
            schema_version=value.schema_version,
            payload=document(value),
        )

    @staticmethod
    def _assert_same_event(
        existing: VocabularyReviewEvent, requested: VocabularyReviewEvent
    ) -> None:
        if (
            existing.session_id != requested.session_id
            or existing.lexical_item_id != requested.lexical_item_id
            or existing.rating != requested.rating
        ):
            raise ConflictError(
                message="Review event ID was reused with different content.",
                code="vocabulary_review_event_conflict",
            )

    @staticmethod
    def _error() -> ExternalServiceError:
        return ExternalServiceError(
            message="Vocabulary learning data is temporarily unavailable.",
            code="vocabulary_review_persistence_error",
        )
