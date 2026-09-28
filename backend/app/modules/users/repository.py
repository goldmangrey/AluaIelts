from typing import Any

from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore import Client

from app.core.exceptions import ConflictError, ExternalServiceError
from app.modules.users.models import UserProfile


class UserRepository:
    collection_name = "users"

    def __init__(self, client: Client) -> None:
        self._collection = client.collection(self.collection_name)

    def get_by_uid(self, uid: str) -> UserProfile | None:
        try:
            snapshot = self._collection.document(uid).get()
            if not snapshot.exists:
                return None
            data = snapshot.to_dict()
            return UserProfile.model_validate(data) if data else None
        except Exception as exc:
            raise ExternalServiceError(
                message="The user profile could not be loaded.",
                code="profile_read_failed",
            ) from exc

    def create(self, profile: UserProfile) -> UserProfile:
        try:
            self._collection.document(profile.uid).create(profile.model_dump(mode="python"))
            return profile
        except AlreadyExists as exc:
            raise ConflictError(
                message="The user profile already exists.",
                code="profile_already_exists",
            ) from exc
        except Exception as exc:
            raise ExternalServiceError(
                message="The user profile could not be created.",
                code="profile_create_failed",
            ) from exc

    def update(self, uid: str, changes: dict[str, Any]) -> UserProfile:
        try:
            reference = self._collection.document(uid)
            reference.update(changes)
            data = reference.get().to_dict()
            if not data:
                raise ExternalServiceError(
                    message="The updated user profile could not be loaded.",
                    code="profile_read_failed",
                )
            return UserProfile.model_validate(data)
        except ExternalServiceError:
            raise
        except Exception as exc:
            raise ExternalServiceError(
                message="The user profile could not be updated.",
                code="profile_update_failed",
            ) from exc
