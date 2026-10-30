from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, ExternalServiceError
from app.db.database import Database
from app.db.models import ExerciseAnswerRow, ExerciseSessionRow
from app.db.serialization import document
from app.modules.exercises.models import ExerciseAttempt, ExerciseSession


class ExerciseRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_session(self, uid: str, session_id: str) -> ExerciseSession | None:
        try:
            with self._database.session() as session:
                row = session.get(ExerciseSessionRow, (uid, session_id))
                return ExerciseSession.model_validate(row.payload) if row else None
        except Exception as exc:
            raise self._error() from exc

    def create_session(self, uid: str, value: ExerciseSession) -> ExerciseSession:
        try:
            with self._database.session() as session:
                session.add(self._session_row(uid, value))
            return value
        except IntegrityError:
            existing = self.get_session(uid, value.session_id)
            if existing:
                return existing
            raise self._error()
        except Exception as exc:
            raise self._error() from exc

    def update_session(self, uid: str, value: ExerciseSession) -> ExerciseSession:
        try:
            with self._database.session() as session:
                row = session.get(ExerciseSessionRow, (uid, value.session_id), with_for_update=True)
                if row is None:
                    session.add(self._session_row(uid, value))
                else:
                    row.daily_plan_date = value.daily_plan_date
                    row.payload = document(value)
            return value
        except Exception as exc:
            raise self._error() from exc

    def get_attempt(self, uid: str, session_id: str, exercise_id: str) -> ExerciseAttempt | None:
        try:
            with self._database.session() as session:
                row = session.get(ExerciseAnswerRow, (uid, session_id, exercise_id))
                return ExerciseAttempt.model_validate(row.payload) if row else None
        except Exception as exc:
            raise self._error() from exc

    def list_attempts(self, uid: str, session_id: str) -> list[ExerciseAttempt]:
        try:
            with self._database.session() as session:
                rows = session.scalars(
                    select(ExerciseAnswerRow).where(
                        ExerciseAnswerRow.learner_id == uid,
                        ExerciseAnswerRow.session_id == session_id,
                    )
                ).all()
                return [ExerciseAttempt.model_validate(row.payload) for row in rows]
        except Exception as exc:
            raise self._error() from exc

    def create_attempt(self, uid: str, value: ExerciseAttempt) -> ExerciseAttempt:
        try:
            with self._database.session() as session:
                session.add(
                    ExerciseAnswerRow(
                        learner_id=uid,
                        session_id=value.session_id,
                        exercise_id=value.exercise_id,
                        attempt_id=str(value.attempt_id),
                        payload=document(value),
                    )
                )
            return value
        except IntegrityError:
            existing = self.get_attempt(uid, value.session_id, value.exercise_id)
            if existing and existing.attempt_id == value.attempt_id:
                if existing.submitted_answer == value.submitted_answer:
                    return existing
                raise ConflictError(
                    message="Attempt ID was already used with a different answer.",
                    code="exercise_attempt_id_conflict",
                )
            raise ConflictError(
                message="This exercise already has a scored attempt.",
                code="exercise_already_answered",
            )
        except ConflictError:
            raise
        except Exception as exc:
            raise self._error() from exc

    @staticmethod
    def _session_row(uid: str, value: ExerciseSession) -> ExerciseSessionRow:
        return ExerciseSessionRow(
            learner_id=uid,
            session_id=value.session_id,
            daily_plan_date=value.daily_plan_date,
            payload=document(value),
        )

    @staticmethod
    def _error() -> ExternalServiceError:
        return ExternalServiceError(
            message="Exercise data is temporarily unavailable.",
            code="exercise_persistence_error",
        )
