from pydantic import BaseModel, Field

from app.modules.vocabulary.models import VocabularyItem, VocabularyTrack


class VocabularyListResponse(BaseModel):
    items: list[VocabularyItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class VocabularyTrackSummary(BaseModel):
    id: str
    stage_id: str
    title: str
    description: str
    cefr_level: str
    topic: str
    item_count: int


class VocabularyTrackDetail(BaseModel):
    track: VocabularyTrack
    items: list[VocabularyItem]


class CurriculumVocabularyResponse(BaseModel):
    curriculum_node_id: str
    tracks: list[VocabularyTrackDetail]
