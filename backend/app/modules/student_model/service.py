from collections import Counter
from datetime import UTC, datetime

from app.core.exceptions import ExternalServiceError
from app.modules.curriculum.content_repository import CurriculumContentRepository
from app.modules.curriculum.user_state_repository import UserCurriculumRepository
from app.modules.mastery.engine import MasteryEngine
from app.modules.mastery.models import MasteryContentType, MasteryLevel, MasteryState
from app.modules.mastery.repository import MasteryRepository
from app.modules.student_model.models import (
    CoverageStatus,
    StudentModelCurriculum,
    StudentModelDataQuality,
    StudentModelErrorTag,
    StudentModelMasteryOverview,
    StudentModelSnapshot,
    StudentModelStrength,
    StudentModelWeakness,
)
from app.modules.users.models import UserProfile
from app.modules.users.repository import UserRepository


class StudentModelService:
    def __init__(
        self,
        mastery: MasteryRepository,
        users: UserRepository,
        curriculum_states: UserCurriculumRepository,
        curriculum_content: CurriculumContentRepository,
    ) -> None:
        self._mastery = mastery
        self._users = users
        self._curriculum_states = curriculum_states
        self._curriculum_content = curriculum_content

    def get_snapshot(self, uid: str) -> StudentModelSnapshot:
        try:
            states = self._mastery.list_states(uid)
            profile = self._users.get_by_uid(uid)
            return self.get_snapshot_from_states(uid, states, profile)
        except ExternalServiceError as exc:
            raise ExternalServiceError(
                message="The student model is temporarily unavailable.",
                code="student_model_unavailable",
            ) from exc

    def get_snapshot_from_states(
        self, uid: str, states: list[MasteryState], profile: UserProfile | None
    ) -> StudentModelSnapshot:
        try:
            evidence_count = self._mastery.count_distinct_applied_events(uid)
            curriculum_state = self._curriculum_states.get(uid)
            vocabulary_ids = {
                state.content_id
                for state in states
                if state.content_type == MasteryContentType.VOCABULARY_ITEM
            }
            grammar_ids = {
                state.content_id
                for state in states
                if state.content_type == MasteryContentType.GRAMMAR_LESSON
            }
            return StudentModelSnapshot(
                user_id=uid,
                generated_at=datetime.now(UTC),
                curriculum=self._curriculum(profile, curriculum_state),
                mastery=StudentModelMasteryOverview(
                    assessed_skill_count=len(states),
                    vocabulary_assessed_item_count=len(vocabulary_ids),
                    grammar_assessed_lesson_count=len(grammar_ids),
                    vocabulary_level=self._aggregate_level(
                        states, MasteryContentType.VOCABULARY_ITEM
                    ),
                    grammar_level=self._aggregate_level(states, MasteryContentType.GRAMMAR_LESSON),
                ),
                strengths=self._strengths(states),
                weaknesses=self._weaknesses(states),
                recent_error_tags=self._error_tags(states),
                data_quality=StudentModelDataQuality(
                    assessment_evidence_count=evidence_count,
                    assessed_vocabulary_items=len(vocabulary_ids),
                    assessed_grammar_lessons=len(grammar_ids),
                    coverage_status=self._coverage(evidence_count),
                ),
            )
        except ExternalServiceError as exc:
            raise ExternalServiceError(
                message="The student model is temporarily unavailable.",
                code="student_model_unavailable",
            ) from exc

    def _curriculum(self, profile, state) -> StudentModelCurriculum:  # type: ignore[no-untyped-def]
        stage_id = state.recommended_stage_id if state else None
        stage_title = self._curriculum_content.get_stage(stage_id).title if stage_id else None
        return StudentModelCurriculum(
            declared_level=profile.current_level if profile else None,
            recommended_stage_id=stage_id,
            recommended_stage_title=stage_title,
            active_node_id=state.active_node_id if state else None,
        )

    @staticmethod
    def _aggregate_level(
        states: list[MasteryState], content_type: MasteryContentType
    ) -> MasteryLevel:
        candidates = [
            state
            for state in states
            if state.content_type == content_type and state.score is not None
        ]
        if not candidates:
            return MasteryLevel.UNASSESSED
        confidence = sum(state.confidence for state in candidates) / len(candidates)
        score = sum((state.score or 0.0) * state.confidence for state in candidates)
        weight = sum(state.confidence for state in candidates)
        aggregate_score = score / weight if weight else 0.0
        return MasteryEngine.level_for(
            aggregate_score,
            confidence,
            sum(state.evidence_count for state in candidates),
        )

    @staticmethod
    def _strengths(states: list[MasteryState]) -> list[StudentModelStrength]:
        candidates = [
            state
            for state in states
            if state.score is not None
            and state.score >= 0.80
            and state.confidence >= 0.50
            and state.evidence_count >= 3
        ]
        candidates.sort(key=lambda state: (state.score or 0.0, state.confidence), reverse=True)
        return [
            StudentModelStrength(
                content_type=state.content_type,
                content_id=state.content_id,
                dimension=state.dimension,
                level=state.level,
                score=state.score or 0.0,
                confidence=state.confidence,
            )
            for state in candidates[:5]
        ]

    @staticmethod
    def _weaknesses(states: list[MasteryState]) -> list[StudentModelWeakness]:
        candidates = [
            state
            for state in states
            if state.score is not None
            and state.score < 0.60
            and state.confidence >= 0.35
            and state.evidence_count >= 3
        ]
        candidates.sort(key=lambda state: (state.score or 0.0, -state.confidence))
        return [
            StudentModelWeakness(
                content_type=state.content_type,
                content_id=state.content_id,
                dimension=state.dimension,
                score=state.score or 0.0,
                confidence=state.confidence,
            )
            for state in candidates[:5]
        ]

    @staticmethod
    def _error_tags(states: list[MasteryState]) -> list[StudentModelErrorTag]:
        counts: Counter[str] = Counter()
        for state in states:
            counts.update(state.error_tag_counts)
        return [StudentModelErrorTag(tag=tag, count=count) for tag, count in counts.most_common(5)]

    @staticmethod
    def _coverage(evidence_count: int) -> CoverageStatus:
        if evidence_count < 10:
            return CoverageStatus.INSUFFICIENT
        if evidence_count < 50:
            return CoverageStatus.PARTIAL
        return CoverageStatus.MEANINGFUL
