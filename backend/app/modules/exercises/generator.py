import hashlib
import re
from uuid import NAMESPACE_URL, uuid5

from app.core.exceptions import ValidationError
from app.modules.curriculum.content_repository import CurriculumContentRepository
from app.modules.curriculum.models import CurriculumNodeType
from app.modules.daily_plan.models import DailyPlanContentType, DailyPlanItem
from app.modules.exercises.models import ExerciseInstance, ExerciseOption, ExerciseType
from app.modules.grammar.content_repository import GrammarContentRepository
from app.modules.grammar.models import GrammarLesson
from app.modules.mastery.models import EvidenceKind, MasteryDimension, MasteryState
from app.modules.vocabulary.content_repository import VocabularyContentRepository
from app.modules.vocabulary.models import VocabularyItem

ENGINE_VERSION = 1

EXERCISE_MAPPING = {
    ExerciseType.VOCABULARY_MEANING_MCQ: (
        MasteryDimension.MEANING_RECOGNITION,
        EvidenceKind.RECOGNITION,
    ),
    ExerciseType.VOCABULARY_RECALL: (MasteryDimension.MEANING_RECALL, EvidenceKind.RECALL),
    ExerciseType.VOCABULARY_COLLOCATION_MCQ: (
        MasteryDimension.COLLOCATION,
        EvidenceKind.CONTROLLED_USE,
    ),
    ExerciseType.VOCABULARY_CONTEXT_GAP: (
        MasteryDimension.CONTEXTUAL_USAGE,
        EvidenceKind.CONTROLLED_USE,
    ),
    ExerciseType.GRAMMAR_RULE_MCQ: (
        MasteryDimension.RULE_RECOGNITION,
        EvidenceKind.RECOGNITION,
    ),
    ExerciseType.GRAMMAR_FORM_CHOICE: (
        MasteryDimension.FORM_CONTROL,
        EvidenceKind.CONTROLLED_USE,
    ),
    ExerciseType.GRAMMAR_ERROR_CORRECTION: (
        MasteryDimension.ERROR_DETECTION,
        EvidenceKind.ERROR_CORRECTION,
    ),
    ExerciseType.GRAMMAR_CONTRAST_MCQ: (
        MasteryDimension.CONTRAST_SELECTION,
        EvidenceKind.CONTRAST,
    ),
}


class DeterministicExerciseGenerator:
    def __init__(
        self,
        vocabulary: VocabularyContentRepository,
        grammar: GrammarContentRepository,
        curriculum: CurriculumContentRepository,
    ) -> None:
        self._vocabulary = vocabulary
        self._grammar = grammar
        self._curriculum = curriculum

    def generate(
        self,
        session_id: str,
        item: DailyPlanItem,
        mastery_states: list[MasteryState],
    ) -> tuple[ExerciseInstance, ...]:
        if item.content_type == DailyPlanContentType.VOCABULARY_ITEM:
            vocabulary = self._vocabulary.get_item(item.content_id)
            count = 2 if item.kind.value == "vocabulary_review" else 3
            preferred = self._weak_dimensions(mastery_states, item.content_id)
            exercises = self._vocabulary_exercises(session_id, vocabulary, preferred)
            return self._sequence(exercises[:count])
        if item.content_type == DailyPlanContentType.GRAMMAR_LESSON:
            lesson = self._grammar.get_lesson(item.content_id)
            count = 3 if item.kind.value == "grammar_review" else 4
            preferred = self._weak_dimensions(mastery_states, item.content_id)
            exercises = self._grammar_exercises(session_id, lesson, preferred)
            return self._sequence(exercises[:count])
        return self._reinforcement(session_id, item)

    @staticmethod
    def _weak_dimensions(
        states: list[MasteryState], content_id: str
    ) -> tuple[MasteryDimension, ...]:
        relevant = [
            state for state in states if state.content_id == content_id and state.score is not None
        ]
        return tuple(
            state.dimension
            for state in sorted(
                relevant, key=lambda value: (value.score or 0, value.dimension.value)
            )
        )

    def _vocabulary_exercises(
        self, session_id: str, item: VocabularyItem, preferred: tuple[MasteryDimension, ...]
    ) -> list[ExerciseInstance]:
        builders = {
            MasteryDimension.MEANING_RECOGNITION: self._vocabulary_meaning,
            MasteryDimension.MEANING_RECALL: self._vocabulary_recall,
            MasteryDimension.COLLOCATION: self._vocabulary_collocation,
            MasteryDimension.CONTEXTUAL_USAGE: self._vocabulary_context,
        }
        order = [
            *preferred,
            MasteryDimension.MEANING_RECOGNITION,
            MasteryDimension.MEANING_RECALL,
            MasteryDimension.COLLOCATION,
            MasteryDimension.CONTEXTUAL_USAGE,
        ]
        result: list[ExerciseInstance] = []
        for dimension in order:
            if dimension not in builders or any(value.dimension == dimension for value in result):
                continue
            exercise = builders[dimension](session_id, item, len(result) + 1)
            if exercise:
                result.append(exercise)
        return result

    def _grammar_exercises(
        self, session_id: str, lesson: GrammarLesson, preferred: tuple[MasteryDimension, ...]
    ) -> list[ExerciseInstance]:
        builders = {
            MasteryDimension.RULE_RECOGNITION: self._grammar_rule,
            MasteryDimension.FORM_CONTROL: self._grammar_form,
            MasteryDimension.ERROR_DETECTION: self._grammar_error,
            MasteryDimension.CONTRAST_SELECTION: self._grammar_contrast,
        }
        order = [*preferred, *builders]
        result: list[ExerciseInstance] = []
        for dimension in order:
            if dimension not in builders or any(value.dimension == dimension for value in result):
                continue
            exercise = builders[dimension](session_id, lesson, len(result) + 1)
            if exercise:
                result.append(exercise)
        # Fill sparse lessons using additional canonical structures.
        index = 1
        while len(result) < 4 and index < len(lesson.structures):
            result.append(self._grammar_rule(session_id, lesson, len(result) + 1, index))
            index += 1
        return result

    def _id(self, session_id: str, kind: ExerciseType, ordinal: int) -> str:
        return str(uuid5(NAMESPACE_URL, f"alua:{session_id}:{kind.value}:{ordinal}"))

    def _options(
        self, exercise_id: str, correct: str, distractors: list[str]
    ) -> tuple[ExerciseOption, ...]:
        texts = list(
            dict.fromkeys([correct, *[value for value in distractors if value != correct]])
        )[:4]
        if len(texts) < 2:
            raise ValidationError(
                message="Not enough canonical content to generate exercise options.",
                code="exercise_content_unavailable",
            )
        texts.sort(key=lambda value: hashlib.sha256(f"{exercise_id}:{value}".encode()).hexdigest())
        return tuple(
            ExerciseOption(id=chr(97 + index), text=text) for index, text in enumerate(texts)
        )

    def _choice(
        self,
        *,
        session_id: str,
        kind: ExerciseType,
        content_type: DailyPlanContentType,
        content_id: str,
        node_id: str | None,
        ordinal: int,
        instruction: str,
        prompt: str,
        correct: str,
        distractors: list[str],
        explanation: str,
        error_tags: tuple[str, ...] = (),
    ) -> ExerciseInstance:
        exercise_id = self._id(session_id, kind, ordinal)
        options = self._options(exercise_id, correct, distractors)
        answer_key = next(option.id for option in options if option.text == correct)
        dimension, evidence = EXERCISE_MAPPING[kind]
        return ExerciseInstance(
            exercise_id=exercise_id,
            exercise_type=kind,
            content_type=content_type,
            content_id=content_id,
            curriculum_node_id=node_id,
            dimension=dimension,
            evidence_kind=evidence,
            instruction=instruction,
            prompt=prompt,
            options=options,
            answer_key=answer_key,
            correct_answer_display=correct,
            explanation=explanation,
            error_tags=error_tags,
            sequence=ordinal,
        )

    def _typed(
        self,
        *,
        session_id: str,
        kind: ExerciseType,
        content_type: DailyPlanContentType,
        content_id: str,
        node_id: str | None,
        ordinal: int,
        instruction: str,
        prompt: str,
        answer: str,
        explanation: str,
        error_tags: tuple[str, ...] = (),
    ) -> ExerciseInstance:
        dimension, evidence = EXERCISE_MAPPING[kind]
        return ExerciseInstance(
            exercise_id=self._id(session_id, kind, ordinal),
            exercise_type=kind,
            content_type=content_type,
            content_id=content_id,
            curriculum_node_id=node_id,
            dimension=dimension,
            evidence_kind=evidence,
            instruction=instruction,
            prompt=prompt,
            answer_key=answer,
            correct_answer_display=answer,
            explanation=explanation,
            error_tags=error_tags,
            sequence=ordinal,
        )

    def _vocabulary_meaning(
        self, session_id: str, item: VocabularyItem, ordinal: int
    ) -> ExerciseInstance:
        pool = sorted(
            self._vocabulary.dataset.items,
            key=lambda value: (
                value.cefr_level != item.cefr_level,
                value.part_of_speech != item.part_of_speech,
                value.id,
            ),
        )
        return self._choice(
            session_id=session_id,
            kind=ExerciseType.VOCABULARY_MEANING_MCQ,
            content_type=DailyPlanContentType.VOCABULARY_ITEM,
            content_id=item.id,
            node_id=None,
            ordinal=ordinal,
            instruction="Choose the correct meaning.",
            prompt=item.lemma,
            correct=item.definition_en,
            distractors=[value.definition_en for value in pool if value.id != item.id],
            explanation=f"{item.lemma}: {item.definition_en}",
        )

    def _vocabulary_recall(
        self, session_id: str, item: VocabularyItem, ordinal: int
    ) -> ExerciseInstance:
        return self._typed(
            session_id=session_id,
            kind=ExerciseType.VOCABULARY_RECALL,
            content_type=DailyPlanContentType.VOCABULARY_ITEM,
            content_id=item.id,
            node_id=None,
            ordinal=ordinal,
            instruction="Type the target word or phrase.",
            prompt=f"{item.definition_en}\n{item.translation_ru}",
            answer=item.lemma,
            explanation=f"The target expression is “{item.lemma}”.",
        )

    def _vocabulary_collocation(
        self, session_id: str, item: VocabularyItem, ordinal: int
    ) -> ExerciseInstance | None:
        if not item.collocations:
            return None
        distractors = [
            value
            for other in self._vocabulary.dataset.items
            if other.id != item.id
            for value in other.collocations
            if item.normalized_lemma not in value.casefold()
        ]
        return self._choice(
            session_id=session_id,
            kind=ExerciseType.VOCABULARY_COLLOCATION_MCQ,
            content_type=DailyPlanContentType.VOCABULARY_ITEM,
            content_id=item.id,
            node_id=None,
            ordinal=ordinal,
            instruction="Choose the canonical collocation.",
            prompt=item.lemma,
            correct=item.collocations[0],
            distractors=distractors,
            explanation=f"A canonical collocation is ‘{item.collocations[0]}’.",
        )

    def _vocabulary_context(
        self, session_id: str, item: VocabularyItem, ordinal: int
    ) -> ExerciseInstance | None:
        pattern = re.compile(rf"\b{re.escape(item.lemma)}\b", re.IGNORECASE)
        example = next((value for value in item.examples if pattern.search(value)), None)
        if not example:
            return None
        return self._typed(
            session_id=session_id,
            kind=ExerciseType.VOCABULARY_CONTEXT_GAP,
            content_type=DailyPlanContentType.VOCABULARY_ITEM,
            content_id=item.id,
            node_id=None,
            ordinal=ordinal,
            instruction="Complete the sentence with the target expression.",
            prompt=pattern.sub("___", example, count=1),
            answer=item.lemma,
            explanation=example,
        )

    def _grammar_rule(
        self, session_id: str, lesson: GrammarLesson, ordinal: int, structure_index: int = 0
    ) -> ExerciseInstance:
        structure = lesson.structures[structure_index]
        distractors = [
            value.formula
            for other in self._grammar.dataset.lessons
            if other.id != lesson.id
            for value in other.structures
        ]
        return self._choice(
            session_id=session_id,
            kind=ExerciseType.GRAMMAR_RULE_MCQ,
            content_type=DailyPlanContentType.GRAMMAR_LESSON,
            content_id=lesson.id,
            node_id=lesson.curriculum_node_ids[0],
            ordinal=ordinal,
            instruction="Choose the correct structure.",
            prompt=lesson.title,
            correct=structure.formula,
            distractors=distractors,
            explanation=f"{structure.label}: {structure.formula}",
        )

    def _grammar_form(
        self, session_id: str, lesson: GrammarLesson, ordinal: int
    ) -> ExerciseInstance | None:
        if not lesson.common_errors:
            return None
        error = lesson.common_errors[0]
        return self._choice(
            session_id=session_id,
            kind=ExerciseType.GRAMMAR_FORM_CHOICE,
            content_type=DailyPlanContentType.GRAMMAR_LESSON,
            content_id=lesson.id,
            node_id=lesson.curriculum_node_ids[0],
            ordinal=ordinal,
            instruction="Choose the correct sentence.",
            prompt=lesson.title,
            correct=error.correct,
            distractors=[error.wrong],
            explanation=error.explanation_en,
            error_tags=(error.error_tag,),
        )

    def _grammar_error(
        self, session_id: str, lesson: GrammarLesson, ordinal: int
    ) -> ExerciseInstance | None:
        if not lesson.common_errors:
            return None
        error = lesson.common_errors[0]
        return self._typed(
            session_id=session_id,
            kind=ExerciseType.GRAMMAR_ERROR_CORRECTION,
            content_type=DailyPlanContentType.GRAMMAR_LESSON,
            content_id=lesson.id,
            node_id=lesson.curriculum_node_ids[0],
            ordinal=ordinal,
            instruction="Correct the sentence.",
            prompt=error.wrong,
            answer=error.correct,
            explanation=error.explanation_en,
            error_tags=(error.error_tag,),
        )

    def _grammar_contrast(
        self, session_id: str, lesson: GrammarLesson, ordinal: int
    ) -> ExerciseInstance | None:
        if not lesson.contrasts:
            return None
        contrast = lesson.contrasts[0]
        correct = contrast.examples[0].sentence
        distractors = [value.sentence for value in lesson.examples if value.sentence != correct]
        return self._choice(
            session_id=session_id,
            kind=ExerciseType.GRAMMAR_CONTRAST_MCQ,
            content_type=DailyPlanContentType.GRAMMAR_LESSON,
            content_id=lesson.id,
            node_id=lesson.curriculum_node_ids[0],
            ordinal=ordinal,
            instruction="Choose the example that matches the contrast.",
            prompt=contrast.title,
            correct=correct,
            distractors=distractors,
            explanation=contrast.explanation_en,
        )

    def _reinforcement(self, session_id: str, item: DailyPlanItem) -> tuple[ExerciseInstance, ...]:
        node = self._curriculum.get_node(item.content_id)
        sources = [self._curriculum.get_node(value) for value in node.prerequisites] + [node]
        generated: list[ExerciseInstance] = []
        for source in sources:
            if source.type == CurriculumNodeType.GRAMMAR_TOPIC:
                lesson = self._grammar.get_lesson_for_curriculum_node(source.id)
                generated.extend(
                    self._grammar_exercises(f"{session_id}:{source.id}", lesson, ())[:2]
                )
            elif source.type == CurriculumNodeType.VOCABULARY_TRACK:
                for track in self._vocabulary.tracks_for_curriculum_node(source.id):
                    for vocabulary in self._vocabulary.items_for_track(track.id)[:1]:
                        generated.extend(
                            self._vocabulary_exercises(
                                f"{session_id}:{source.id}:{vocabulary.id}", vocabulary, ()
                            )[:2]
                        )
            if len(generated) >= 5:
                break
        unique = list(
            {
                (value.content_type, value.content_id, value.exercise_type): value
                for value in generated
            }.values()
        )[:5]
        if len(unique) < 2:
            raise ValidationError(
                message="Not enough canonical content for reinforcement.",
                code="exercise_content_unavailable",
            )
        return self._sequence(unique)

    @staticmethod
    def _sequence(exercises: list[ExerciseInstance]) -> tuple[ExerciseInstance, ...]:
        return tuple(
            value.model_copy(update={"sequence": index}) for index, value in enumerate(exercises, 1)
        )
