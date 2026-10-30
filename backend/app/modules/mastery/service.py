from collections import Counter
from datetime import UTC, datetime

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.grammar.content_repository import GrammarContentRepository
from app.modules.mastery.engine import MasteryEngine
from app.modules.mastery.models import (
    DIMENSIONS_BY_CONTENT_TYPE,
    MasteryContentType,
    MasteryDimension,
    MasteryEvidence,
    MasteryLevel,
    MasteryState,
    make_state_id,
)
from app.modules.mastery.repository import MasteryRepository
from app.modules.mastery.schemas import (
    ContentMasterySummary,
    ErrorTagCount,
    MasteryDimensionSummary,
)
from app.modules.vocabulary.content_repository import VocabularyContentRepository


class MasteryService:
    def __init__(
        self,
        repository: MasteryRepository,
        engine: MasteryEngine,
        vocabulary: VocabularyContentRepository,
        grammar: GrammarContentRepository,
    ) -> None:
        self._repository = repository
        self._engine = engine
        self._vocabulary = vocabulary
        self._grammar = grammar

    def apply_evidence(self, uid: str, evidence: MasteryEvidence) -> MasteryState:
        """Apply trusted assessment evidence; future Exercise Engine is the caller.

        The future flow is: persist immutable assessment LearningEvent, map its result
        to one or more MasteryEvidence values, then call this method. The transaction
        marker makes replay safe for each event/state pair.
        """
        self._validate_content(evidence.content_type, evidence.content_id)
        self._validate_dimension(evidence.content_type, evidence.dimension)
        applied_at = datetime.now(UTC)
        state_id = make_state_id(evidence.content_type, evidence.content_id, evidence.dimension)
        return self._repository.apply_once(
            uid=uid,
            event_id=evidence.event_id,
            state_id=state_id,
            applied_at=applied_at,
            project=lambda current: self._engine.apply(
                uid=uid,
                evidence=evidence,
                current=current,
                applied_at=applied_at,
            ),
        )

    def get_state(self, uid: str, state_id: str) -> MasteryState:
        state = self._repository.get(uid, state_id)
        if state is None:
            raise NotFoundError(message="Mastery state not found.", code="mastery_state_not_found")
        return state

    def list_states(
        self,
        uid: str,
        *,
        content_type: MasteryContentType | None = None,
        dimension: MasteryDimension | None = None,
        level: MasteryLevel | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MasteryState]:
        states = self._repository.list_states(uid)
        filtered = [
            state
            for state in states
            if (content_type is None or state.content_type == content_type)
            and (dimension is None or state.dimension == dimension)
            and (level is None or state.level == level)
        ]
        filtered.sort(key=lambda state: (state.updated_at, state.state_id), reverse=True)
        return filtered[offset : offset + limit]

    def get_content_summary(
        self, uid: str, content_type: MasteryContentType, content_id: str
    ) -> ContentMasterySummary:
        self._validate_content(content_type, content_id)
        states = [
            state
            for state in self._repository.list_states(uid)
            if state.content_type == content_type and state.content_id == content_id
        ]
        return self.summarize_content(content_type, content_id, states)

    def summarize_content(
        self,
        content_type: MasteryContentType,
        content_id: str,
        states: list[MasteryState],
    ) -> ContentMasterySummary:
        by_dimension = {state.dimension: state for state in states}
        expected = DIMENSIONS_BY_CONTENT_TYPE[content_type]
        dimensions = [
            MasteryDimensionSummary(
                dimension=dimension,
                score=state.score if (state := by_dimension.get(dimension)) else None,
                confidence=state.confidence if state else 0.0,
                level=state.level if state else MasteryLevel.UNASSESSED,
                trend=state.trend if state else "unknown",
                evidence_count=state.evidence_count if state else 0,
                last_evidence_at=state.last_evidence_at if state else None,
            )
            for dimension in expected
        ]
        assessed = [state for state in states if state.score is not None]
        evidence_count = sum(state.evidence_count for state in assessed)
        if assessed:
            confidence_weight = sum(state.confidence for state in assessed)
            overall_score = (
                sum((state.score or 0.0) * state.confidence for state in assessed)
                / confidence_weight
                if confidence_weight > 0
                else sum(state.score or 0.0 for state in assessed) / len(assessed)
            )
            coverage = len({state.dimension for state in assessed}) / len(expected)
            overall_confidence = (
                sum(state.confidence for state in assessed) / len(assessed)
            ) * coverage
            overall_level = self._engine.level_for(
                overall_score, overall_confidence, evidence_count
            )
            last_evidence_at = max(state.last_evidence_at for state in assessed)
        else:
            overall_score = None
            overall_confidence = 0.0
            overall_level = MasteryLevel.UNASSESSED
            last_evidence_at = None
        tags: Counter[str] = Counter()
        for state in assessed:
            tags.update(state.error_tag_counts)
        return ContentMasterySummary(
            content_type=content_type,
            content_id=content_id,
            overall_score=overall_score,
            overall_confidence=overall_confidence,
            overall_level=overall_level,
            dimensions=dimensions,
            evidence_count=evidence_count,
            last_evidence_at=last_evidence_at,
            top_error_tags=[
                ErrorTagCount(tag=tag, count=count) for tag, count in tags.most_common(5)
            ],
        )

    def _validate_content(self, content_type: MasteryContentType, content_id: str) -> None:
        try:
            if content_type == MasteryContentType.VOCABULARY_ITEM:
                self._vocabulary.get_item(content_id)
            else:
                self._grammar.get_lesson(content_id)
        except NotFoundError as exc:
            raise NotFoundError(
                message="Mastery content not found.", code="mastery_content_not_found"
            ) from exc

    @staticmethod
    def _validate_dimension(content_type: MasteryContentType, dimension: MasteryDimension) -> None:
        if dimension not in DIMENSIONS_BY_CONTENT_TYPE[content_type]:
            raise ValidationError(
                message="Dimension is invalid for this content type.",
                code="mastery_invalid_dimension",
            )
