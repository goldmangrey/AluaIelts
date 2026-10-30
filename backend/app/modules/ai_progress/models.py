from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AIProgressLanguage(StrEnum):
    EN = "en"
    RU = "ru"


class AIProgressFact(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    value: str | int | float | bool
    unit: str | None = Field(default=None, max_length=40)


class AIProgressContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    period: dict[str, object]
    learner: dict[str, object]
    today: dict[str, object] | None = None
    progress: dict[str, object] | None = None
    learning_profile: dict[str, object] | None = None
    recent_errors: list[dict[str, object]] | None = None
    data_quality: dict[str, object]
    facts: tuple[AIProgressFact, ...]
    generated_at: datetime


class AIProgressInsightSeverity(StrEnum):
    INFO = "info"
    ATTENTION = "attention"


class AIProgressInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    statement: str = Field(min_length=1, max_length=700)
    supporting_fact_ids: list[str] = Field(default_factory=list, max_length=12)
    severity: AIProgressInsightSeverity = AIProgressInsightSeverity.INFO


class AIProgressRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    recommendation: str = Field(min_length=1, max_length=700)
    reason: str = Field(min_length=1, max_length=700)
    supporting_fact_ids: list[str] = Field(default_factory=list, max_length=12)


class AIProgressDataLimitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(min_length=1, max_length=500)


class AIProgressReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    headline: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=1500)
    highlights: list[AIProgressInsight] = Field(min_length=1, max_length=6)
    areas_to_work_on: list[AIProgressInsight] = Field(default_factory=list, max_length=6)
    recommendations: list[AIProgressRecommendation] = Field(min_length=1, max_length=5)
    data_limitations: list[AIProgressDataLimitation] = Field(min_length=1, max_length=5)


class AIProgressChatAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1, max_length=2500)
    supporting_fact_ids: list[str] = Field(default_factory=list, max_length=16)
    limitations: list[str] = Field(default_factory=list, max_length=5)
    suggested_followups: list[str] = Field(default_factory=list, max_length=3)


class AIProgressConversationStatus(StrEnum):
    ACTIVE = "active"


class AIProgressConversation(BaseModel):
    model_config = ConfigDict(frozen=True)
    conversation_id: str
    relationship_id: str
    created_by_partner_uid: str
    period_days: int
    timezone: str
    language: AIProgressLanguage
    status: AIProgressConversationStatus = AIProgressConversationStatus.ACTIVE
    created_at: datetime
    updated_at: datetime


class AIProgressChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class AIProgressChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    message_id: str
    role: AIProgressChatRole
    content: str
    created_at: datetime
    supporting_fact_ids: tuple[str, ...] = ()
