import json
import unicodedata
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ExternalServiceError, NotFoundError, ValidationError
from app.modules.curriculum.content_repository import CurriculumContentRepository
from app.modules.curriculum.models import CurriculumNodeType
from app.modules.vocabulary.models import (
    PartOfSpeech,
    VocabularyDataset,
    VocabularyDatasetMetadata,
    VocabularyImportance,
    VocabularyItem,
    VocabularyRegister,
    VocabularyTopic,
    VocabularyTrack,
    WordFamilyMember,
)


class _Manifest(BaseModel):
    id: str
    version: int
    version_label: str
    source_language: str
    translation_language: str
    content_files: tuple[str, ...]


class _ContentItem(BaseModel):
    id: str
    lemma: str
    part_of_speech: PartOfSpeech
    translation_ru: str
    definition_en: str
    example: str
    collocations: tuple[str, ...] = ()
    synonyms: tuple[str, ...] = ()
    antonyms: tuple[str, ...] = ()
    word_family: tuple[WordFamilyMember, ...] = ()
    usage_notes: tuple[str, ...] = ()
    common_confusions: tuple[str, ...] = ()


class _ContentTrack(BaseModel):
    id: str
    stage_id: str
    title: str
    description: str
    cefr_level: str
    topic: VocabularyTopic
    items: tuple[_ContentItem, ...] = Field(min_length=4)
    related_item_ids: tuple[str, ...] = Field(min_length=2)


def normalize_lemma(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return " ".join(normalized.split())


class VocabularyContentRepository:
    def __init__(
        self,
        content_directory: Path,
        curriculum: CurriculumContentRepository,
    ) -> None:
        self._content_directory = content_directory
        self._curriculum = curriculum

    @cached_property
    def dataset(self) -> VocabularyDataset:
        try:
            manifest = _Manifest.model_validate(self._read_json("manifest.json"))
            content_tracks: list[_ContentTrack] = []
            for filename in manifest.content_files:
                content_tracks.extend(
                    _ContentTrack.model_validate(item) for item in self._read_json(filename)
                )
            memberships: dict[str, list[str]] = {}
            for track in content_tracks:
                for item_id in (*(item.id for item in track.items), *track.related_item_ids):
                    memberships.setdefault(item_id, []).append(track.id)
            tracks = tuple(
                VocabularyTrack(
                    id=track.id,
                    stage_id=track.stage_id,
                    title=track.title,
                    description=track.description,
                    cefr_level=track.cefr_level,
                    topic=track.topic,
                    item_ids=tuple(item.id for item in track.items) + track.related_item_ids,
                )
                for track in content_tracks
            )
            items = [
                self._expand_item(item, track, memberships[item.id], index)
                for track in content_tracks
                for index, item in enumerate(track.items)
            ]
            dataset = VocabularyDataset(
                metadata=VocabularyDatasetMetadata(
                    id=manifest.id,
                    version=manifest.version,
                    version_label=manifest.version_label,
                    source_language=manifest.source_language,
                    translation_language=manifest.translation_language,
                ),
                tracks=tracks,
                items=tuple(items),
            )
            self._validate(dataset)
            return dataset
        except (OSError, json.JSONDecodeError, PydanticValidationError, ValueError) as exc:
            raise ExternalServiceError(
                message="The vocabulary content is invalid or unavailable.",
                code="vocabulary_invalid_content",
            ) from exc

    @staticmethod
    def _expand_item(
        item: _ContentItem,
        track: _ContentTrack,
        track_ids: list[str],
        index: int,
    ) -> VocabularyItem:
        academic = track.stage_id == "ielts_academic"
        return VocabularyItem(
            id=item.id,
            lemma=item.lemma,
            normalized_lemma=normalize_lemma(item.lemma),
            part_of_speech=item.part_of_speech,
            sense=item.definition_en,
            definition_en=item.definition_en,
            translation_ru=item.translation_ru,
            cefr_level=track.cefr_level,
            grammatical_register=(
                VocabularyRegister.ACADEMIC if academic else VocabularyRegister.NEUTRAL
            ),
            frequency="common" if index < 2 else "less_common",
            importance=VocabularyImportance.CORE if index == 0 else VocabularyImportance.HIGH,
            topics=(track.topic,),
            track_ids=tuple(track_ids),
            word_family=item.word_family,
            collocations=item.collocations,
            synonyms=item.synonyms,
            antonyms=item.antonyms,
            examples=(item.example,),
            usage_notes=item.usage_notes,
            common_confusions=item.common_confusions,
            tags=(track.cefr_level.casefold(), track.topic.value),
        )

    def _read_json(self, filename: str) -> Any:
        path = self._content_directory / filename
        if path.parent != self._content_directory or path.suffix != ".json":
            raise ValueError("Invalid vocabulary content filename.")
        return json.loads(path.read_text(encoding="utf-8"))

    @cached_property
    def _items_by_id(self) -> dict[str, VocabularyItem]:
        return {item.id: item for item in self.dataset.items}

    @cached_property
    def _tracks_by_id(self) -> dict[str, VocabularyTrack]:
        return {track.id: track for track in self.dataset.tracks}

    def get_item(self, item_id: str) -> VocabularyItem:
        try:
            return self._items_by_id[item_id]
        except KeyError as exc:
            raise NotFoundError(
                message="Vocabulary item not found.", code="vocabulary_item_not_found"
            ) from exc

    def get_track(self, track_id: str) -> VocabularyTrack:
        try:
            return self._tracks_by_id[track_id]
        except KeyError as exc:
            raise NotFoundError(
                message="Vocabulary track not found.", code="vocabulary_track_not_found"
            ) from exc

    def items_for_track(self, track_id: str) -> list[VocabularyItem]:
        track = self.get_track(track_id)
        return [self._items_by_id[item_id] for item_id in track.item_ids]

    def search(
        self,
        *,
        query: str | None = None,
        cefr: str | None = None,
        topic: VocabularyTopic | None = None,
        part_of_speech: PartOfSpeech | None = None,
        track_id: str | None = None,
    ) -> list[VocabularyItem]:
        if track_id is not None:
            candidates = self.items_for_track(track_id)
        else:
            candidates = list(self.dataset.items)
        needle = normalize_lemma(query) if query else None
        results = []
        for item in candidates:
            searchable = " ".join(
                (item.lemma, item.definition_en, item.translation_ru, *item.synonyms)
            ).casefold()
            if needle and needle not in searchable:
                continue
            if cefr and item.cefr_level.value.casefold() != cefr.casefold():
                continue
            if topic and topic not in item.topics:
                continue
            if part_of_speech and item.part_of_speech != part_of_speech:
                continue
            results.append(item)
        return results

    def tracks_for_curriculum_node(self, node_id: str) -> list[VocabularyTrack]:
        node = self._curriculum.get_node(node_id)
        if node.type != CurriculumNodeType.VOCABULARY_TRACK:
            raise ValidationError(
                message="The curriculum node is not a vocabulary track.",
                code="curriculum_node_not_vocabulary",
            )
        return [self.get_track(reference) for reference in node.content_refs]

    def _validate(self, dataset: VocabularyDataset) -> None:
        item_ids = [item.id for item in dataset.items]
        track_ids = [track.id for track in dataset.tracks]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Duplicate vocabulary item id.")
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("Duplicate vocabulary track id.")
        if len(dataset.items) < 300:
            raise ValueError("Vocabulary dataset must contain at least 300 unique items.")

        known_items = set(item_ids)
        known_tracks = set(track_ids)
        for track in dataset.tracks:
            if len(track.item_ids) != len(set(track.item_ids)):
                raise ValueError(f"Duplicate item in track {track.id}.")
            if any(item_id not in known_items for item_id in track.item_ids):
                raise ValueError(f"Unknown item in track {track.id}.")
        for item in dataset.items:
            if item.normalized_lemma != normalize_lemma(item.lemma):
                raise ValueError(f"Invalid normalized lemma for {item.id}.")
            if not item.track_ids or any(
                track_id not in known_tracks for track_id in item.track_ids
            ):
                raise ValueError(f"Invalid track mapping for {item.id}.")
            for track_id in item.track_ids:
                if item.id not in self._track_item_ids(dataset, track_id):
                    raise ValueError(f"Asymmetric track mapping for {item.id}.")

        curriculum_tracks = {
            reference
            for stage in self._curriculum.program.stages
            for node in stage.nodes
            if node.type == CurriculumNodeType.VOCABULARY_TRACK
            for reference in node.content_refs
        }
        if known_tracks != curriculum_tracks:
            missing = sorted(curriculum_tracks - known_tracks)
            extra = sorted(known_tracks - curriculum_tracks)
            raise ValueError(f"Curriculum track mismatch; missing={missing}, extra={extra}.")

    @staticmethod
    def _track_item_ids(dataset: VocabularyDataset, track_id: str) -> tuple[str, ...]:
        return next(track.item_ids for track in dataset.tracks if track.id == track_id)


@lru_cache
def get_vocabulary_content_repository() -> VocabularyContentRepository:
    from app.modules.curriculum.content_repository import get_curriculum_content_repository

    path = Path(__file__).parents[2] / "content" / "vocabulary"
    return VocabularyContentRepository(path, get_curriculum_content_repository())
