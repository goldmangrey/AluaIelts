from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.modules.mastery.models import MasteryDimension
from app.modules.student_model.models import (
    StudentModelCurriculum,
    StudentModelStrength,
    StudentModelWeakness,
)


class ProgressDataQuality(StrEnum):
    INSUFFICIENT = "insufficient"
    PARTIAL = "partial"
    MEANINGFUL = "meaningful"


class ProgressPeriod(BaseModel):
    start_date: date
    end_date: date
    days: int
    timezone: str
    previous_start_date: date
    previous_end_date: date


class ProgressSummary(BaseModel):
    eligible_days: int
    active_days: int
    practice_days: int
    plans_generated: int
    planned_items: int
    completed_items: int
    pending_items: int
    fully_completed_plan_days: int
    estimated_planned_minutes: int
    estimated_completed_minutes: int
    assessment_attempts: int
    correct_attempts: int
    plan_completion_rate: float | None


class ProgressDomainAssessment(BaseModel):
    attempts: int
    correct: int
    incorrect: int
    accuracy: float | None
    distinct_content_practiced: int


class ProgressDimensionAssessment(BaseModel):
    dimension: MasteryDimension
    attempts: int
    correct: int
    accuracy: float | None


class ProgressAssessmentSummary(BaseModel):
    attempts: int
    correct: int
    incorrect: int
    accuracy: float | None
    data_quality: ProgressDataQuality
    average_response_time_ms: int | None
    grammar: ProgressDomainAssessment
    vocabulary: ProgressDomainAssessment
    dimensions: list[ProgressDimensionAssessment]


class ProgressDailyPoint(BaseModel):
    date: date
    active: bool
    practice_active: bool
    learning_events: int
    assessment_attempts: int
    correct_attempts: int
    incorrect_attempts: int
    grammar_attempts: int
    grammar_correct: int
    vocabulary_attempts: int
    vocabulary_correct: int
    planned_items: int
    completed_items: int
    estimated_planned_minutes: int
    estimated_completed_minutes: int
    accuracy: float | None


class ProgressContentMasteryBreakdown(BaseModel):
    total: int
    assessed: int
    unassessed: int
    developing: int
    competent: int
    strong: int


class ProgressMasterySummary(BaseModel):
    vocabulary: ProgressContentMasteryBreakdown
    grammar: ProgressContentMasteryBreakdown


class ProgressConsistency(BaseModel):
    eligible_days: int
    active_days: int
    practice_days: int
    fully_completed_plan_days: int
    activity_consistency: float | None


class ProgressErrorPattern(BaseModel):
    tag: str
    count: int
    display_title: str
    explanation: str | None = None


class ProgressComparison(BaseModel):
    previous_data_available: bool
    active_days_delta: int
    practice_days_delta: int
    assessment_attempts_delta: int
    completed_items_delta: int
    estimated_completed_minutes_delta: int
    accuracy_percentage_points_delta: float | None
    plan_completion_percentage_points_delta: float | None
    accuracy_comparison_available: bool


class ProgressSnapshot(BaseModel):
    period: ProgressPeriod
    summary: ProgressSummary
    timeline: list[ProgressDailyPoint]
    assessment: ProgressAssessmentSummary
    mastery: ProgressMasterySummary
    consistency: ProgressConsistency
    recent_errors: list[ProgressErrorPattern]
    strengths: list[StudentModelStrength]
    weaknesses: list[StudentModelWeakness]
    curriculum: StudentModelCurriculum
    comparison: ProgressComparison
    generated_at: datetime


class ProgressAggregate(BaseModel):
    summary: ProgressSummary
    timeline: list[ProgressDailyPoint]
    assessment: ProgressAssessmentSummary
    consistency: ProgressConsistency
    plan_completion_rate: float | None = Field(default=None, ge=0, le=1)
    error_tag_counts: dict[str, int]
