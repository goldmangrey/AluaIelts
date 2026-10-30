from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import ValidationError
from app.modules.ai_progress.models import AIProgressContext, AIProgressFact
from app.modules.daily_plan.models import DailyPlanItemState
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.partner.models import PartnerRelationship
from app.modules.progress.service import SUPPORTED_PERIODS, ProgressAnalyticsService
from app.modules.student_model.service import StudentModelService


class AIProgressContextBuilder:
    def __init__(
        self,
        *,
        progress: ProgressAnalyticsService,
        student_model: StudentModelService,
        plans: DailyPlanRepository,
    ) -> None:
        self._progress = progress
        self._student_model = student_model
        self._plans = plans

    def build(
        self, relationship: PartnerRelationship, days: int, timezone_name: str
    ) -> AIProgressContext:
        if days not in SUPPORTED_PERIODS:
            raise ValidationError(
                message="Analysis period must be 7, 30, or 90 days.",
                code="ai_progress_invalid_period",
            )
        try:
            timezone = ZoneInfo(timezone_name)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValidationError(
                message="A valid IANA timezone is required.",
                code="ai_progress_invalid_timezone",
            ) from exc

        permissions = relationship.sharing_settings
        learner_uid = relationship.learner_uid
        snapshot = (
            self._progress.get_snapshot(learner_uid, days, timezone.key)
            if permissions.share_progress_analytics or permissions.share_recent_error_patterns
            else None
        )
        student = (
            self._student_model.get_snapshot(learner_uid)
            if permissions.share_learning_profile
            else None
        )
        facts: list[AIProgressFact] = []
        progress_data: dict[str, object] | None = None
        errors_data: list[dict[str, object]] | None = None
        profile_data: dict[str, object] | None = None
        today_data: dict[str, object] | None = None

        if snapshot and permissions.share_progress_analytics:
            progress_data = self._progress_data(snapshot, facts)
        if snapshot and permissions.share_recent_error_patterns:
            errors_data = []
            for index, error in enumerate(snapshot.recent_errors):
                errors_data.append({"title": error.display_title, "count": error.count})
                facts.append(
                    AIProgressFact(
                        id=f"error.{index}",
                        label=f"Recent error pattern: {error.display_title}",
                        value=error.count,
                        unit="errors",
                    )
                )
        if student:
            profile_data = self._profile_data(student, facts)
        if permissions.share_daily_activity:
            today_data = self._today_data(
                learner_uid, datetime.now(UTC).astimezone(timezone).date(), facts
            )

        quality = {
            "assessment": snapshot.assessment.data_quality.value if snapshot else "unavailable",
            "attempt_count": snapshot.assessment.attempts if snapshot else 0,
            "mastery_coverage": student.data_quality.coverage_status.value
            if student
            else "unavailable",
            "assessed_skill_count": student.mastery.assessed_skill_count if student else 0,
        }
        return AIProgressContext(
            period={"days": days, "timezone": timezone.key},
            learner={"display_name": "Learner"},
            today=today_data,
            progress=progress_data,
            learning_profile=profile_data,
            recent_errors=errors_data,
            data_quality=quality,
            facts=tuple(facts),
            generated_at=datetime.now(UTC),
        )

    @staticmethod
    def _progress_data(snapshot, facts: list[AIProgressFact]) -> dict[str, object]:  # type: ignore[no-untyped-def]
        values: list[tuple[str, str, object, str | None]] = [
            ("progress.active_days", "Active days", snapshot.summary.active_days, "days"),
            ("progress.practice_days", "Practice days", snapshot.summary.practice_days, "days"),
            (
                "progress.completed_items",
                "Completed plan items",
                snapshot.summary.completed_items,
                "items",
            ),
            (
                "progress.estimated_completed_minutes",
                "Estimated completed study volume",
                snapshot.summary.estimated_completed_minutes,
                "estimated minutes",
            ),
            ("progress.attempts", "Assessment attempts", snapshot.assessment.attempts, "attempts"),
            (
                "progress.correct",
                "Correct assessment attempts",
                snapshot.assessment.correct,
                "attempts",
            ),
            (
                "progress.grammar.attempts",
                "Grammar attempts",
                snapshot.assessment.grammar.attempts,
                "attempts",
            ),
            (
                "progress.vocabulary.attempts",
                "Vocabulary attempts",
                snapshot.assessment.vocabulary.attempts,
                "attempts",
            ),
            (
                "mastery.grammar.assessed",
                "Assessed grammar lessons",
                snapshot.mastery.grammar.assessed,
                "lessons",
            ),
            (
                "mastery.grammar.strong",
                "Strong assessed grammar lessons",
                snapshot.mastery.grammar.strong,
                "lessons",
            ),
            (
                "mastery.vocabulary.assessed",
                "Assessed vocabulary items",
                snapshot.mastery.vocabulary.assessed,
                "items",
            ),
            (
                "mastery.vocabulary.strong",
                "Strong assessed vocabulary items",
                snapshot.mastery.vocabulary.strong,
                "items",
            ),
        ]
        optional = [
            ("progress.accuracy", "Assessment accuracy", snapshot.assessment.accuracy, "ratio"),
            (
                "progress.grammar.accuracy",
                "Grammar accuracy",
                snapshot.assessment.grammar.accuracy,
                "ratio",
            ),
            (
                "progress.vocabulary.accuracy",
                "Vocabulary accuracy",
                snapshot.assessment.vocabulary.accuracy,
                "ratio",
            ),
            (
                "comparison.accuracy_delta_pp",
                "Accuracy change from previous period",
                snapshot.comparison.accuracy_percentage_points_delta,
                "percentage points",
            ),
            (
                "comparison.completed_items_delta",
                "Completed-item change from previous period",
                snapshot.comparison.completed_items_delta,
                "items",
            ),
        ]
        values.extend(value for value in optional if value[2] is not None)
        facts.extend(
            AIProgressFact(id=id_, label=label, value=value, unit=unit)
            for id_, label, value, unit in values
        )
        return {
            "summary": snapshot.summary.model_dump(mode="json"),
            "assessment": snapshot.assessment.model_dump(mode="json", exclude={"dimensions"}),
            "mastery": snapshot.mastery.model_dump(mode="json"),
            "comparison": snapshot.comparison.model_dump(mode="json"),
        }

    @staticmethod
    def _profile_data(student, facts: list[AIProgressFact]) -> dict[str, object]:  # type: ignore[no-untyped-def]
        strengths = []
        for index, strength in enumerate(student.strengths[:5]):
            entry = {
                "content_type": strength.content_type.value,
                "dimension": strength.dimension.value,
                "level": strength.level.value,
                "score": strength.score,
                "confidence": strength.confidence,
            }
            strengths.append(entry)
            facts.append(
                AIProgressFact(
                    id=f"student.strength.{index}",
                    label=f"Assessed strength in {strength.dimension.value}",
                    value=strength.score,
                    unit="score 0-1",
                )
            )
        weaknesses = []
        for index, weakness in enumerate(student.weaknesses[:5]):
            entry = {
                "content_type": weakness.content_type.value,
                "dimension": weakness.dimension.value,
                "score": weakness.score,
                "confidence": weakness.confidence,
            }
            weaknesses.append(entry)
            facts.append(
                AIProgressFact(
                    id=f"student.weakness.{index}",
                    label=f"Assessed area to work on: {weakness.dimension.value}",
                    value=weakness.score,
                    unit="score 0-1",
                )
            )
        stage = student.curriculum.recommended_stage_title
        if stage:
            facts.append(
                AIProgressFact(
                    id="student.recommended_stage",
                    label="Recommended curriculum stage",
                    value=stage,
                )
            )
        return {
            "curriculum": {
                "declared_level": student.curriculum.declared_level.value
                if student.curriculum.declared_level
                else None,
                "recommended_stage_title": stage,
            },
            "mastery": student.mastery.model_dump(mode="json"),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "data_quality": student.data_quality.model_dump(mode="json"),
        }

    def _today_data(self, uid, local_date, facts: list[AIProgressFact]) -> dict[str, object]:  # type: ignore[no-untyped-def]
        plan = self._plans.get(uid, local_date)
        if plan is None:
            facts.append(
                AIProgressFact(id="today.has_plan", label="Today has a study plan", value=False)
            )
            return {"has_plan": False}
        completed = [item for item in plan.items if item.state == DailyPlanItemState.COMPLETED]
        pending = [item for item in plan.items if item.state != DailyPlanItemState.COMPLETED]
        current_focus = pending[0].title if pending else None
        completed_minutes = sum(item.estimated_minutes for item in completed)
        values = [
            AIProgressFact(
                id="today.completed_items",
                label="Today's completed plan items",
                value=len(completed),
                unit="items",
            ),
            AIProgressFact(
                id="today.total_items",
                label="Today's total plan items",
                value=len(plan.items),
                unit="items",
            ),
            AIProgressFact(
                id="today.estimated_completed_minutes",
                label="Today's estimated completed study volume",
                value=completed_minutes,
                unit="estimated minutes",
            ),
        ]
        if current_focus:
            values.append(
                AIProgressFact(
                    id="today.current_focus", label="Today's current focus", value=current_focus
                )
            )
        facts.extend(values)
        return {
            "has_plan": True,
            "completed_items": len(completed),
            "total_items": len(plan.items),
            "estimated_completed_minutes": completed_minutes,
            "estimated_planned_minutes": plan.estimated_minutes,
            "current_focus": current_focus,
        }
