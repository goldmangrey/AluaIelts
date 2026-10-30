from collections import Counter
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from app.modules.daily_plan.models import DailyPlan, DailyPlanItemState
from app.modules.learning_events.models import (
    LearningContentType,
    LearningEvent,
    LearningEventCategory,
    LearningEventType,
)
from app.modules.mastery.models import MasteryDimension
from app.modules.progress.models import (
    ProgressAggregate,
    ProgressAssessmentSummary,
    ProgressConsistency,
    ProgressDailyPoint,
    ProgressDataQuality,
    ProgressDimensionAssessment,
    ProgressDomainAssessment,
    ProgressSummary,
)


class ProgressAnalyticsEngine:
    """Pure aggregation over bounded trusted events and daily-plan snapshots."""

    def aggregate(
        self,
        *,
        start_date: date,
        end_date: date,
        timezone: ZoneInfo,
        events: list[LearningEvent],
        plans: list[DailyPlan],
    ) -> ProgressAggregate:
        dates = self._dates(start_date, end_date)
        event_days: dict[date, list[LearningEvent]] = {value: [] for value in dates}
        for event in events:
            local_date = event.server_received_at.astimezone(timezone).date()
            if local_date in event_days and event.category in {
                LearningEventCategory.ENGAGEMENT,
                LearningEventCategory.ASSESSMENT,
            }:
                event_days[local_date].append(event)
        plans_by_date = {
            plan.local_date: plan for plan in plans if start_date <= plan.local_date <= end_date
        }
        timeline = [
            self._daily_point(day, event_days[day], plans_by_date.get(day)) for day in dates
        ]
        assessments = [
            event
            for event in events
            if event.event_type == LearningEventType.EXERCISE_ANSWERED
            and event.assessment is not None
            and start_date <= event.server_received_at.astimezone(timezone).date() <= end_date
        ]
        assessment = self._assessment(assessments)
        period_plans = list(plans_by_date.values())
        planned_items = sum(len(plan.items) for plan in period_plans)
        completed_items = sum(
            item.state == DailyPlanItemState.COMPLETED
            for plan in period_plans
            for item in plan.items
        )
        pending_items = sum(
            item.state == DailyPlanItemState.PENDING for plan in period_plans for item in plan.items
        )
        completed_plan_days = sum(
            bool(plan.items)
            and all(item.state == DailyPlanItemState.COMPLETED for item in plan.items)
            for plan in period_plans
        )
        plan_completion_rate = completed_items / planned_items if planned_items else None
        active_days = sum(point.active for point in timeline)
        practice_days = sum(point.practice_active for point in timeline)
        summary = ProgressSummary(
            eligible_days=len(dates),
            active_days=active_days,
            practice_days=practice_days,
            plans_generated=len(period_plans),
            planned_items=planned_items,
            completed_items=completed_items,
            pending_items=pending_items,
            fully_completed_plan_days=completed_plan_days,
            estimated_planned_minutes=sum(
                item.estimated_minutes for plan in period_plans for item in plan.items
            ),
            estimated_completed_minutes=sum(
                item.estimated_minutes
                for plan in period_plans
                for item in plan.items
                if item.state == DailyPlanItemState.COMPLETED
            ),
            assessment_attempts=assessment.attempts,
            correct_attempts=assessment.correct,
            plan_completion_rate=plan_completion_rate,
        )
        error_tags: Counter[str] = Counter()
        for event in assessments:
            if event.assessment and event.assessment.outcome < 0.75:
                error_tags.update(event.assessment.error_tags)
        return ProgressAggregate(
            summary=summary,
            timeline=timeline,
            assessment=assessment,
            consistency=ProgressConsistency(
                eligible_days=len(dates),
                active_days=active_days,
                practice_days=practice_days,
                fully_completed_plan_days=completed_plan_days,
                activity_consistency=active_days / len(dates) if dates else None,
            ),
            plan_completion_rate=plan_completion_rate,
            error_tag_counts=dict(error_tags),
        )

    @staticmethod
    def _dates(start: date, end: date) -> list[date]:
        if start > end:
            return []
        return [start + timedelta(days=index) for index in range((end - start).days + 1)]

    def _daily_point(
        self, day: date, events: list[LearningEvent], plan: DailyPlan | None
    ) -> ProgressDailyPoint:
        assessments = [
            event
            for event in events
            if event.event_type == LearningEventType.EXERCISE_ANSWERED
            and event.assessment is not None
        ]
        correct = sum(
            bool(event.assessment and event.assessment.is_correct) for event in assessments
        )
        grammar = [
            event
            for event in assessments
            if event.content_type == LearningContentType.GRAMMAR_LESSON
        ]
        vocabulary = [
            event
            for event in assessments
            if event.content_type == LearningContentType.VOCABULARY_ITEM
        ]
        items = plan.items if plan else ()
        completed = [item for item in items if item.state == DailyPlanItemState.COMPLETED]
        return ProgressDailyPoint(
            date=day,
            active=bool(events),
            practice_active=bool(assessments),
            learning_events=len(events),
            assessment_attempts=len(assessments),
            correct_attempts=correct,
            incorrect_attempts=len(assessments) - correct,
            grammar_attempts=len(grammar),
            grammar_correct=sum(
                bool(event.assessment and event.assessment.is_correct) for event in grammar
            ),
            vocabulary_attempts=len(vocabulary),
            vocabulary_correct=sum(
                bool(event.assessment and event.assessment.is_correct) for event in vocabulary
            ),
            planned_items=len(items),
            completed_items=len(completed),
            estimated_planned_minutes=sum(item.estimated_minutes for item in items),
            estimated_completed_minutes=sum(item.estimated_minutes for item in completed),
            accuracy=correct / len(assessments) if assessments else None,
        )

    def _assessment(self, events: list[LearningEvent]) -> ProgressAssessmentSummary:
        correct = sum(bool(event.assessment and event.assessment.is_correct) for event in events)
        grammar = [
            event for event in events if event.content_type == LearningContentType.GRAMMAR_LESSON
        ]
        vocabulary = [
            event for event in events if event.content_type == LearningContentType.VOCABULARY_ITEM
        ]
        response_times = [
            event.assessment.response_time_ms
            for event in events
            if event.assessment and event.assessment.response_time_ms is not None
        ]
        return ProgressAssessmentSummary(
            attempts=len(events),
            correct=correct,
            incorrect=len(events) - correct,
            accuracy=correct / len(events) if events else None,
            data_quality=self.quality(len(events)),
            average_response_time_ms=(
                round(sum(response_times) / len(response_times)) if response_times else None
            ),
            grammar=self._domain(grammar),
            vocabulary=self._domain(vocabulary),
            dimensions=[self._dimension(dimension, events) for dimension in MasteryDimension],
        )

    @staticmethod
    def quality(attempts: int) -> ProgressDataQuality:
        if attempts < 5:
            return ProgressDataQuality.INSUFFICIENT
        if attempts < 20:
            return ProgressDataQuality.PARTIAL
        return ProgressDataQuality.MEANINGFUL

    @staticmethod
    def _domain(events: list[LearningEvent]) -> ProgressDomainAssessment:
        correct = sum(bool(event.assessment and event.assessment.is_correct) for event in events)
        return ProgressDomainAssessment(
            attempts=len(events),
            correct=correct,
            incorrect=len(events) - correct,
            accuracy=correct / len(events) if events else None,
            distinct_content_practiced=len({event.content_id for event in events}),
        )

    @staticmethod
    def _dimension(
        dimension: MasteryDimension, events: list[LearningEvent]
    ) -> ProgressDimensionAssessment:
        matching = [
            event
            for event in events
            if event.assessment and event.assessment.dimension == dimension.value
        ]
        correct = sum(bool(event.assessment and event.assessment.is_correct) for event in matching)
        return ProgressDimensionAssessment(
            dimension=dimension,
            attempts=len(matching),
            correct=correct,
            accuracy=correct / len(matching) if matching else None,
        )
