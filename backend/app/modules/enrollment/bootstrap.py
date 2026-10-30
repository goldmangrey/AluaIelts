from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import HouseholdProfileRow, LearnerProfileRow
from app.db.serialization import document
from app.modules.users.models import UserProfile, UserRole

ROLES = {"husband": "Муж", "wife": "Жена"}


def household_lock(session: Session) -> None:
    # Serialize redemption and administrative changes across PostgreSQL workers.
    # Released at transaction end, including rollback. Never a process-local lock.
    session.execute(text("SELECT pg_advisory_xact_lock(19770429, 2)"))


def bind_existing(session: Session, role: str, learner_id: str) -> None:
    if role not in ROLES:
        raise ValueError("Unknown household role")
    if session.get(LearnerProfileRow, learner_id) is None:
        raise NotFoundError(message="Learner not found.", code="learner_not_found")
    existing = session.get(HouseholdProfileRow, role)
    if existing:
        if existing.learner_id != learner_id:
            raise ConflictError(
                message="Role already bound; refusing to replace progress.",
                code="household_role_already_bound",
            )
        return
    if session.scalar(
        select(HouseholdProfileRow).where(HouseholdProfileRow.learner_id == learner_id)
    ):
        raise ConflictError(
            message="Learner already has another household role.",
            code="household_learner_already_bound",
        )
    session.add(HouseholdProfileRow(role=role, learner_id=learner_id))
    session.flush()


def ensure_profiles(session: Session) -> None:
    for role, name in ROLES.items():
        if session.get(HouseholdProfileRow, role):
            continue
        now = datetime.now(UTC)
        profile = UserProfile(
            uid=str(uuid4()),
            display_name=name,
            role=UserRole.LEARNER,
            created_at=now,
            updated_at=now,
        )
        session.add(
            LearnerProfileRow(
                learner_id=profile.uid,
                display_name=name,
                created_at=now,
                updated_at=now,
                payload=document(profile),
            )
        )
        session.flush()
        session.add(HouseholdProfileRow(role=role, learner_id=profile.uid))
        session.flush()
