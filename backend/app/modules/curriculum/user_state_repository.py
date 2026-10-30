from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, ExternalServiceError
from app.db.database import Database
from app.db.models import CurriculumStateRow
from app.db.serialization import document
from app.modules.curriculum.models import UserCurriculumState


class UserCurriculumRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, uid: str) -> UserCurriculumState | None:
        try:
            with self._database.session() as session:
                row = session.get(CurriculumStateRow, uid)
                return UserCurriculumState.model_validate(row.payload) if row else None
        except Exception as exc:
            raise self._error() from exc

    def create(self, uid: str, value: UserCurriculumState) -> UserCurriculumState:
        try:
            with self._database.session() as session:
                session.add(
                    CurriculumStateRow(
                        learner_id=uid,
                        updated_at=value.updated_at,
                        payload=document(value),
                    )
                )
            return value
        except IntegrityError as exc:
            raise ConflictError(
                message="Curriculum state already exists.", code="curriculum_state_exists"
            ) from exc
        except Exception as exc:
            raise self._error() from exc

    def update(self, uid: str, changes: dict[str, Any]) -> UserCurriculumState:
        try:
            with self._database.session() as session:
                row = session.get(CurriculumStateRow, uid, with_for_update=True)
                if row is None:
                    raise ValueError("Curriculum state does not exist")
                value = UserCurriculumState.model_validate(row.payload).model_copy(update=changes)
                row.updated_at = changes.get("updated_at", datetime.now(UTC))
                row.payload = document(value)
                return value
        except Exception as exc:
            raise self._error() from exc

    @staticmethod
    def _error() -> ExternalServiceError:
        return ExternalServiceError(
            message="Curriculum state is temporarily unavailable.",
            code="curriculum_state_error",
        )
