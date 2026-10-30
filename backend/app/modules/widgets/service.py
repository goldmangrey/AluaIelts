from datetime import UTC, date, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import ValidationError
from app.modules.daily_plan.models import (
    DailyPlan,
    DailyPlanContentType,
    DailyPlanItem,
    DailyPlanItemKind,
    DailyPlanItemState,
)
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.exercises.generator import ENGINE_VERSION
from app.modules.exercises.repository import ExerciseRepository
from app.modules.grammar.content_repository import GrammarContentRepository
from app.modules.partner.repository import PartnerRepository
from app.modules.progress.service import ProgressAnalyticsService
from app.modules.users.models import UserRole
from app.modules.users.repository import UserRepository
from app.modules.vocabulary_review.service import VocabularyLearningService
from app.modules.widgets.models import (
    LearnerWidgetSnapshot,
    PartnerWidgetPermissions,
    PartnerWidgetSnapshot,
    WidgetGrammarSnapshot,
    WidgetPracticeSnapshot,
    WidgetSnapshotEnvelope,
    WidgetTodaySnapshot,
    WidgetUserMode,
    WidgetVocabularySnapshot,
)


class WidgetSnapshotService:
    def __init__(
        self,
        *,
        users: UserRepository,
        plans: DailyPlanRepository,
        grammar: GrammarContentRepository,
        relationships: PartnerRepository,
        progress: ProgressAnalyticsService,
        exercises: ExerciseRepository,
        vocabulary_learning: VocabularyLearningService,
    ) -> None:
        self._users = users
        self._plans = plans
        self._grammar = grammar
        self._relationships = relationships
        self._progress = progress
        self._exercises = exercises
        self._vocabulary_learning = vocabulary_learning

    def get_snapshot(self, uid: str, timezone_name: str) -> WidgetSnapshotEnvelope:
        timezone = self._timezone(timezone_name)
        local_date = datetime.now(UTC).astimezone(timezone).date()
        profile = self._users.get_by_uid(uid)
        monitoring = self._relationships.get_active_by_partner(uid)
        sharing = self._relationships.get_active_by_learner(uid)
        is_learner = bool(profile and profile.role == UserRole.LEARNER) or sharing is not None
        is_partner = bool(profile and profile.role == UserRole.PARTNER) or monitoring is not None
        learner = (
            self._learner(uid, local_date, timezone_name, profile.display_name if profile else None)
            if is_learner
            else None
        )
        partner = self._partner(monitoring, local_date, timezone_name) if monitoring else None
        mode = (
            WidgetUserMode.BOTH
            if is_learner and is_partner
            else WidgetUserMode.PARTNER
            if is_partner
            else WidgetUserMode.LEARNER
        )
        now = datetime.now(UTC)
        return WidgetSnapshotEnvelope(
            generation_id=str(uuid4()),
            generated_at=now,
            valid_from=now,
            valid_until=now + timedelta(hours=24),
            user_mode=mode,
            learner=learner,
            partner=partner,
        )

    def _learner(
        self, uid: str, local_date: date, timezone_name: str, display_name: str | None
    ) -> LearnerWidgetSnapshot:
        learning = self._vocabulary_learning.get_today(uid, timezone_name)
        pack_items = [
            *learning.daily_pack.core_words,
            *learning.daily_pack.synonym_upgrades,
            *learning.daily_pack.phrases,
        ]
        vocabulary_cards = tuple(
            WidgetVocabularySnapshot(
                content_id=item.id,
                term=item.term,
                translation_ru=item.translation_ru,
                ipa=item.ipa,
                cefr=item.cefr,
                definition_en=item.definition_en,
                example=item.examples[0] if item.examples else None,
                part_of_speech=item.part_of_speech,
            )
            for item in pack_items
        )
        plan = self._plans.get(uid, local_date)
        if plan is None:
            return LearnerWidgetSnapshot(
                display_name=display_name,
                local_date=local_date,
                pack_id=learning.daily_pack.pack_id,
                content_version=learning.daily_pack.content_version,
                pack_schema_version=learning.daily_pack.schema_version,
                vocabulary_cards=vocabulary_cards,
            )
        pending = [item for item in plan.items if item.state == DailyPlanItemState.PENDING]
        grammar_items = self._ordered_content_items(plan, DailyPlanContentType.GRAMMAR_LESSON)
        practice_item = pending[0] if pending else None
        return LearnerWidgetSnapshot(
            display_name=display_name,
            local_date=local_date,
            pack_id=learning.daily_pack.pack_id,
            content_version=learning.daily_pack.content_version,
            pack_schema_version=learning.daily_pack.schema_version,
            today=self._today(
                plan,
                len(learning.daily_pack.core_words)
                + len(learning.daily_pack.synonym_upgrades)
                + len(learning.daily_pack.phrases),
                learning.review_due_count,
            ),
            vocabulary_cards=vocabulary_cards,
            grammar_cards=self._grammar_deck(grammar_items),
            practice=self._practice_snapshot(uid, local_date, practice_item),
        )

    @staticmethod
    def _ordered_content_items(
        plan: DailyPlan, content_type: DailyPlanContentType
    ) -> list[DailyPlanItem]:
        matching = [item for item in plan.items if item.content_type == content_type]
        return sorted(
            matching,
            key=lambda item: (
                item.state != DailyPlanItemState.PENDING,
                item.kind
                not in {
                    DailyPlanItemKind.GRAMMAR_FOCUS,
                    DailyPlanItemKind.VOCABULARY_LEARNING,
                },
                item.sequence,
            ),
        )

    def _partner(self, relationship, local_date: date, timezone_name: str) -> PartnerWidgetSnapshot:  # type: ignore[no-untyped-def]
        settings = relationship.sharing_settings
        learner = self._users.get_by_uid(relationship.learner_uid)
        values: dict[str, object] = {}
        if settings.share_daily_activity:
            plan = self._plans.get(relationship.learner_uid, local_date)
            if plan:
                learning = self._vocabulary_learning.get_today(
                    relationship.learner_uid, timezone_name
                )
                today = self._today(
                    plan,
                    len(learning.daily_pack.core_words)
                    + len(learning.daily_pack.synonym_upgrades)
                    + len(learning.daily_pack.phrases),
                    learning.review_due_count,
                )
                values.update(
                    active_today=today.completed_items > 0,
                    completed_items=today.completed_items,
                    total_items=today.total_items,
                    estimated_planned_minutes=today.estimated_planned_minutes,
                    estimated_completed_minutes=today.estimated_completed_minutes,
                    current_focus=today.current_focus,
                )
        if settings.share_progress_analytics:
            progress = self._progress.get_snapshot(relationship.learner_uid, 7, timezone_name)
            values["active_days_7"] = progress.summary.active_days
        return PartnerWidgetSnapshot(
            learner_display_name=(
                learner.display_name if learner and learner.display_name else "Learner"
            ),
            local_date=local_date,
            permissions=PartnerWidgetPermissions(
                daily_activity=settings.share_daily_activity,
                progress_analytics=settings.share_progress_analytics,
            ),
            **values,
        )

    @staticmethod
    def _today(
        plan: DailyPlan, vocabulary_count: int, vocabulary_review_due: int
    ) -> WidgetTodaySnapshot:
        completed = [item for item in plan.items if item.state == DailyPlanItemState.COMPLETED]
        pending = [item for item in plan.items if item.state != DailyPlanItemState.COMPLETED]
        focus = next((item.title for item in pending if item.priority.value == "high"), None)
        return WidgetTodaySnapshot(
            completed_items=len(completed),
            total_items=len(plan.items),
            estimated_planned_minutes=plan.estimated_minutes,
            estimated_completed_minutes=sum(item.estimated_minutes for item in completed),
            current_focus=focus or (pending[0].title if pending else None),
            grammar_items=sum(
                item.content_type == DailyPlanContentType.GRAMMAR_LESSON for item in plan.items
            ),
            vocabulary_items=vocabulary_count,
            review_items=sum(
                item.kind
                in {
                    DailyPlanItemKind.GRAMMAR_REVIEW,
                    DailyPlanItemKind.VOCABULARY_REVIEW,
                    DailyPlanItemKind.REINFORCEMENT,
                }
                for item in plan.items
            )
            + vocabulary_review_due,
        )

    def _grammar_deck(self, items: list[DailyPlanItem]) -> tuple[WidgetGrammarSnapshot, ...]:
        content_ids = [item.content_id for item in items]
        if items:
            first = self._grammar.get_lesson(items[0].content_id)
            content_ids.extend(
                lesson.id for lesson in self._grammar.lessons_for_stage(first.stage_id)
            )
        content_ids = list(dict.fromkeys(content_ids))[:6]
        return tuple(self._grammar_snapshot(content_id) for content_id in content_ids)

    def _grammar_snapshot(self, content_id: str) -> WidgetGrammarSnapshot:
        lesson = self._grammar.get_lesson(content_id)
        structure = lesson.structures[0]
        support = (
            lesson.common_errors[0].explanation_ru
            if lesson.common_errors
            else lesson.uses[0].explanation_ru
            if lesson.uses
            else lesson.explanation_ru
        )
        short_title = lesson.short_title.removesuffix(" Basics")
        return WidgetGrammarSnapshot(
            content_id=lesson.id,
            display_title=lesson.title,
            short_title=short_title,
            formula=structure.formula,
            support_ru=support,
            example=structure.example,
        )

    def _practice_snapshot(
        self, uid: str, local_date: date, item: DailyPlanItem | None
    ) -> WidgetPracticeSnapshot | None:
        if item is None:
            return None
        session_id = str(
            uuid5(
                NAMESPACE_URL,
                f"alua:{uid}:{local_date}:{item.item_id}:{ENGINE_VERSION}",
            )
        )
        session = self._exercises.get_session(uid, session_id)
        return WidgetPracticeSnapshot(
            local_date=local_date,
            daily_plan_item_id=item.item_id,
            title=item.title,
            item_kind=item.kind.value,
            existing_session_id=session.session_id if session else None,
            question_count=session.total_exercises if session else None,
            remaining_count=(session.total_exercises - session.answered_exercises)
            if session
            else None,
            estimated_minutes=item.estimated_minutes,
            has_existing_session=session is not None,
        )

    @staticmethod
    def _timezone(name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValidationError(
                message="A valid IANA timezone is required.", code="widget_invalid_timezone"
            ) from exc
