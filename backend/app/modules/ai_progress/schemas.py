from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.ai_progress.models import (
    AIProgressChatAnswer,
    AIProgressChatMessage,
    AIProgressConversationStatus,
    AIProgressLanguage,
    AIProgressReport,
)


class AIProgressPeriodRequest(BaseModel):
    days: int = 30
    timezone: str = Field(default="UTC", min_length=1, max_length=100)
    language: AIProgressLanguage = AIProgressLanguage.EN


class AIProgressMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class AIProgressReportResponse(BaseModel):
    report: AIProgressReport
    period_days: int
    timezone: str
    language: AIProgressLanguage
    generated_at: datetime


class AIProgressConversationPublic(BaseModel):
    conversation_id: str
    period_days: int
    timezone: str
    language: AIProgressLanguage
    status: AIProgressConversationStatus
    created_at: datetime
    updated_at: datetime


class AIProgressConversationResponse(BaseModel):
    conversation: AIProgressConversationPublic
    messages: list[AIProgressChatMessage]


class AIProgressChatResponse(BaseModel):
    message: AIProgressChatMessage
    answer: AIProgressChatAnswer
