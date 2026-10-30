import json
from functools import cached_property, lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ExternalServiceError, NotFoundError
from app.modules.curriculum.models import (
    CurriculumNode,
    CurriculumNodeType,
    CurriculumProgram,
    CurriculumStage,
    CurriculumTrack,
)
from app.modules.users.models import EnglishLevel


class _ContentNode(BaseModel):
    id: str
    title: str
    prerequisites: tuple[str, ...] | None = None


class _ContentStage(BaseModel):
    id: str
    order: int
    title: str
    subtitle: str
    cefr_from: EnglishLevel
    cefr_to: EnglishLevel
    description: str
    target_ielts_range: str | None = None
    estimated_weeks: int | None = None
    entry_prerequisites: tuple[str, ...] = ()
    grammar_nodes: tuple[_ContentNode, ...]
    vocabulary_nodes: tuple[_ContentNode, ...]
    reinforcement_node: _ContentNode


class _ContentProgram(BaseModel):
    id: str
    version: int
    version_label: str
    title: str
    description: str
    stages: tuple[_ContentStage, ...]


class CurriculumContentRepository:
    def __init__(self, content_path: Path) -> None:
        self._content_path = content_path

    @cached_property
    def program(self) -> CurriculumProgram:
        try:
            data = json.loads(self._content_path.read_text(encoding="utf-8"))
            content = _ContentProgram.model_validate(data)
            program = self._expand(content)
            self._validate_graph(program)
            return program
        except (OSError, json.JSONDecodeError, PydanticValidationError, ValueError) as exc:
            raise ExternalServiceError(
                message="The curriculum content is invalid or unavailable.",
                code="curriculum_invalid_content",
            ) from exc

    @staticmethod
    def _expand(content: _ContentProgram) -> CurriculumProgram:
        stages: list[CurriculumStage] = []
        for source in content.stages:
            nodes: list[CurriculumNode] = []
            previous_grammar_id: str | None = None
            order = 1
            for item in source.grammar_nodes:
                prerequisites = item.prerequisites
                if prerequisites is None:
                    prerequisites = (
                        (previous_grammar_id,)
                        if previous_grammar_id
                        else source.entry_prerequisites
                    )
                nodes.append(
                    CurriculumNode(
                        id=item.id,
                        stage_id=source.id,
                        track=CurriculumTrack.GRAMMAR,
                        type=CurriculumNodeType.GRAMMAR_TOPIC,
                        title=item.title,
                        short_title=item.title,
                        description=f"Build accurate control of {item.title.lower()}.",
                        order=order,
                        cefr_level=source.cefr_to,
                        prerequisites=prerequisites,
                        objectives=(f"Understand and apply {item.title.lower()}.",),
                        content_refs=(item.id,),
                        tags=(source.cefr_to.value.lower(), "grammar"),
                    )
                )
                previous_grammar_id = item.id
                order += 1
            vocabulary_ids: list[str] = []
            for item in source.vocabulary_nodes:
                prerequisites = (
                    item.prerequisites
                    if item.prerequisites is not None
                    else source.entry_prerequisites
                )
                nodes.append(
                    CurriculumNode(
                        id=item.id,
                        stage_id=source.id,
                        track=CurriculumTrack.VOCABULARY,
                        type=CurriculumNodeType.VOCABULARY_TRACK,
                        title=item.title,
                        short_title=item.title,
                        description=f"Develop usable vocabulary for {item.title.lower()}.",
                        order=order,
                        cefr_level=source.cefr_to,
                        prerequisites=prerequisites,
                        objectives=(f"Recognise and use language for {item.title.lower()}.",),
                        content_refs=(item.id,),
                        tags=(source.cefr_to.value.lower(), "vocabulary"),
                    )
                )
                vocabulary_ids.append(item.id)
                order += 1
            reinforcement_prerequisites = source.reinforcement_node.prerequisites or tuple(
                [*(item.id for item in source.grammar_nodes), *vocabulary_ids]
            )
            reinforcement = source.reinforcement_node
            nodes.append(
                CurriculumNode(
                    id=reinforcement.id,
                    stage_id=source.id,
                    track=CurriculumTrack.MIXED,
                    type=CurriculumNodeType.REINFORCEMENT,
                    title=reinforcement.title,
                    short_title="Reinforcement",
                    description="Consolidate this stage across grammar and vocabulary.",
                    order=order,
                    cefr_level=source.cefr_to,
                    estimated_minutes=45,
                    prerequisites=reinforcement_prerequisites,
                    objectives=(
                        "Consolidate grammar.",
                        "Revisit vocabulary.",
                        "Prepare for mixed recognition and production.",
                    ),
                    content_refs=(reinforcement.id,),
                    tags=(source.cefr_to.value.lower(), "reinforcement"),
                )
            )
            stages.append(
                CurriculumStage(
                    id=source.id,
                    order=source.order,
                    title=source.title,
                    subtitle=source.subtitle,
                    cefr_from=source.cefr_from,
                    cefr_to=source.cefr_to,
                    description=source.description,
                    target_ielts_range=source.target_ielts_range,
                    estimated_weeks=source.estimated_weeks,
                    nodes=tuple(nodes),
                )
            )
        return CurriculumProgram(
            id=content.id,
            version=content.version,
            version_label=content.version_label,
            title=content.title,
            description=content.description,
            stages=tuple(stages),
        )

    def get_stage(self, stage_id: str) -> CurriculumStage:
        for stage in self.program.stages:
            if stage.id == stage_id:
                return stage
        raise NotFoundError(
            message="Curriculum stage not found.", code="curriculum_stage_not_found"
        )

    def get_node(self, node_id: str) -> CurriculumNode:
        for stage in self.program.stages:
            for node in stage.nodes:
                if node.id == node_id:
                    return node
        raise NotFoundError(message="Curriculum node not found.", code="curriculum_node_not_found")

    @staticmethod
    def _validate_graph(program: CurriculumProgram) -> None:
        stage_ids = [stage.id for stage in program.stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("Duplicate curriculum stage id.")
        if [stage.order for stage in program.stages] != sorted(
            stage.order for stage in program.stages
        ):
            raise ValueError("Curriculum stages are not ordered.")

        nodes = [node for stage in program.stages for node in stage.nodes]
        node_by_id = {node.id: node for node in nodes}
        if len(node_by_id) != len(nodes):
            raise ValueError("Duplicate curriculum node id.")
        for stage in program.stages:
            if [node.order for node in stage.nodes] != sorted(node.order for node in stage.nodes):
                raise ValueError(f"Nodes in {stage.id} are not ordered.")
            if any(node.stage_id != stage.id for node in stage.nodes):
                raise ValueError(f"Invalid stage reference in {stage.id}.")
        for node in nodes:
            if node.id in node.prerequisites:
                raise ValueError(f"Node {node.id} depends on itself.")
            if any(prerequisite not in node_by_id for prerequisite in node.prerequisites):
                raise ValueError(f"Unknown prerequisite for {node.id}.")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("Curriculum dependency cycle detected.")
            if node_id in visited:
                return
            visiting.add(node_id)
            for prerequisite in node_by_id[node_id].prerequisites:
                visit(prerequisite)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in node_by_id:
            visit(node_id)


@lru_cache
def get_curriculum_content_repository() -> CurriculumContentRepository:
    path = Path(__file__).parents[2] / "content" / "curriculum" / "curriculum_v1.json"
    return CurriculumContentRepository(path)
