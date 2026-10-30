from collections.abc import Callable
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ExternalServiceError
from app.db.database import Database
from app.db.models import MasteryEvidenceRow, MasteryStateRow
from app.db.serialization import document
from app.modules.mastery.models import MasteryState


def make_application_id(event_id: UUID, state_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"alua:mastery:{event_id}:{state_id}"))


class MasteryRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, uid: str, state_id: str) -> MasteryState | None:
        try:
            with self._database.session() as session:
                row = session.get(MasteryStateRow, (uid, state_id))
                return MasteryState.model_validate(row.payload) if row else None
        except Exception as exc:
            raise self._persistence_error() from exc

    def list_states(self, uid: str) -> list[MasteryState]:
        try:
            with self._database.session() as session:
                rows = session.scalars(
                    select(MasteryStateRow).where(MasteryStateRow.learner_id == uid)
                ).all()
                return [MasteryState.model_validate(row.payload) for row in rows]
        except Exception as exc:
            raise self._persistence_error() from exc

    def count_distinct_applied_events(self, uid: str) -> int:
        try:
            with self._database.session() as session:
                return int(
                    session.scalar(
                        select(func.count(func.distinct(MasteryEvidenceRow.event_id))).where(
                            MasteryEvidenceRow.learner_id == uid
                        )
                    )
                    or 0
                )
        except Exception as exc:
            raise self._persistence_error() from exc

    def apply_once(
        self,
        *,
        uid: str,
        event_id: UUID,
        state_id: str,
        applied_at: datetime,
        project: Callable[[MasteryState | None], MasteryState],
    ) -> MasteryState:
        application_id = make_application_id(event_id, state_id)
        try:
            with self._database.session() as session:
                state_row = session.get(MasteryStateRow, (uid, state_id), with_for_update=True)
                marker = session.get(MasteryEvidenceRow, application_id)
                current = MasteryState.model_validate(state_row.payload) if state_row else None
                if marker:
                    if current is None:
                        raise ValueError("Applied evidence marker exists without its projection.")
                    return current
                updated = project(current)
                if state_row is None:
                    session.add(
                        MasteryStateRow(
                            learner_id=uid,
                            state_id=state_id,
                            updated_at=updated.updated_at,
                            payload=document(updated),
                        )
                    )
                else:
                    state_row.updated_at = updated.updated_at
                    state_row.payload = document(updated)
                session.add(
                    MasteryEvidenceRow(
                        application_id=application_id,
                        learner_id=uid,
                        event_id=str(event_id),
                        state_id=state_id,
                        applied_at=applied_at,
                        engine_version=str(updated.engine_version),
                    )
                )
                return updated
        except IntegrityError:
            existing = self.get(uid, state_id)
            if existing:
                return existing
            raise self._persistence_error()
        except Exception as exc:
            raise self._persistence_error() from exc

    @staticmethod
    def _persistence_error() -> ExternalServiceError:
        return ExternalServiceError(
            message="Mastery data is temporarily unavailable.",
            code="mastery_persistence_error",
        )
