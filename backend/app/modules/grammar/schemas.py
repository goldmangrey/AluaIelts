from pydantic import BaseModel, Field

from app.modules.grammar.models import GrammarLesson


class GrammarListResponse(BaseModel):
    items: list[GrammarLesson]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    dataset_version: int = Field(ge=1)


class GrammarStageResponse(BaseModel):
    stage_id: str
    title: str
    lessons: list[GrammarLesson]
    dataset_version: int
