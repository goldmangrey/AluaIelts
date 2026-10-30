from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.models import EnglishLevel


class GrammarStructure(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    formula: str
    example: str


class GrammarUse(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    explanation_en: str
    explanation_ru: str | None = None
    example: str
    translation_ru: str | None = None


class GrammarExample(BaseModel):
    model_config = ConfigDict(frozen=True)

    sentence: str
    translation_ru: str | None = None
    note: str | None = None


class GrammarCommonError(BaseModel):
    model_config = ConfigDict(frozen=True)

    wrong: str
    correct: str
    explanation_en: str
    explanation_ru: str
    error_tag: str = Field(pattern=r"^[a-z][a-z0-9_]*$")


class GrammarContrast(BaseModel):
    model_config = ConfigDict(frozen=True)

    related_lesson_id: str | None = None
    title: str
    explanation_en: str
    explanation_ru: str
    examples: tuple[GrammarExample, ...] = Field(min_length=1)


class GrammarLesson(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    short_title: str
    cefr_level: EnglishLevel
    stage_id: str
    summary: str
    explanation_en: str
    explanation_ru: str
    structures: tuple[GrammarStructure, ...] = Field(min_length=1)
    uses: tuple[GrammarUse, ...] = Field(min_length=1)
    examples: tuple[GrammarExample, ...] = Field(min_length=2)
    common_errors: tuple[GrammarCommonError, ...] = ()
    contrasts: tuple[GrammarContrast, ...] = ()
    usage_notes: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    curriculum_node_ids: tuple[str, ...] = Field(min_length=1)
    estimated_study_minutes: int | None = Field(default=None, ge=5, le=120)


class GrammarDatasetMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int = Field(ge=1)
    version_label: str
    language: str
    support_language: str


class GrammarDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: GrammarDatasetMetadata
    lessons: tuple[GrammarLesson, ...]
