from app.modules.grammar.content_repository import GrammarContentRepository
from app.modules.grammar.models import GrammarLesson
from app.modules.grammar.schemas import GrammarListResponse, GrammarStageResponse


class GrammarService:
    def __init__(self, content: GrammarContentRepository) -> None:
        self._content = content

    def list_lessons(
        self,
        *,
        query: str | None,
        cefr: str | None,
        stage_id: str | None,
        tag: str | None,
        limit: int,
        offset: int,
    ) -> GrammarListResponse:
        lessons = self._content.search(query=query, cefr=cefr, stage_id=stage_id, tag=tag)
        return GrammarListResponse(
            items=lessons[offset : offset + limit],
            total=len(lessons),
            limit=limit,
            offset=offset,
            dataset_version=self._content.dataset.metadata.version,
        )

    def get_lesson(self, lesson_id: str) -> GrammarLesson:
        return self._content.get_lesson(lesson_id)

    def get_lesson_for_curriculum_node(self, node_id: str) -> GrammarLesson:
        return self._content.get_lesson_for_curriculum_node(node_id)

    def get_stage(self, stage_id: str) -> GrammarStageResponse:
        lessons = self._content.lessons_for_stage(stage_id)
        return GrammarStageResponse(
            stage_id=stage_id,
            title=self._content.get_stage_title(stage_id),
            lessons=lessons,
            dataset_version=self._content.dataset.metadata.version,
        )
