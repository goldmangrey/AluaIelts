from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, ExternalServiceError
from app.db.database import Database
from app.db.models import LearnerProfileRow
from app.db.serialization import document
from app.modules.users.models import UserProfile


class UserRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_by_uid(self, uid: str) -> UserProfile | None:
        try:
            with self._database.session() as session:
                row = session.get(LearnerProfileRow, uid)
                return UserProfile.model_validate(row.payload) if row else None
        except Exception as exc:
            raise self._error("profile_read_failed") from exc

    def create(self, profile: UserProfile) -> UserProfile:
        try:
            with self._database.session() as session:
                session.add(
                    LearnerProfileRow(
                        learner_id=profile.uid,
                        display_name=profile.display_name or "Learner",
                        created_at=profile.created_at,
                        updated_at=profile.updated_at,
                        payload=document(profile),
                    )
                )
            return profile
        except IntegrityError as exc:
            raise ConflictError(
                message="The user profile already exists.", code="profile_already_exists"
            ) from exc
        except Exception as exc:
            raise self._error("profile_create_failed") from exc

    def update(self, uid: str, changes: dict[str, Any]) -> UserProfile:
        try:
            with self._database.session() as session:
                row = session.get(LearnerProfileRow, uid, with_for_update=True)
                if row is None:
                    raise ValueError("Learner profile does not exist")
                profile = UserProfile.model_validate(row.payload).model_copy(update=changes)
                row.payload = document(profile)
                row.display_name = profile.display_name or "Learner"
                row.updated_at = changes.get("updated_at", datetime.now(UTC))
            return profile
        except Exception as exc:
            raise self._error("profile_update_failed") from exc

    @staticmethod
    def _error(code: str) -> ExternalServiceError:
        return ExternalServiceError(
            message="The user profile is temporarily unavailable.", code=code
        )
