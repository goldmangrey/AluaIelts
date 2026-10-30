from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import ValidationError
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.grammar.content_repository import GrammarContentRepository
from app.modules.learning_events.repository import LearningEventRepository
from app.modules.mastery.models import MasteryContentType, MasteryLevel, MasteryState
from app.modules.mastery.repository import MasteryRepository
from app.modules.mastery.service import MasteryService
from app.modules.progress.engine import ProgressAnalyticsEngine
from app.modules.progress.models import (
    ProgressAggregate,
    ProgressComparison,
    ProgressContentMasteryBreakdown,
    ProgressErrorPattern,
    ProgressMasterySummary,
    ProgressPeriod,
    ProgressSnapshot,
)
from app.modules.progress.repository import ProgressAnalyticsRepository
from app.modules.student_model.service import StudentModelService
from app.modules.users.repository import UserRepository
from app.modules.vocabulary.content_repository import VocabularyContentRepository

SUPPORTED_PERIODS = {7, 30, 90}


class ProgressAnalyticsService:
    def __init__(
        self,
        *,
        events: LearningEventRepository,
        plans: DailyPlanRepository,
        mastery_repository: MasteryRepository,
        mastery_service: MasteryService,
        student_model: StudentModelService,
        users: UserRepository,
        vocabulary: VocabularyContentRepository,
        grammar: GrammarContentRepository,
        engine: ProgressAnalyticsEngine,
        repository: ProgressAnalyticsRepository,
    ) -> None:
        self._events = events
        self._plans = plans
        self._mastery_repository = mastery_repository
        self._mastery_service = mastery_service
        self._student_model = student_model
        self._users = users
        self._vocabulary = vocabulary
        self._grammar = grammar
        self._engine = engine
        self._repository = repository

    def get_snapshot(
        self, uid: str, days: int, timezone_name: str, *, now: datetime | None = None
    ) -> ProgressSnapshot:
        if days not in SUPPORTED_PERIODS:
            raise ValidationError(
                message="Progress period must be 7, 30, or 90 days.",
                code="progress_invalid_period",
            )
        try:
            timezone = ZoneInfo(timezone_name)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValidationError(
                message="A valid IANA timezone is required.", code="progress_invalid_timezone"
            ) from exc
        instant = now or datetime.now(UTC)
        end_date = instant.astimezone(timezone).date()
        requested_start = end_date - timedelta(days=days - 1)
        previous_end = requested_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days - 1)
        profile = self._users.get_by_uid(uid)
        created_date = (
            profile.created_at.astimezone(timezone).date()
            if profile is not None
            else requested_start
        )
        current_start = max(requested_start, created_date)
        effective_previous_start = max(previous_start, created_date)
        query_start = min(current_start, effective_previous_start)
        start_utc = datetime.combine(query_start, time.min, timezone).astimezone(UTC)
        end_utc = datetime.combine(end_date + timedelta(days=1), time.min, timezone).astimezone(UTC)
        all_events = self._events.list_between(uid, start_utc, end_utc)
        all_plans = self._plans.list_between(uid, query_start, end_date)
        current = self._engine.aggregate(
            start_date=current_start,
            end_date=end_date,
            timezone=timezone,
            events=all_events,
            plans=all_plans,
        )
        previous = self._engine.aggregate(
            start_date=effective_previous_start,
            end_date=previous_end,
            timezone=timezone,
            events=all_events,
            plans=all_plans,
        )
        states = self._mastery_repository.list_states(uid)
        student = self._student_model.get_snapshot_from_states(uid, states, profile)
        snapshot = ProgressSnapshot(
            period=ProgressPeriod(
                start_date=current_start,
                end_date=end_date,
                days=days,
                timezone=timezone.key,
                previous_start_date=effective_previous_start,
                previous_end_date=previous_end,
            ),
            summary=current.summary,
            timeline=current.timeline,
            assessment=current.assessment,
            mastery=self._mastery(states),
            consistency=current.consistency,
            recent_errors=self._errors(current.error_tag_counts),
            strengths=student.strengths,
            weaknesses=student.weaknesses,
            curriculum=student.curriculum,
            comparison=self._comparison(current, previous),
            generated_at=datetime.now(UTC),
        )
        self._repository.save(uid, snapshot)
        return snapshot

    def _mastery(self, states: list[MasteryState]) -> ProgressMasterySummary:
        grouped: dict[tuple[MasteryContentType, str], list[MasteryState]] = defaultdict(list)
        for state in states:
            if state.evidence_count > 0 and state.score is not None:
                grouped[(state.content_type, state.content_id)].append(state)
        levels: dict[MasteryContentType, list[MasteryLevel]] = defaultdict(list)
        for (content_type, content_id), content_states in grouped.items():
            summary = self._mastery_service.summarize_content(
                content_type, content_id, content_states
            )
            levels[content_type].append(summary.overall_level)
        return ProgressMasterySummary(
            vocabulary=self._breakdown(
                len(self._vocabulary.dataset.items),
                levels[MasteryContentType.VOCABULARY_ITEM],
            ),
            grammar=self._breakdown(
                len(self._grammar.dataset.lessons),
                levels[MasteryContentType.GRAMMAR_LESSON],
            ),
        )

    @staticmethod
    def _breakdown(total: int, levels: list[MasteryLevel]) -> ProgressContentMasteryBreakdown:
        return ProgressContentMasteryBreakdown(
            total=total,
            assessed=len(levels),
            unassessed=max(0, total - len(levels)),
            developing=levels.count(MasteryLevel.DEVELOPING),
            competent=levels.count(MasteryLevel.COMPETENT),
            strong=levels.count(MasteryLevel.STRONG),
        )

    def _errors(self, counts: dict[str, int]) -> list[ProgressErrorPattern]:
        lookup = {
            error.error_tag: error
            for lesson in self._grammar.dataset.lessons
            for error in lesson.common_errors
        }
        result = []
        for tag, count in sorted(counts.items(), key=lambda value: (-value[1], value[0]))[:5]:
            error = lookup.get(tag)
            result.append(
                ProgressErrorPattern(
                    tag=tag,
                    count=count,
                    display_title=tag.replace("_", " ").title(),
                    explanation=error.explanation_en if error else None,
                )
            )
        return result

    @staticmethod
    def _comparison(current: ProgressAggregate, previous: ProgressAggregate) -> ProgressComparison:
        accuracy_delta = (
            round((current.assessment.accuracy - previous.assessment.accuracy) * 100, 4)
            if current.assessment.accuracy is not None and previous.assessment.accuracy is not None
            else None
        )
        plan_delta = (
            round((current.plan_completion_rate - previous.plan_completion_rate) * 100, 4)
            if current.plan_completion_rate is not None
            and previous.plan_completion_rate is not None
            else None
        )
        return ProgressComparison(
            previous_data_available=(
                previous.summary.active_days > 0
                or previous.summary.plans_generated > 0
                or previous.summary.assessment_attempts > 0
            ),
            active_days_delta=current.summary.active_days - previous.summary.active_days,
            practice_days_delta=current.summary.practice_days - previous.summary.practice_days,
            assessment_attempts_delta=(
                current.summary.assessment_attempts - previous.summary.assessment_attempts
            ),
            completed_items_delta=current.summary.completed_items
            - previous.summary.completed_items,
            estimated_completed_minutes_delta=(
                current.summary.estimated_completed_minutes
                - previous.summary.estimated_completed_minutes
            ),
            accuracy_percentage_points_delta=accuracy_delta,
            plan_completion_percentage_points_delta=plan_delta,
            accuracy_comparison_available=(
                current.assessment.data_quality.value != "insufficient"
                and previous.assessment.data_quality.value != "insufficient"
            ),
        )
