from datetime import datetime
from uuid import uuid4

from sqlalchemy import select

from app.core.exceptions import ExternalServiceError, NotFoundError
from app.db.database import Database
from app.db.models import AIConversationRow, AIMessageRow, AIReportRow
from app.db.serialization import document
from app.modules.ai_progress.models import (
    AIProgressChatMessage,
    AIProgressConversation,
    AIProgressReport,
)


class AIProgressRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save_report(
        self,
        *,
        relationship_id: str,
        partner_uid: str,
        generated_at: datetime,
        report: AIProgressReport,
    ) -> str:
        report_id = str(uuid4())
        try:
            with self._database.session() as session:
                session.add(
                    AIReportRow(
                        report_id=report_id,
                        relationship_id=relationship_id,
                        created_by_partner_id=partner_uid,
                        created_at=generated_at,
                        payload=document(report),
                    )
                )
            return report_id
        except Exception as exc:
            raise self._error() from exc

    def create_conversation(self, value: AIProgressConversation) -> AIProgressConversation:
        try:
            with self._database.session() as session:
                session.add(
                    AIConversationRow(
                        conversation_id=value.conversation_id,
                        relationship_id=value.relationship_id,
                        created_by_partner_id=value.created_by_partner_uid,
                        updated_at=value.updated_at,
                        payload=document(value),
                    )
                )
            return value
        except Exception as exc:
            raise self._error() from exc

    def get_conversation(
        self, relationship_id: str, conversation_id: str
    ) -> AIProgressConversation:
        try:
            with self._database.session() as session:
                row = session.get(AIConversationRow, conversation_id)
                if row is None or row.relationship_id != relationship_id:
                    raise NotFoundError(
                        message="AI progress conversation not found.",
                        code="ai_progress_conversation_not_found",
                    )
                return AIProgressConversation.model_validate(row.payload)
        except NotFoundError:
            raise
        except Exception as exc:
            raise self._error() from exc

    def list_messages(
        self, relationship_id: str, conversation_id: str, limit: int
    ) -> list[AIProgressChatMessage]:
        self.get_conversation(relationship_id, conversation_id)
        try:
            with self._database.session() as session:
                rows = session.scalars(
                    select(AIMessageRow)
                    .where(AIMessageRow.conversation_id == conversation_id)
                    .order_by(AIMessageRow.created_at.desc(), AIMessageRow.message_id.desc())
                    .limit(limit)
                ).all()
                return [AIProgressChatMessage.model_validate(row.payload) for row in reversed(rows)]
        except Exception as exc:
            raise self._error() from exc

    def save_exchange(
        self,
        conversation: AIProgressConversation,
        user_message: AIProgressChatMessage,
        assistant_message: AIProgressChatMessage,
    ) -> None:
        try:
            with self._database.session() as session:
                row = session.get(
                    AIConversationRow, conversation.conversation_id, with_for_update=True
                )
                if row is None or row.relationship_id != conversation.relationship_id:
                    raise ValueError("Conversation does not exist")
                session.add_all(
                    [
                        self._message_row(conversation.conversation_id, user_message),
                        self._message_row(conversation.conversation_id, assistant_message),
                    ]
                )
                updated = conversation.model_copy(
                    update={"updated_at": assistant_message.created_at}
                )
                row.updated_at = assistant_message.created_at
                row.payload = document(updated)
        except Exception as exc:
            raise self._error() from exc

    @staticmethod
    def _message_row(conversation_id: str, value: AIProgressChatMessage) -> AIMessageRow:
        return AIMessageRow(
            message_id=value.message_id,
            conversation_id=conversation_id,
            created_at=value.created_at,
            role=value.role.value,
            content=value.content,
            payload=document(value),
        )

    @staticmethod
    def _error() -> ExternalServiceError:
        return ExternalServiceError(
            message="AI conversation data is temporarily unavailable.",
            code="ai_progress_persistence_error",
        )
