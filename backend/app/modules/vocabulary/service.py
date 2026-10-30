from app.modules.vocabulary.content_repository import VocabularyContentRepository
from app.modules.vocabulary.models import PartOfSpeech, VocabularyItem, VocabularyTopic
from app.modules.vocabulary.schemas import (
    CurriculumVocabularyResponse,
    VocabularyListResponse,
    VocabularyTrackDetail,
    VocabularyTrackSummary,
)


class VocabularyService:
    def __init__(self, content: VocabularyContentRepository) -> None:
        self._content = content

    def list_items(
        self,
        *,
        query: str | None,
        cefr: str | None,
        topic: VocabularyTopic | None,
        part_of_speech: PartOfSpeech | None,
        track_id: str | None,
        limit: int,
        offset: int,
    ) -> VocabularyListResponse:
        items = self._content.search(
            query=query,
            cefr=cefr,
            topic=topic,
            part_of_speech=part_of_speech,
            track_id=track_id,
        )
        return VocabularyListResponse(
            items=items[offset : offset + limit], total=len(items), limit=limit, offset=offset
        )

    def get_item(self, item_id: str) -> VocabularyItem:
        return self._content.get_item(item_id)

    def list_tracks(self) -> list[VocabularyTrackSummary]:
        return [
            VocabularyTrackSummary(
                id=track.id,
                stage_id=track.stage_id,
                title=track.title,
                description=track.description,
                cefr_level=track.cefr_level.value,
                topic=track.topic.value,
                item_count=len(track.item_ids),
            )
            for track in self._content.dataset.tracks
        ]

    def get_track(self, track_id: str) -> VocabularyTrackDetail:
        return VocabularyTrackDetail(
            track=self._content.get_track(track_id),
            items=self._content.items_for_track(track_id),
        )

    def get_curriculum_node(self, node_id: str) -> CurriculumVocabularyResponse:
        tracks = self._content.tracks_for_curriculum_node(node_id)
        return CurriculumVocabularyResponse(
            curriculum_node_id=node_id,
            tracks=[self.get_track(track.id) for track in tracks],
        )
