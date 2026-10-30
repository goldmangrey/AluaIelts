import structlog

from app.core.config import Settings
from app.modules.daily_plan.models import DailyPlanContentType, DailyPlanItem
from app.modules.exercises.ai_generator import OpenAIExerciseGenerator
from app.modules.exercises.ai_models import ExerciseGenerationBlueprint, ExerciseGenerationSlot
from app.modules.exercises.ai_validator import AIExerciseValidator
from app.modules.exercises.generator import DeterministicExerciseGenerator
from app.modules.exercises.models import (
    ExerciseGenerationMode,
    ExerciseGenerationSource,
    ExerciseInstance,
)
from app.modules.grammar.content_repository import GrammarContentRepository
from app.modules.mastery.models import MasteryState
from app.modules.vocabulary.content_repository import VocabularyContentRepository

logger = structlog.get_logger(__name__)


class ExerciseGenerationCoordinator:
    def __init__(
        self,
        *,
        deterministic: DeterministicExerciseGenerator,
        ai: OpenAIExerciseGenerator,
        validator: AIExerciseValidator,
        vocabulary: VocabularyContentRepository,
        grammar: GrammarContentRepository,
        settings: Settings,
    ) -> None:
        self._deterministic = deterministic
        self._ai = ai
        self._validator = validator
        self._vocabulary = vocabulary
        self._grammar = grammar
        self._settings = settings

    def generate(
        self, session_id: str, item: DailyPlanItem, mastery_states: list[MasteryState]
    ) -> tuple[tuple[ExerciseInstance, ...], ExerciseGenerationMode]:
        fallback = self._deterministic.generate(session_id, item, mastery_states)
        blueprint = self._blueprint(fallback)
        batch = self._ai.generate(blueprint)
        if batch is None:
            return fallback, ExerciseGenerationMode.DETERMINISTIC
        candidates = {candidate.slot_id: candidate for candidate in batch.exercises}
        result: list[ExerciseInstance] = []
        for slot in blueprint.slots:
            candidate = candidates.get(slot.slot_id)
            accepted = (
                self._validator.build(slot, candidate, self._settings.openai_exercise_model)
                if candidate
                else None
            )
            result.append(accepted or slot.fallback)
        ai_count = sum(
            exercise.generation_source == ExerciseGenerationSource.OPENAI for exercise in result
        )
        mode = (
            ExerciseGenerationMode.OPENAI
            if ai_count == len(result)
            else ExerciseGenerationMode.HYBRID
            if ai_count
            else ExerciseGenerationMode.DETERMINISTIC
        )
        logger.info(
            "exercise_generation_completed",
            requested_slots=len(result),
            accepted_ai_slots=ai_count,
            fallback_slots=len(result) - ai_count,
            generation_mode=mode.value,
            model=self._settings.openai_exercise_model,
        )
        return tuple(result), mode

    def _blueprint(self, exercises: tuple[ExerciseInstance, ...]) -> ExerciseGenerationBlueprint:
        return ExerciseGenerationBlueprint(
            slots=tuple(self._slot(exercise) for exercise in exercises)
        )

    def _slot(self, exercise: ExerciseInstance) -> ExerciseGenerationSlot:
        facts: dict[str, object]
        allowed: tuple[str, ...]
        if exercise.content_type == DailyPlanContentType.VOCABULARY_ITEM:
            item = self._vocabulary.get_item(exercise.content_id)
            facts = {
                "lemma": item.lemma,
                "definition_en": item.definition_en,
                "part_of_speech": item.part_of_speech.value,
                "collocations": item.collocations[:3],
                "examples": item.examples[:2],
            }
            allowed = tuple(item.examples[:2]) + tuple(item.collocations[:3])
            cefr = item.cefr_level.value
        else:
            lesson = self._grammar.get_lesson(exercise.content_id)
            facts = {
                "title": lesson.title,
                "summary": lesson.summary,
                "structures": [value.model_dump() for value in lesson.structures[:3]],
                "common_errors": [value.model_dump() for value in lesson.common_errors[:2]],
                "contrasts": [value.model_dump() for value in lesson.contrasts[:1]],
            }
            allowed = tuple(value.sentence for value in lesson.examples[:4])
            cefr = lesson.cefr_level.value
        return ExerciseGenerationSlot(
            slot_id=f"slot_{exercise.sequence}",
            exercise_type=exercise.exercise_type,
            content_type=exercise.content_type.value,
            content_id=exercise.content_id,
            curriculum_node_id=exercise.curriculum_node_id,
            cefr_level=cefr,
            dimension=exercise.dimension.value,
            evidence_kind=exercise.evidence_kind.value,
            difficulty=exercise.difficulty.value,
            canonical_answer_anchor=exercise.correct_answer_display,
            canonical_facts=facts,
            allowed_source_material=allowed,
            fallback=exercise,
        )
