import json
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ExternalServiceError, NotFoundError, ValidationError
from app.modules.curriculum.content_repository import CurriculumContentRepository
from app.modules.curriculum.models import CurriculumNodeType
from app.modules.grammar.models import GrammarDataset, GrammarDatasetMetadata, GrammarLesson


class _Manifest(BaseModel):
    dataset_id: str
    version: int
    version_label: str
    language: str
    support_language: str
    content_files: tuple[str, ...]


class GrammarContentRepository:
    def __init__(self, content_directory: Path, curriculum: CurriculumContentRepository) -> None:
        self._content_directory = content_directory
        self._curriculum = curriculum

    @cached_property
    def dataset(self) -> GrammarDataset:
        try:
            manifest = _Manifest.model_validate(self._read_json("manifest.json"))
            lessons = tuple(
                GrammarLesson.model_validate(raw)
                for filename in manifest.content_files
                for raw in self._read_json(filename)
            )
            dataset = GrammarDataset(
                metadata=GrammarDatasetMetadata(
                    id=manifest.dataset_id,
                    version=manifest.version,
                    version_label=manifest.version_label,
                    language=manifest.language,
                    support_language=manifest.support_language,
                ),
                lessons=lessons,
            )
            self._validate(dataset)
            return dataset
        except (OSError, json.JSONDecodeError, PydanticValidationError, ValueError) as exc:
            raise ExternalServiceError(
                message="The grammar content is invalid or unavailable.",
                code="grammar_invalid_content",
            ) from exc

    def _read_json(self, filename: str) -> Any:
        path = self._content_directory / filename
        if path.parent != self._content_directory or path.suffix != ".json":
            raise ValueError("Invalid grammar content filename.")
        return json.loads(path.read_text(encoding="utf-8"))

    @cached_property
    def _lessons_by_id(self) -> dict[str, GrammarLesson]:
        return {lesson.id: lesson for lesson in self.dataset.lessons}

    @cached_property
    def _lessons_by_node_id(self) -> dict[str, GrammarLesson]:
        return {
            node_id: lesson
            for lesson in self.dataset.lessons
            for node_id in lesson.curriculum_node_ids
        }

    def get_lesson(self, lesson_id: str) -> GrammarLesson:
        try:
            return self._lessons_by_id[lesson_id]
        except KeyError as exc:
            raise NotFoundError(
                message="Grammar lesson not found.", code="grammar_lesson_not_found"
            ) from exc

    def get_lesson_for_curriculum_node(self, node_id: str) -> GrammarLesson:
        node = self._curriculum.get_node(node_id)
        if node.type != CurriculumNodeType.GRAMMAR_TOPIC:
            raise ValidationError(
                message="The curriculum node is not a grammar topic.",
                code="grammar_node_not_grammar",
            )
        try:
            return self._lessons_by_node_id[node_id]
        except KeyError as exc:
            raise ExternalServiceError(
                message="Grammar curriculum mapping is unavailable.",
                code="grammar_curriculum_mapping_error",
            ) from exc

    def lessons_for_stage(self, stage_id: str) -> list[GrammarLesson]:
        try:
            stage = self._curriculum.get_stage(stage_id)
        except NotFoundError as exc:
            raise NotFoundError(
                message="Grammar stage not found.", code="grammar_stage_not_found"
            ) from exc
        return [
            self.get_lesson_for_curriculum_node(node.id)
            for node in stage.nodes
            if node.type == CurriculumNodeType.GRAMMAR_TOPIC
        ]

    def get_stage_title(self, stage_id: str) -> str:
        try:
            return self._curriculum.get_stage(stage_id).title
        except NotFoundError as exc:
            raise NotFoundError(
                message="Grammar stage not found.", code="grammar_stage_not_found"
            ) from exc

    def search(
        self,
        *,
        query: str | None = None,
        cefr: str | None = None,
        stage_id: str | None = None,
        tag: str | None = None,
    ) -> list[GrammarLesson]:
        needle = query.casefold().strip() if query else None
        results: list[GrammarLesson] = []
        for lesson in self.dataset.lessons:
            searchable = " ".join(
                (lesson.title, lesson.short_title, lesson.summary, *lesson.keywords, *lesson.tags)
            ).casefold()
            if needle and needle not in searchable:
                continue
            if cefr and lesson.cefr_level.value.casefold() != cefr.casefold():
                continue
            if stage_id and lesson.stage_id != stage_id:
                continue
            if tag and tag.casefold() not in {value.casefold() for value in lesson.tags}:
                continue
            results.append(lesson)
        return results

    def _validate(self, dataset: GrammarDataset) -> None:
        lesson_ids = [lesson.id for lesson in dataset.lessons]
        if len(lesson_ids) != len(set(lesson_ids)):
            raise ValueError("Duplicate grammar lesson id.")

        curriculum_nodes = {
            node.id: node
            for stage in self._curriculum.program.stages
            for node in stage.nodes
            if node.type == CurriculumNodeType.GRAMMAR_TOPIC
        }
        mapped_nodes = [
            node_id for lesson in dataset.lessons for node_id in lesson.curriculum_node_ids
        ]
        if len(mapped_nodes) != len(set(mapped_nodes)):
            raise ValueError("Duplicate grammar curriculum mapping.")
        if set(mapped_nodes) != set(curriculum_nodes):
            raise ValueError("Grammar curriculum mapping is incomplete.")
        if len(dataset.lessons) != len(curriculum_nodes):
            raise ValueError("Grammar v1 requires one lesson per curriculum node.")

        known_lessons = set(lesson_ids)
        valid_stages = {stage.id for stage in self._curriculum.program.stages}
        for lesson in dataset.lessons:
            if lesson.stage_id not in valid_stages:
                raise ValueError(f"Invalid stage for {lesson.id}.")
            if lesson.curriculum_node_ids != (lesson.id,):
                raise ValueError(f"Grammar v1 mapping must be 1:1 for {lesson.id}.")
            node = curriculum_nodes[lesson.id]
            if node.stage_id != lesson.stage_id or node.cefr_level != lesson.cefr_level:
                raise ValueError(f"Curriculum metadata mismatch for {lesson.id}.")
            if node.content_refs != (lesson.id,):
                raise ValueError(f"Curriculum content reference mismatch for {lesson.id}.")
            for contrast in lesson.contrasts:
                if contrast.related_lesson_id == lesson.id:
                    raise ValueError(f"Self-referencing contrast in {lesson.id}.")
                if contrast.related_lesson_id not in known_lessons:
                    raise ValueError(f"Invalid contrast reference in {lesson.id}.")


@lru_cache
def get_grammar_content_repository() -> GrammarContentRepository:
    from app.modules.curriculum.content_repository import get_curriculum_content_repository

    directory = Path(__file__).parents[2] / "content" / "grammar"
    return GrammarContentRepository(directory, get_curriculum_content_repository())
