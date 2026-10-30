from uuid import NAMESPACE_URL, uuid5

from app.modules.daily_plan.models import (
    DailyPlanContentType,
    DailyPlanContext,
    DailyPlanDraft,
    DailyPlanItem,
    DailyPlanItemKind,
    DailyPlanItemState,
    DailyPlanStatus,
    DailyPlanStrategy,
    PlanningCandidate,
)
from app.modules.student_model.models import CoverageStatus

PLANNER_VERSION = 1
ITEM_MINUTES = {
    DailyPlanItemKind.GRAMMAR_FOCUS: 10,
    DailyPlanItemKind.VOCABULARY_LEARNING: 2,
    DailyPlanItemKind.GRAMMAR_REVIEW: 4,
    DailyPlanItemKind.VOCABULARY_REVIEW: 2,
    DailyPlanItemKind.REINFORCEMENT: 6,
}


class DailyPlanEngine:
    """Pure deterministic planning over canonical, prevalidated candidates."""

    def build(self, context: DailyPlanContext) -> DailyPlanDraft:
        reviews = self._unique_sorted_reviews(context.review_candidates)
        review_ratio = self._review_ratio(context.coverage, bool(reviews))
        review_budget = int(context.target_minutes * review_ratio)
        progression_budget = context.target_minutes - review_budget
        selected: list[PlanningCandidate] = []
        used: set[tuple[DailyPlanContentType, str]] = set()

        progression = sorted(
            context.progression_candidates,
            key=lambda candidate: (
                0 if candidate.reason.value == "active_curriculum" else 1,
                candidate.progression_rank,
                candidate.curriculum_order,
                candidate.content_id,
            ),
        )
        grammar_added = False
        vocabulary_added = 0
        progression_minutes = 0
        for candidate in progression:
            cost = ITEM_MINUTES[candidate.kind]
            key = (candidate.content_type, candidate.content_id)
            if key in used:
                continue
            if candidate.kind == DailyPlanItemKind.GRAMMAR_FOCUS and grammar_added:
                continue
            if candidate.kind == DailyPlanItemKind.VOCABULARY_LEARNING and vocabulary_added >= 15:
                continue
            minimum_continuity = (
                candidate.kind == DailyPlanItemKind.GRAMMAR_FOCUS and not grammar_added
            ) or (candidate.kind == DailyPlanItemKind.VOCABULARY_LEARNING and vocabulary_added == 0)
            if progression_minutes + cost > progression_budget and not minimum_continuity:
                continue
            if progression_minutes + cost > context.target_minutes:
                continue
            selected.append(candidate)
            used.add(key)
            progression_minutes += cost
            grammar_added |= candidate.kind == DailyPlanItemKind.GRAMMAR_FOCUS
            vocabulary_added += int(candidate.kind == DailyPlanItemKind.VOCABULARY_LEARNING)

        review_minutes = 0
        for candidate in reviews:
            cost = ITEM_MINUTES[candidate.kind]
            key = (candidate.content_type, candidate.content_id)
            if key in used or review_minutes + cost > review_budget:
                continue
            if progression_minutes + review_minutes + cost > context.target_minutes:
                continue
            selected.append(candidate)
            used.add(key)
            review_minutes += cost

        # Use spare time for additional curriculum progression, never extra new grammar.
        for candidate in progression:
            cost = ITEM_MINUTES[candidate.kind]
            key = (candidate.content_type, candidate.content_id)
            if key in used or progression_minutes + review_minutes + cost > context.target_minutes:
                continue
            if candidate.kind == DailyPlanItemKind.GRAMMAR_FOCUS:
                continue
            if candidate.kind == DailyPlanItemKind.VOCABULARY_LEARNING and vocabulary_added >= 15:
                continue
            selected.append(candidate)
            used.add(key)
            progression_minutes += cost
            vocabulary_added += int(candidate.kind == DailyPlanItemKind.VOCABULARY_LEARNING)

        items = tuple(
            DailyPlanItem(
                item_id=self._item_id(context, candidate, sequence),
                kind=candidate.kind,
                content_type=candidate.content_type,
                content_id=candidate.content_id,
                curriculum_node_id=candidate.curriculum_node_id,
                title=candidate.title,
                subtitle=candidate.subtitle,
                cefr_level=candidate.cefr_level,
                estimated_minutes=ITEM_MINUTES[candidate.kind],
                priority=candidate.priority,
                reason=candidate.reason,
                sequence=sequence,
                state=DailyPlanItemState.PENDING,
            )
            for sequence, candidate in enumerate(selected, start=1)
        )
        return DailyPlanDraft(
            strategy=self._strategy(context.coverage, review_minutes, context.target_minutes),
            status=DailyPlanStatus.READY if items else DailyPlanStatus.NO_AVAILABLE_CONTENT,
            items=items,
        )

    @staticmethod
    def _review_ratio(coverage: CoverageStatus, has_reviews: bool) -> float:
        if not has_reviews or coverage == CoverageStatus.INSUFFICIENT:
            return 0.0
        if coverage == CoverageStatus.PARTIAL:
            return 0.30
        return 0.45

    @staticmethod
    def _strategy(
        coverage: CoverageStatus, review_minutes: int, target_minutes: int
    ) -> DailyPlanStrategy:
        if coverage == CoverageStatus.INSUFFICIENT:
            return DailyPlanStrategy.CURRICULUM_FIRST
        if review_minutes == 0:
            return DailyPlanStrategy.BALANCED
        if review_minutes / target_minutes >= 0.40:
            return DailyPlanStrategy.REVIEW_HEAVY
        return DailyPlanStrategy.WEAKNESS_FOCUS

    @staticmethod
    def _unique_sorted_reviews(
        candidates: tuple[PlanningCandidate, ...],
    ) -> list[PlanningCandidate]:
        best: dict[tuple[DailyPlanContentType, str], PlanningCandidate] = {}
        for candidate in candidates:
            key = (candidate.content_type, candidate.content_id)
            current = best.get(key)
            if current is None or candidate.review_rank < current.review_rank:
                best[key] = candidate
        return sorted(
            best.values(), key=lambda candidate: (candidate.review_rank, candidate.content_id)
        )

    @staticmethod
    def _item_id(context: DailyPlanContext, candidate: PlanningCandidate, sequence: int) -> str:
        value = ":".join(
            (
                "alua",
                context.uid,
                context.local_date.isoformat(),
                candidate.kind.value,
                candidate.content_type.value,
                candidate.content_id,
                str(sequence),
            )
        )
        return str(uuid5(NAMESPACE_URL, value))
