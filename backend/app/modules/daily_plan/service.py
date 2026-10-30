from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.curriculum.models import (
    CurriculumNodeStatus,
    CurriculumNodeType,
    UserCurriculumOverview,
)
from app.modules.curriculum.service import CurriculumService
from app.modules.daily_plan.engine import DailyPlanEngine
from app.modules.daily_plan.models import (
    DailyPlan,
    DailyPlanContentType,
    DailyPlanContext,
    DailyPlanGenerationContext,
    DailyPlanItemKind,
    DailyPlanItemState,
    DailyPlanPriority,
    DailyPlanReason,
    DailyPlanStatus,
    PlanningCandidate,
)
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.daily_plan.schemas import (
    DailyPlanItemResponse,
    DailyPlanResponse,
    DailyPlanVocabularySummary,
)
from app.modules.grammar.content_repository import GrammarContentRepository
from app.modules.mastery.models import (
    MasteryContentType,
    MasteryLevel,
    MasteryState,
    MasteryTrend,
)
from app.modules.mastery.repository import MasteryRepository
from app.modules.student_model.models import CoverageStatus
from app.modules.users.repository import UserRepository
from app.modules.vocabulary_review.contract import PACK_SCHEMA_VERSION
from app.modules.vocabulary_review.service import VocabularyLearningService

DEFAULT_STUDY_MINUTES = 30


class DailyPlanService:
    def __init__(
        self,
        repository: DailyPlanRepository,
        engine: DailyPlanEngine,
        curriculum: CurriculumService,
        users: UserRepository,
        mastery: MasteryRepository,
        grammar: GrammarContentRepository,
        vocabulary_learning: VocabularyLearningService,
    ) -> None:
        self._repository = repository
        self._engine = engine
        self._curriculum = curriculum
        self._users = users
        self._mastery = mastery
        self._grammar = grammar
        self._vocabulary_learning = vocabulary_learning

    def ensure_today(self, uid: str, timezone: str) -> DailyPlanResponse:
        local_date = self._local_date(timezone)
        existing = self._repository.get(uid, local_date)
        if existing is not None:
            return self._hydrate(uid, self._migrate(existing))

        profile = self._users.get_by_uid(uid)
        overview = self._curriculum.get_user_curriculum(uid)
        states = self._mastery.list_states(uid)
        coverage = self._coverage(self._mastery.count_distinct_applied_events(uid))
        target_minutes = (
            profile.daily_study_minutes
            if profile and profile.daily_study_minutes is not None
            else DEFAULT_STUDY_MINUTES
        )
        context = DailyPlanContext(
            uid=uid,
            local_date=local_date,
            target_minutes=target_minutes,
            coverage=coverage,
            progression_candidates=self._progression_candidates(overview),
            review_candidates=self._review_candidates(states),
        )
        draft = self._engine.build(context)
        now = datetime.now(UTC)
        plan = DailyPlan(
            plan_id=f"{uid}:{local_date.isoformat()}",
            user_id=uid,
            local_date=local_date,
            timezone_at_generation=timezone,
            target_minutes=target_minutes,
            estimated_minutes=sum(item.estimated_minutes for item in draft.items),
            curriculum_version=overview.curriculum_version,
            vocabulary_version=PACK_SCHEMA_VERSION,
            grammar_version=self._grammar.dataset.metadata.version,
            strategy=draft.strategy,
            status=draft.status,
            items=draft.items,
            created_at=now,
            updated_at=now,
            generation_context=DailyPlanGenerationContext(
                declared_level=profile.current_level if profile else None,
                recommended_stage_id=overview.recommended_stage_id,
                active_node_id=overview.active_node_id,
                student_model_coverage=coverage,
                target_minutes=target_minutes,
            ),
        )
        return self._hydrate(uid, self._repository.create(uid, plan))

    def get_today(self, uid: str, timezone: str) -> DailyPlanResponse:
        return self.get_plan(uid, self._local_date(timezone))

    def get_plan(self, uid: str, local_date: date) -> DailyPlanResponse:
        plan = self._repository.get(uid, local_date)
        if plan is None:
            raise NotFoundError(message="Daily plan not found.", code="daily_plan_not_found")
        return self._hydrate(uid, self._migrate(plan))

    def complete_item_from_exercise_session(
        self, uid: str, local_date: date, item_id: str
    ) -> DailyPlan:
        return self._repository.complete_item(uid, local_date, item_id)

    @staticmethod
    def _local_date(timezone: str) -> date:
        try:
            zone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValidationError(
                message="Timezone must be a valid IANA identifier.",
                code="daily_plan_invalid_timezone",
            ) from exc
        return datetime.now(zone).date()

    def _progression_candidates(
        self, overview: UserCurriculumOverview
    ) -> tuple[PlanningCandidate, ...]:
        candidates: list[PlanningCandidate] = []
        for stage in overview.stages:
            for progress in stage.nodes:
                if progress.status not in {
                    CurriculumNodeStatus.ACTIVE,
                    CurriculumNodeStatus.AVAILABLE,
                }:
                    continue
                node = progress.node
                active = progress.status == CurriculumNodeStatus.ACTIVE
                progression_rank = 0 if active else 1 if progress.is_recommended else 2
                reason = (
                    DailyPlanReason.ACTIVE_CURRICULUM if active else DailyPlanReason.NEXT_CURRICULUM
                )
                priority = DailyPlanPriority.HIGH if active else DailyPlanPriority.NORMAL
                order = stage.stage.order * 1000 + node.order
                if node.type == CurriculumNodeType.GRAMMAR_TOPIC:
                    lesson = self._grammar.get_lesson_for_curriculum_node(node.id)
                    candidates.append(
                        PlanningCandidate(
                            kind=DailyPlanItemKind.GRAMMAR_FOCUS,
                            content_type=DailyPlanContentType.GRAMMAR_LESSON,
                            content_id=lesson.id,
                            curriculum_node_id=node.id,
                            title=lesson.title,
                            subtitle=lesson.summary,
                            cefr_level=lesson.cefr_level.value,
                            reason=reason,
                            priority=priority,
                            curriculum_order=order,
                            progression_rank=progression_rank,
                        )
                    )
                elif node.type == CurriculumNodeType.VOCABULARY_TRACK:
                    # Vocabulary progression is represented by the canonical daily lexical pack.
                    continue
                else:
                    candidates.append(
                        PlanningCandidate(
                            kind=DailyPlanItemKind.REINFORCEMENT,
                            content_type=DailyPlanContentType.CURRICULUM_NODE,
                            content_id=node.id,
                            curriculum_node_id=node.id,
                            title=node.title,
                            subtitle=node.description,
                            cefr_level=node.cefr_level.value,
                            reason=DailyPlanReason.REINFORCEMENT,
                            priority=DailyPlanPriority.LOW,
                            curriculum_order=order,
                            progression_rank=progression_rank if node.required else 3,
                        )
                    )
        return tuple(candidates)

    def _review_candidates(
        self,
        states: list[MasteryState],
    ) -> tuple[PlanningCandidate, ...]:
        candidates: list[PlanningCandidate] = []
        for state in states:
            if state.score is None or (
                state.level == MasteryLevel.STRONG and state.confidence >= 0.75
            ):
                continue
            declining = state.trend == MasteryTrend.DECLINING and state.confidence >= 0.35
            weak = (
                state.level == MasteryLevel.DEVELOPING
                and state.confidence >= 0.35
                and state.evidence_count >= 3
            ) or (state.score < 0.60 and state.confidence >= 0.35 and state.evidence_count >= 3)
            if not declining and not weak:
                continue
            grammar = state.content_type == MasteryContentType.GRAMMAR_LESSON
            if grammar:
                lesson = self._grammar.get_lesson(state.content_id)
                title, subtitle, cefr = (
                    lesson.title,
                    lesson.summary,
                    lesson.cefr_level.value,
                )
            else:
                # Vocabulary review is exclusively scheduled by vocabulary_review SRS.
                continue
            candidates.append(
                PlanningCandidate(
                    kind=(
                        DailyPlanItemKind.GRAMMAR_REVIEW
                        if grammar
                        else DailyPlanItemKind.VOCABULARY_REVIEW
                    ),
                    content_type=(
                        DailyPlanContentType.GRAMMAR_LESSON
                        if grammar
                        else DailyPlanContentType.VOCABULARY_ITEM
                    ),
                    content_id=state.content_id,
                    title=title,
                    subtitle=subtitle,
                    cefr_level=cefr,
                    reason=(
                        DailyPlanReason.DECLINING_MASTERY
                        if declining
                        else DailyPlanReason.WEAK_MASTERY
                    ),
                    priority=(DailyPlanPriority.HIGH if declining else DailyPlanPriority.NORMAL),
                    review_rank=(
                        0 if declining else 1,
                        state.score,
                        -sum(state.error_tag_counts.values()),
                        state.last_evidence_at.isoformat(),
                    ),
                )
            )
        return tuple(candidates)

    def _hydrate(self, uid: str, plan: DailyPlan) -> DailyPlanResponse:
        items = [DailyPlanItemResponse.model_validate(item.model_dump()) for item in plan.items]
        completed = [item for item in plan.items if item.state == DailyPlanItemState.COMPLETED]
        vocabulary_today = self._vocabulary_learning.get_today(
            uid,
            plan.timezone_at_generation,
            datetime.combine(
                plan.local_date,
                datetime.min.time().replace(hour=12),
                tzinfo=ZoneInfo(plan.timezone_at_generation),
            ).astimezone(UTC),
        )
        pack = vocabulary_today.daily_pack
        return DailyPlanResponse(
            **plan.model_dump(exclude={"items", "user_id", "archived_legacy_vocabulary_items"}),
            items=items,
            vocabulary=DailyPlanVocabularySummary(
                pack_id=pack.pack_id,
                content_version=pack.content_version,
                total_lexical_units=(
                    len(pack.core_words) + len(pack.synonym_upgrades) + len(pack.phrases)
                ),
                core_word_count=len(pack.core_words),
                synonym_upgrade_count=len(pack.synonym_upgrades),
                phrase_chunk_count=len(pack.phrases),
                review_due_count=vocabulary_today.review_due_count,
            ),
            total_items=len(items),
            completed_items=len(completed),
            remaining_items=sum(item.state == DailyPlanItemState.PENDING for item in plan.items),
            completed_estimated_minutes=sum(item.estimated_minutes for item in completed),
        )

    def _migrate(self, plan: DailyPlan) -> DailyPlan:
        if plan.planner_version == 2:
            return plan
        legacy_vocabulary = tuple(
            item for item in plan.items if item.content_type == DailyPlanContentType.VOCABULARY_ITEM
        )
        active_items = tuple(
            item.model_copy(update={"sequence": sequence})
            for sequence, item in enumerate(
                (
                    item
                    for item in plan.items
                    if item.content_type != DailyPlanContentType.VOCABULARY_ITEM
                ),
                start=1,
            )
        )
        status = plan.status if active_items else DailyPlanStatus.NO_AVAILABLE_CONTENT
        if active_items and all(
            item.state == DailyPlanItemState.COMPLETED for item in active_items
        ):
            status = DailyPlanStatus.COMPLETED
        migrated = plan.model_copy(
            update={
                "schema_version": 2,
                "planner_version": 2,
                "items": active_items,
                "archived_legacy_vocabulary_items": (
                    plan.archived_legacy_vocabulary_items + legacy_vocabulary
                ),
                "estimated_minutes": sum(item.estimated_minutes for item in active_items),
                "status": status,
                "updated_at": datetime.now(UTC),
            }
        )
        return self._repository.replace(plan.user_id, migrated)

    @staticmethod
    def _coverage(event_count: int) -> CoverageStatus:
        if event_count < 10:
            return CoverageStatus.INSUFFICIENT
        if event_count < 50:
            return CoverageStatus.PARTIAL
        return CoverageStatus.MEANINGFUL
