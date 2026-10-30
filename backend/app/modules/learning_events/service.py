from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.curriculum.content_repository import CurriculumContentRepository
from app.modules.grammar.content_repository import GrammarContentRepository
from app.modules.learning_events.models import (
    EVENT_CONTENT_TYPES,
    AssessmentEventPayload,
    LearningEvent,
    LearningEventCategory,
    LearningEventSource,
    LearningEventType,
)
from app.modules.learning_events.repository import LearningEventRepository
from app.modules.learning_events.schemas import CreateLearningEventRequest
from app.modules.vocabulary.content_repository import VocabularyContentRepository

CLIENT_EVENT_TYPES = {
    LearningEventType.GRAMMAR_LESSON_OPENED,
    LearningEventType.VOCABULARY_TRACK_OPENED,
    LearningEventType.VOCABULARY_ITEM_OPENED,
}


class LearningEventService:
    def __init__(
        self,
        repository: LearningEventRepository,
        curriculum: CurriculumContentRepository,
        grammar: GrammarContentRepository,
        vocabulary: VocabularyContentRepository,
    ) -> None:
        self._repository = repository
        self._curriculum = curriculum
        self._grammar = grammar
        self._vocabulary = vocabulary

    def record_client_event(self, uid: str, request: CreateLearningEventRequest) -> LearningEvent:
        if request.event_type not in CLIENT_EVENT_TYPES:
            raise ValidationError(
                message="This learning event type cannot be created by a client.",
                code="learning_event_invalid_type",
            )
        if request.client_occurred_at and request.client_occurred_at > datetime.now(
            UTC
        ) + timedelta(days=30):
            raise ValidationError(
                message="The client event time is too far in the future.",
                code="learning_event_invalid_time",
            )
        event = LearningEvent(
            event_id=request.event_id,
            schema_version=request.schema_version,
            user_id=uid,
            event_type=request.event_type,
            category=LearningEventCategory.ENGAGEMENT,
            source=LearningEventSource.IOS_APP,
            content_type=EVENT_CONTENT_TYPES[request.event_type],
            content_id=request.content_id,
            curriculum_node_id=request.curriculum_node_id,
            client_occurred_at=request.client_occurred_at,
            server_received_at=datetime.now(UTC),
            timezone=request.timezone,
            session_id=request.session_id,
        )
        return self._validate_and_store(event)

    def record_curriculum_node_started(self, uid: str, node_id: str) -> LearningEvent:
        event_id = uuid5(NAMESPACE_URL, f"alua:{uid}:curriculum-node-started:{node_id}")
        event = LearningEvent(
            event_id=event_id,
            user_id=uid,
            event_type=LearningEventType.CURRICULUM_NODE_STARTED,
            category=LearningEventCategory.ENGAGEMENT,
            source=LearningEventSource.BACKEND,
            content_type=EVENT_CONTENT_TYPES[LearningEventType.CURRICULUM_NODE_STARTED],
            content_id=node_id,
            curriculum_node_id=node_id,
            server_received_at=datetime.now(UTC),
        )
        return self._validate_and_store(event)

    def record_exercise_answered(
        self,
        *,
        uid: str,
        event_id: UUID,
        content_type: str,
        content_id: str,
        curriculum_node_id: str | None,
        occurred_at: datetime | None,
        assessment: AssessmentEventPayload,
    ) -> LearningEvent:
        event = LearningEvent(
            event_id=event_id,
            schema_version=2,
            user_id=uid,
            event_type=LearningEventType.EXERCISE_ANSWERED,
            category=LearningEventCategory.ASSESSMENT,
            source=LearningEventSource.BACKEND,
            content_type=content_type,
            content_id=content_id,
            curriculum_node_id=curriculum_node_id,
            client_occurred_at=occurred_at,
            server_received_at=datetime.now(UTC),
            assessment=assessment,
        )
        return self._validate_and_store(event)

    def get_event(self, uid: str, event_id: UUID) -> LearningEvent:
        event = self._repository.get_by_id(uid, event_id)
        if event is None:
            raise NotFoundError(
                message="Learning event not found.", code="learning_event_not_found"
            )
        return event

    def list_recent(
        self,
        uid: str,
        *,
        limit: int,
        before_server_received_at: datetime | None,
    ) -> list[LearningEvent]:
        if before_server_received_at and before_server_received_at.tzinfo is None:
            raise ValidationError(
                message="The events cursor must include a timezone.",
                code="learning_event_invalid_cursor",
            )
        return self._repository.list_recent(
            uid,
            limit=limit,
            before_server_received_at=before_server_received_at,
        )

    def _validate_and_store(self, event: LearningEvent) -> LearningEvent:
        self._validate_content_reference(event)
        self._validate_curriculum_context(event)
        existing = self._repository.get_by_id(event.user_id, event.event_id)
        if existing is not None:
            return self._resolve_idempotency(existing, event)
        persisted = self._repository.create(event.user_id, event)
        return self._resolve_idempotency(persisted, event)

    def _validate_content_reference(self, event: LearningEvent) -> None:
        try:
            if event.event_type == LearningEventType.CURRICULUM_NODE_STARTED:
                self._curriculum.get_node(event.content_id)
            elif event.event_type == LearningEventType.GRAMMAR_LESSON_OPENED:
                self._grammar.get_lesson(event.content_id)
            elif event.event_type == LearningEventType.VOCABULARY_TRACK_OPENED:
                self._vocabulary.get_track(event.content_id)
            elif event.event_type == LearningEventType.VOCABULARY_ITEM_OPENED:
                self._vocabulary.get_item(event.content_id)
            elif event.content_type.value == "grammar_lesson":
                self._grammar.get_lesson(event.content_id)
            else:
                self._vocabulary.get_item(event.content_id)
        except NotFoundError as exc:
            raise ValidationError(
                message="The referenced learning content does not exist.",
                code="learning_event_invalid_content_reference",
            ) from exc

    def _validate_curriculum_context(self, event: LearningEvent) -> None:
        if event.curriculum_node_id is None:
            return
        try:
            node = self._curriculum.get_node(event.curriculum_node_id)
            if event.event_type == LearningEventType.EXERCISE_ANSWERED:
                return
            if event.event_type == LearningEventType.CURRICULUM_NODE_STARTED:
                valid = node.id == event.content_id
            elif event.event_type == LearningEventType.GRAMMAR_LESSON_OPENED:
                valid = event.content_id in node.content_refs
            elif event.event_type == LearningEventType.VOCABULARY_TRACK_OPENED:
                valid = event.content_id in node.content_refs
            else:
                item = self._vocabulary.get_item(event.content_id)
                valid = any(reference in item.track_ids for reference in node.content_refs)
            if not valid:
                raise ValueError("Content is not mapped to the curriculum context.")
        except (NotFoundError, ValueError) as exc:
            raise ValidationError(
                message="The curriculum context does not match the learning content.",
                code="learning_event_invalid_curriculum_context",
            ) from exc

    @staticmethod
    def _resolve_idempotency(existing: LearningEvent, requested: LearningEvent) -> LearningEvent:
        if existing.idempotency_payload() == requested.idempotency_payload():
            return existing
        raise ConflictError(
            message="This learning event ID already exists with different data.",
            code="learning_event_id_conflict",
        )
