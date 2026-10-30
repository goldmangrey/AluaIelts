from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, ExternalServiceError, NotFoundError
from app.db.database import Database
from app.db.models import PartnerInvitationRow, PartnerPermissionRow, PartnerRelationshipRow
from app.db.serialization import document
from app.modules.partner.models import (
    PartnerInvitation,
    PartnerInviteStatus,
    PartnerRelationship,
    PartnerRelationshipStatus,
    PartnerSharingSettings,
)


class PartnerRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_relationship(self, relationship_id: str) -> PartnerRelationship | None:
        try:
            with self._database.session() as session:
                row = session.get(PartnerRelationshipRow, relationship_id)
                return PartnerRelationship.model_validate(row.payload) if row else None
        except Exception as exc:
            raise self._error() from exc

    def _active_for(self, field, uid: str) -> PartnerRelationship | None:  # type: ignore[no-untyped-def]
        try:
            with self._database.session() as session:
                row = session.scalar(
                    select(PartnerRelationshipRow).where(
                        field == uid,
                        PartnerRelationshipRow.status == PartnerRelationshipStatus.ACTIVE.value,
                    )
                )
                return PartnerRelationship.model_validate(row.payload) if row else None
        except Exception as exc:
            raise self._error() from exc

    def get_active_by_learner(self, uid: str) -> PartnerRelationship | None:
        return self._active_for(PartnerRelationshipRow.learner_id, uid)

    def get_active_by_partner(self, uid: str) -> PartnerRelationship | None:
        return self._active_for(PartnerRelationshipRow.partner_id, uid)

    def create_invite(self, invitation: PartnerInvitation) -> PartnerInvitation:
        try:
            with self._database.session() as session:
                active_relationship = session.scalar(
                    select(PartnerRelationshipRow)
                    .where(
                        PartnerRelationshipRow.learner_id == invitation.learner_uid,
                        PartnerRelationshipRow.status == PartnerRelationshipStatus.ACTIVE.value,
                    )
                    .with_for_update()
                )
                if active_relationship:
                    raise ConflictError(
                        message="The learner already has a partner.",
                        code="learner_already_has_partner",
                    )
                prior = session.scalars(
                    select(PartnerInvitationRow)
                    .where(
                        PartnerInvitationRow.learner_id == invitation.learner_uid,
                        PartnerInvitationRow.status == PartnerInviteStatus.ACTIVE.value,
                    )
                    .with_for_update()
                ).all()
                for row in prior:
                    old = PartnerInvitation.model_validate(row.payload).model_copy(
                        update={"status": PartnerInviteStatus.REVOKED}
                    )
                    row.status = PartnerInviteStatus.REVOKED.value
                    row.payload = document(old)
                session.add(
                    PartnerInvitationRow(
                        code_hash=invitation.code_hash,
                        learner_id=invitation.learner_uid,
                        status=invitation.status.value,
                        expires_at=invitation.expires_at,
                        payload=document(invitation),
                    )
                )
            return invitation
        except ConflictError:
            raise
        except Exception as exc:
            raise self._error() from exc

    def accept_invite(
        self,
        *,
        code_hash: str,
        partner_uid: str,
        relationship_factory: Callable[[str], PartnerRelationship],
    ) -> PartnerRelationship:
        try:
            with self._database.session() as session:
                invite_row = session.get(PartnerInvitationRow, code_hash, with_for_update=True)
                if invite_row is None:
                    raise NotFoundError(
                        message="Invitation is invalid.", code="partner_invite_not_found"
                    )
                invite = PartnerInvitation.model_validate(invite_row.payload)
                now = datetime.now(UTC)
                if invite.status != PartnerInviteStatus.ACTIVE:
                    raise ConflictError(
                        message="Invitation is no longer active.",
                        code="partner_invite_already_used",
                    )
                if invite.expires_at <= now:
                    expired = invite.model_copy(update={"status": PartnerInviteStatus.EXPIRED})
                    invite_row.status = expired.status.value
                    invite_row.payload = document(expired)
                    raise ConflictError(
                        message="Invitation has expired.", code="partner_invite_expired"
                    )
                if invite.learner_uid == partner_uid:
                    raise ConflictError(
                        message="You cannot accept your own invitation.",
                        code="partner_self_pairing_not_allowed",
                    )
                existing_learner = session.scalar(
                    select(PartnerRelationshipRow).where(
                        PartnerRelationshipRow.learner_id == invite.learner_uid,
                        PartnerRelationshipRow.status == PartnerRelationshipStatus.ACTIVE.value,
                    )
                )
                existing_partner = session.scalar(
                    select(PartnerRelationshipRow).where(
                        PartnerRelationshipRow.partner_id == partner_uid,
                        PartnerRelationshipRow.status == PartnerRelationshipStatus.ACTIVE.value,
                    )
                )
                if existing_learner:
                    raise ConflictError(
                        message="The learner already has a partner.",
                        code="learner_already_has_partner",
                    )
                if existing_partner:
                    raise ConflictError(
                        message="You already monitor a learner.",
                        code="partner_already_connected",
                    )
                relationship = relationship_factory(invite.learner_uid)
                session.add(self._relationship_row(relationship))
                # Persist the FK parent before permissions (no ORM relationship orders these).
                session.flush()
                session.add(self._permission_row(relationship))
                accepted = invite.model_copy(
                    update={
                        "status": PartnerInviteStatus.ACCEPTED,
                        "accepted_at": now,
                        "accepted_by_uid": partner_uid,
                    }
                )
                invite_row.status = accepted.status.value
                invite_row.payload = document(accepted)
                return relationship
        except (ConflictError, NotFoundError):
            raise
        except IntegrityError as exc:
            raise ConflictError(
                message="A partner relationship already exists.",
                code="partner_relationship_conflict",
            ) from exc
        except Exception as exc:
            raise self._error() from exc

    def update_sharing(
        self, relationship: PartnerRelationship, settings: PartnerSharingSettings
    ) -> PartnerRelationship:
        updated = relationship.model_copy(
            update={"sharing_settings": settings, "updated_at": datetime.now(UTC)}
        )
        try:
            with self._database.session() as session:
                row = session.get(
                    PartnerRelationshipRow, updated.relationship_id, with_for_update=True
                )
                if row is None:
                    raise ValueError("Relationship does not exist")
                row.payload = document(updated)
                permission = session.get(PartnerPermissionRow, updated.relationship_id)
                values = self._permission_row(updated)
                if permission is None:
                    session.add(values)
                else:
                    permission.daily_activity = values.daily_activity
                    permission.progress_analytics = values.progress_analytics
                    permission.ai_analysis = values.ai_analysis
                    permission.updated_at = values.updated_at
            return updated
        except Exception as exc:
            raise self._error() from exc

    def revoke(self, relationship: PartnerRelationship) -> PartnerRelationship:
        now = datetime.now(UTC)
        updated = relationship.model_copy(
            update={
                "status": PartnerRelationshipStatus.REVOKED,
                "revoked_at": now,
                "updated_at": now,
            }
        )
        try:
            with self._database.session() as session:
                row = session.get(
                    PartnerRelationshipRow, relationship.relationship_id, with_for_update=True
                )
                if row is None:
                    raise ValueError("Relationship does not exist")
                row.status = updated.status.value
                row.payload = document(updated)
            return updated
        except Exception as exc:
            raise self._error() from exc

    @staticmethod
    def _relationship_row(value: PartnerRelationship) -> PartnerRelationshipRow:
        return PartnerRelationshipRow(
            relationship_id=value.relationship_id,
            learner_id=value.learner_uid,
            partner_id=value.partner_uid,
            status=value.status.value,
            payload=document(value),
        )

    @staticmethod
    def _permission_row(value: PartnerRelationship) -> PartnerPermissionRow:
        settings = value.sharing_settings
        return PartnerPermissionRow(
            relationship_id=value.relationship_id,
            daily_activity=settings.share_daily_activity,
            progress_analytics=settings.share_progress_analytics,
            ai_analysis=settings.allow_ai_progress_analysis,
            updated_at=value.updated_at,
        )

    @staticmethod
    def _error() -> ExternalServiceError:
        return ExternalServiceError(
            message="Partner data is temporarily unavailable.", code="partner_persistence_error"
        )
