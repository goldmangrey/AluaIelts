from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.models import EnglishLevel


class PartOfSpeech(StrEnum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PHRASE = "phrase"
    PHRASAL_VERB = "phrasal_verb"
    OTHER = "other"


class VocabularyRegister(StrEnum):
    NEUTRAL = "neutral"
    INFORMAL = "informal"
    FORMAL = "formal"
    ACADEMIC = "academic"


class VocabularyFrequency(StrEnum):
    VERY_COMMON = "very_common"
    COMMON = "common"
    LESS_COMMON = "less_common"


class VocabularyImportance(StrEnum):
    CORE = "core"
    HIGH = "high"
    SUPPORTING = "supporting"


class VocabularyTopic(StrEnum):
    EVERYDAY_LIFE = "everyday_life"
    FAMILY_RELATIONSHIPS = "family_relationships"
    HOME = "home"
    FOOD = "food"
    TRAVEL = "travel"
    EDUCATION = "education"
    WORK = "work"
    HEALTH = "health"
    SHOPPING_MONEY = "shopping_money"
    COMMUNICATION = "communication"
    TECHNOLOGY = "technology"
    ENVIRONMENT = "environment"
    SOCIETY = "society"
    CULTURE = "culture"
    MEDIA = "media"
    SCIENCE = "science"
    BUSINESS = "business"
    GOVERNMENT = "government"
    IELTS_ACADEMIC = "ielts_academic"


class WordFamilyMember(BaseModel):
    model_config = ConfigDict(frozen=True)

    lemma: str
    part_of_speech: PartOfSpeech


class VocabularyItem(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    lemma: str
    normalized_lemma: str
    part_of_speech: PartOfSpeech
    sense: str
    definition_en: str
    translation_ru: str
    cefr_level: EnglishLevel
    grammatical_register: VocabularyRegister = Field(
        default=VocabularyRegister.NEUTRAL,
        alias="register",
        serialization_alias="register",
    )
    frequency: VocabularyFrequency = VocabularyFrequency.COMMON
    importance: VocabularyImportance = VocabularyImportance.SUPPORTING
    topics: tuple[VocabularyTopic, ...]
    track_ids: tuple[str, ...]
    word_family: tuple[WordFamilyMember, ...] = ()
    collocations: tuple[str, ...] = ()
    synonyms: tuple[str, ...] = ()
    antonyms: tuple[str, ...] = ()
    examples: tuple[str, ...] = Field(min_length=1)
    usage_notes: tuple[str, ...] = ()
    common_confusions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


class VocabularyTrack(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    stage_id: str
    title: str
    description: str
    cefr_level: EnglishLevel
    topic: VocabularyTopic
    item_ids: tuple[str, ...] = Field(min_length=6)


class VocabularyDatasetMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int = Field(ge=1)
    version_label: str
    source_language: str
    translation_language: str


class VocabularyDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: VocabularyDatasetMetadata
    tracks: tuple[VocabularyTrack, ...]
    items: tuple[VocabularyItem, ...]
