from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ExternalServiceError
from app.db.database import Database
from app.db.models import LearningEventRow
from app.db.serialization import document
from app.modules.learning_events.models import LearningEvent


class LearningEventRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_by_id(self, uid: str, event_id: UUID) -> LearningEvent | None:
        try:
            with self._database.session() as session:
                row = session.get(LearningEventRow, (uid, str(event_id)))
                return LearningEvent.model_validate(row.payload) if row else None
        except Exception as exc:
            raise self._error() from exc

    def create(self, uid: str, event: LearningEvent) -> LearningEvent:
        try:
            with self._database.session() as session:
                session.add(
                    LearningEventRow(
                        learner_id=uid,
                        event_id=str(event.event_id),
                        server_received_at=event.server_received_at,
                        event_type=event.event_type.value,
                        payload=document(event),
                    )
                )
            return event
        except IntegrityError:
            existing = self.get_by_id(uid, event.event_id)
            if existing is not None:
                return existing
            raise self._error()
        except Exception as exc:
            raise self._error() from exc

    def list_recent(
        self, uid: str, *, limit: int, before_server_received_at: datetime | None
    ) -> list[LearningEvent]:
        try:
            statement = select(LearningEventRow).where(LearningEventRow.learner_id == uid)
            if before_server_received_at is not None:
                statement = statement.where(
                    LearningEventRow.server_received_at < before_server_received_at
                )
            statement = statement.order_by(LearningEventRow.server_received_at.desc()).limit(limit)
            with self._database.session() as session:
                return [
                    LearningEvent.model_validate(row.payload)
                    for row in session.scalars(statement).all()
                ]
        except Exception as exc:
            raise self._error() from exc

    def list_between(
        self, uid: str, start_utc: datetime, end_utc_exclusive: datetime
    ) -> list[LearningEvent]:
        try:
            with self._database.session() as session:
                rows = session.scalars(
                    select(LearningEventRow)
                    .where(
                        LearningEventRow.learner_id == uid,
                        LearningEventRow.server_received_at >= start_utc,
                        LearningEventRow.server_received_at < end_utc_exclusive,
                    )
                    .order_by(LearningEventRow.server_received_at)
                ).all()
                return [LearningEvent.model_validate(row.payload) for row in rows]
        except Exception as exc:
            raise self._error() from exc

    @staticmethod
    def _error() -> ExternalServiceError:
        return ExternalServiceError(
            message="Learning event data is temporarily unavailable.",
            code="learning_event_persistence_error",
        )
