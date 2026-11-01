from datetime import UTC, datetime
from typing import Any

from app.core.auth import AuthenticatedUser
from app.core.exceptions import NotFoundError
from app.modules.users.models import UserProfile
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserProfileUpdate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def get_or_create_profile(self, identity: AuthenticatedUser) -> UserProfile:
        # Both authentication mechanisms resolve an existing PostgreSQL learner.
        # Provisioning is exclusively an explicit private administrative operation.
        return self.get_profile(identity.uid)

    def get_profile(self, uid: str) -> UserProfile:
        profile = self._repository.get_by_uid(uid)
        if profile is None:
            raise NotFoundError(message="User profile not found.", code="profile_not_found")
        return profile

    def update_profile(
        self,
        identity: AuthenticatedUser,
        request: UserProfileUpdate,
    ) -> UserProfile:
        self.get_or_create_profile(identity)
        changes: dict[str, Any] = request.model_dump(exclude_unset=True)
        if not changes:
            return self.get_profile(identity.uid)
        changes["updated_at"] = datetime.now(UTC)
        return self._repository.update(identity.uid, changes)
