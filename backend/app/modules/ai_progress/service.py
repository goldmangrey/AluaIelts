from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import Settings
from app.core.exceptions import (
    ExternalServiceError,
    ForbiddenError,
    UnauthorizedError,
    ValidationError,
)
from app.modules.ai_progress.context_builder import AIProgressContextBuilder
from app.modules.ai_progress.models import (
    AIProgressChatMessage,
    AIProgressChatRole,
    AIProgressConversation,
    AIProgressLanguage,
    AIProgressReport,
)
from app.modules.ai_progress.openai_provider import OpenAIProgressProvider
from app.modules.ai_progress.prompts import build_chat_prompt, build_report_prompt
from app.modules.ai_progress.repository import AIProgressRepository
from app.modules.ai_progress.schemas import (
    AIProgressChatResponse,
    AIProgressConversationPublic,
    AIProgressConversationResponse,
    AIProgressReportResponse,
)
from app.modules.ai_progress.validator import (
    dedupe_fact_references,
    validate_fact_references,
)
from app.modules.partner.models import PartnerRelationship
from app.modules.partner.repository import PartnerRepository
from app.modules.progress.service import SUPPORTED_PERIODS


class AIProgressService:
    def __init__(
        self,
        *,
        relationships: PartnerRepository,
        repository: AIProgressRepository,
        context_builder: AIProgressContextBuilder,
        provider: OpenAIProgressProvider,
        settings: Settings,
    ) -> None:
        self._relationships = relationships
        self._repository = repository
        self._context_builder = context_builder
        self._provider = provider
        self._settings = settings

    def generate_report(
        self, partner_uid: str, days: int, timezone: str, language: AIProgressLanguage
    ) -> AIProgressReportResponse:
        relationship = self._authorize(partner_uid)
        context = self._context_builder.build(relationship, days, timezone)
        allowed = {fact.id for fact in context.facts}
        report = self._provider.report(build_report_prompt(context, language))
        if not self._valid_report(report, allowed):
            report = self._provider.report(build_report_prompt(context, language, sorted(allowed)))
            if not self._valid_report(report, allowed):
                raise ExternalServiceError(
                    message="AI analysis returned unsupported evidence references.",
                    code="ai_progress_invalid_response",
                )
        generated_at = datetime.now(UTC)
        self._repository.save_report(
            relationship_id=relationship.relationship_id,
            partner_uid=partner_uid,
            generated_at=generated_at,
            report=report,
        )
        return AIProgressReportResponse(
            report=report,
            period_days=days,
            timezone=timezone,
            language=language,
            generated_at=generated_at,
        )

    def create_conversation(
        self, partner_uid: str, days: int, timezone: str, language: AIProgressLanguage
    ) -> AIProgressConversationResponse:
        relationship = self._authorize(partner_uid)
        self._validate_period(days, timezone)
        now = datetime.now(UTC)
        conversation = AIProgressConversation(
            conversation_id=str(uuid4()),
            relationship_id=relationship.relationship_id,
            created_by_partner_uid=partner_uid,
            period_days=days,
            timezone=timezone,
            language=language,
            created_at=now,
            updated_at=now,
        )
        self._repository.create_conversation(conversation)
        return AIProgressConversationResponse(
            conversation=self._public_conversation(conversation), messages=[]
        )

    def get_conversation(
        self, partner_uid: str, conversation_id: str
    ) -> AIProgressConversationResponse:
        relationship = self._authorize(partner_uid)
        conversation = self._repository.get_conversation(
            relationship.relationship_id, conversation_id
        )
        self._validate_ownership(conversation, relationship, partner_uid)
        messages = self._repository.list_messages(
            relationship.relationship_id,
            conversation_id,
            self._settings.openai_progress_chat_history_limit,
        )
        return AIProgressConversationResponse(
            conversation=self._public_conversation(conversation), messages=messages
        )

    def send_message(
        self, partner_uid: str, conversation_id: str, question: str
    ) -> AIProgressChatResponse:
        relationship = self._authorize(partner_uid)
        conversation = self._repository.get_conversation(
            relationship.relationship_id, conversation_id
        )
        self._validate_ownership(conversation, relationship, partner_uid)
        history = self._repository.list_messages(
            relationship.relationship_id,
            conversation_id,
            self._settings.openai_progress_chat_history_limit,
        )
        context = self._context_builder.build(
            relationship, conversation.period_days, conversation.timezone
        )
        allowed = {fact.id for fact in context.facts}
        answer = self._provider.chat(
            build_chat_prompt(context, conversation.language, history, question)
        )
        if not validate_fact_references(answer.supporting_fact_ids, allowed):
            answer = self._provider.chat(
                build_chat_prompt(
                    context,
                    conversation.language,
                    history,
                    question,
                    sorted(allowed),
                )
            )
            if not validate_fact_references(answer.supporting_fact_ids, allowed):
                raise ExternalServiceError(
                    message="AI analysis returned unsupported evidence references.",
                    code="ai_progress_invalid_response",
                )
        now = datetime.now(UTC)
        user_message = AIProgressChatMessage(
            message_id=str(uuid4()),
            role=AIProgressChatRole.USER,
            content=question,
            created_at=now,
        )
        assistant_message = AIProgressChatMessage(
            message_id=str(uuid4()),
            role=AIProgressChatRole.ASSISTANT,
            content=answer.answer,
            created_at=datetime.now(UTC),
            supporting_fact_ids=dedupe_fact_references(answer.supporting_fact_ids),
        )
        self._repository.save_exchange(conversation, user_message, assistant_message)
        return AIProgressChatResponse(message=assistant_message, answer=answer)

    def _authorize(self, partner_uid: str) -> PartnerRelationship:
        if not self._settings.openai_progress_analysis_enabled:
            raise ExternalServiceError(
                message="AI progress analysis is unavailable.",
                code="ai_progress_unavailable",
            )
        relationship = self._relationships.get_active_by_partner(partner_uid)
        if relationship is None or relationship.partner_uid != partner_uid:
            raise UnauthorizedError(
                message="Partner AI analysis is not authorized.",
                code="partner_not_authorized",
            )
        if not relationship.sharing_settings.allow_ai_progress_analysis:
            raise ForbiddenError(
                message="AI progress analysis is not enabled by the learner.",
                code="partner_ai_analysis_not_allowed",
            )
        return relationship

    @staticmethod
    def _validate_period(days: int, timezone: str) -> None:
        if days not in SUPPORTED_PERIODS:
            raise ValidationError(
                message="Analysis period must be 7, 30, or 90 days.",
                code="ai_progress_invalid_period",
            )
        try:
            ZoneInfo(timezone)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValidationError(
                message="A valid IANA timezone is required.",
                code="ai_progress_invalid_timezone",
            ) from exc

    @staticmethod
    def _validate_ownership(
        conversation: AIProgressConversation,
        relationship: PartnerRelationship,
        partner_uid: str,
    ) -> None:
        if (
            conversation.relationship_id != relationship.relationship_id
            or conversation.created_by_partner_uid != partner_uid
        ):
            raise UnauthorizedError(
                message="AI conversation is not authorized.",
                code="partner_not_authorized",
            )

    @staticmethod
    def _valid_report(report: AIProgressReport, allowed: set[str]) -> bool:
        ids = [
            fact_id
            for item in [*report.highlights, *report.areas_to_work_on]
            for fact_id in item.supporting_fact_ids
        ]
        ids.extend(
            fact_id
            for recommendation in report.recommendations
            for fact_id in recommendation.supporting_fact_ids
        )
        return validate_fact_references(ids, allowed)

    @staticmethod
    def _public_conversation(
        conversation: AIProgressConversation,
    ) -> AIProgressConversationPublic:
        return AIProgressConversationPublic(
            conversation_id=conversation.conversation_id,
            period_days=conversation.period_days,
            timezone=conversation.timezone,
            language=conversation.language,
            status=conversation.status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
