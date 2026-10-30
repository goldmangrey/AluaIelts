import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationError
from app.modules.daily_plan.models import (
    DailyPlanContentType,
    DailyPlanItemKind,
    DailyPlanItemState,
)
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.partner.models import (
    PartnerInvitation,
    PartnerRelationship,
    PartnerSharingSettings,
)
from app.modules.partner.repository import PartnerRepository
from app.modules.partner.schemas import (
    PartnerDashboardSnapshot,
    PartnerInviteResponse,
    PartnerLearnerSummary,
    PartnerLearningProfile,
    PartnerRelationshipSummary,
    PartnerStatusResponse,
    PartnerTodayActivity,
)
from app.modules.progress.service import SUPPORTED_PERIODS, ProgressAnalyticsService
from app.modules.student_model.service import StudentModelService
from app.modules.users.repository import UserRepository

INVITE_TTL = timedelta(hours=24)
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def normalize_invite_code(code: str) -> str:
    normalized = code.strip().upper().replace("-", "")
    if len(normalized) != 10 or any(value not in INVITE_ALPHABET for value in normalized):
        raise ValidationError(message="Invitation code is invalid.", code="partner_invite_invalid")
    return normalized


def hash_invite_code(code: str) -> str:
    return hashlib.sha256(normalize_invite_code(code).encode()).hexdigest()


class PartnerService:
    def __init__(
        self,
        *,
        repository: PartnerRepository,
        users: UserRepository,
        plans: DailyPlanRepository,
        progress: ProgressAnalyticsService,
        student_model: StudentModelService,
    ) -> None:
        self._repository = repository
        self._users = users
        self._plans = plans
        self._progress = progress
        self._student_model = student_model

    def create_invite(self, learner_uid: str) -> PartnerInviteResponse:
        raw = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(10))
        code = f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"
        now = datetime.now(UTC)
        code_hash = hash_invite_code(code)
        invitation = PartnerInvitation(
            invite_id=code_hash,
            learner_uid=learner_uid,
            code_hash=code_hash,
            created_at=now,
            expires_at=now + INVITE_TTL,
        )
        self._repository.create_invite(invitation)
        return PartnerInviteResponse(
            invite_id=invitation.invite_id, code=code, expires_at=invitation.expires_at
        )

    def accept_invite(self, partner_uid: str, code: str) -> PartnerRelationship:
        code_hash = hash_invite_code(code)

        def relationship(learner_uid: str) -> PartnerRelationship:
            now = datetime.now(UTC)
            relationship_id = str(uuid5(NAMESPACE_URL, f"alua:partner:{learner_uid}:{partner_uid}"))
            return PartnerRelationship(
                relationship_id=relationship_id,
                learner_uid=learner_uid,
                partner_uid=partner_uid,
                sharing_settings=PartnerSharingSettings(),
                created_at=now,
                updated_at=now,
            )

        return self._repository.accept_invite(
            code_hash=code_hash, partner_uid=partner_uid, relationship_factory=relationship
        )

    def get_status(self, uid: str) -> PartnerStatusResponse:
        sharing = self._repository.get_active_by_learner(uid)
        monitoring = self._repository.get_active_by_partner(uid)
        return PartnerStatusResponse(
            sharing_my_progress=self._summary(sharing, sharing.partner_uid) if sharing else None,
            monitoring_learner=self._summary(monitoring, monitoring.learner_uid)
            if monitoring
            else None,
        )

    def update_sharing(
        self, learner_uid: str, settings: PartnerSharingSettings
    ) -> PartnerStatusResponse:
        relationship = self._repository.get_active_by_learner(learner_uid)
        if relationship is None:
            raise NotFoundError(
                message="Active relationship not found.", code="partner_relationship_not_found"
            )
        self._repository.update_sharing(relationship, settings)
        return self.get_status(learner_uid)

    def revoke(self, uid: str) -> PartnerStatusResponse:
        relationship = self._repository.get_active_by_learner(
            uid
        ) or self._repository.get_active_by_partner(uid)
        if relationship is None:
            raise NotFoundError(
                message="Active relationship not found.", code="partner_relationship_not_found"
            )
        self._repository.revoke(relationship)
        return self.get_status(uid)

    def get_dashboard(
        self, partner_uid: str, days: int, timezone_name: str
    ) -> PartnerDashboardSnapshot:
        relationship = self._repository.get_active_by_partner(partner_uid)
        if relationship is None:
            raise UnauthorizedError(
                message="Partner access is not authorized.", code="partner_not_authorized"
            )
        if days not in SUPPORTED_PERIODS:
            raise ValidationError(
                message="Period must be 7, 30, or 90 days.", code="progress_invalid_period"
            )
        try:
            timezone = ZoneInfo(timezone_name)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValidationError(
                message="A valid IANA timezone is required.", code="progress_invalid_timezone"
            ) from exc
        settings = relationship.sharing_settings
        snapshot = (
            self._progress.get_snapshot(relationship.learner_uid, days, timezone_name)
            if settings.share_progress_analytics or settings.share_recent_error_patterns
            else None
        )
        student = (
            self._student_model.get_snapshot(relationship.learner_uid)
            if settings.share_learning_profile
            else None
        )
        learner = self._users.get_by_uid(relationship.learner_uid)
        return PartnerDashboardSnapshot(
            learner=PartnerLearnerSummary(
                display_name=(
                    learner.display_name if learner and learner.display_name else "Learner"
                )
            ),
            relationship_id=relationship.relationship_id,
            connected_at=relationship.created_at,
            permissions=settings,
            today_activity=self._today(
                relationship.learner_uid, datetime.now(UTC).astimezone(timezone).date()
            )
            if settings.share_daily_activity
            else None,
            progress=snapshot if settings.share_progress_analytics else None,
            learning_profile=(
                PartnerLearningProfile(
                    curriculum=student.curriculum,
                    mastery=student.mastery,
                    strengths=student.strengths,
                    weaknesses=student.weaknesses,
                    data_quality=student.data_quality,
                )
                if student
                else None
            ),
            recent_errors=snapshot.recent_errors
            if snapshot and settings.share_recent_error_patterns
            else None,
            generated_at=datetime.now(UTC),
        )

    def _today(self, uid: str, local_date) -> PartnerTodayActivity:  # type: ignore[no-untyped-def]
        plan = self._plans.get(uid, local_date)
        if plan is None:
            return PartnerTodayActivity(local_date=local_date, has_plan=False)
        completed = [item for item in plan.items if item.state == DailyPlanItemState.COMPLETED]
        pending = [item for item in plan.items if item.state != DailyPlanItemState.COMPLETED]
        focus = next((item.title for item in pending if item.priority.value == "high"), None) or (
            pending[0].title if pending else None
        )
        return PartnerTodayActivity(
            local_date=local_date,
            has_plan=True,
            target_minutes=plan.target_minutes,
            estimated_minutes=plan.estimated_minutes,
            estimated_completed_minutes=sum(item.estimated_minutes for item in completed),
            total_items=len(plan.items),
            completed_items=len(completed),
            remaining_items=len(plan.items) - len(completed),
            plan_status=plan.status.value,
            current_focus=focus,
            grammar_items=sum(
                item.content_type == DailyPlanContentType.GRAMMAR_LESSON for item in plan.items
            ),
            vocabulary_items=sum(
                item.content_type == DailyPlanContentType.VOCABULARY_ITEM for item in plan.items
            ),
            review_items=sum(
                item.kind
                in {
                    DailyPlanItemKind.GRAMMAR_REVIEW,
                    DailyPlanItemKind.VOCABULARY_REVIEW,
                    DailyPlanItemKind.REINFORCEMENT,
                }
                for item in plan.items
            ),
        )

    def _summary(
        self, relationship: PartnerRelationship, other_uid: str
    ) -> PartnerRelationshipSummary:
        profile = self._users.get_by_uid(other_uid)
        return PartnerRelationshipSummary(
            relationship_id=relationship.relationship_id,
            display_name=profile.display_name
            if profile and profile.display_name
            else ("Partner" if other_uid == relationship.partner_uid else "Learner"),
            connected_at=relationship.created_at,
            sharing_settings=relationship.sharing_settings,
        )
