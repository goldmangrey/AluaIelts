import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.modules.users.models import EnglishLevel
from app.modules.vocabulary_review.models import LexicalItem, LexicalKind

SELECTION_ALGORITHM_VERSION = 2

_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
_QUALITY_TAGS = ("Oxford", "NGSL", "OPAL", "NAWL")


@dataclass(frozen=True)
class DailyVocabularySelection:
    core_word_ids: tuple[str, ...]
    synonym_upgrade_ids: tuple[str, ...]
    phrase_ids: tuple[str, ...]


class DailyVocabularySelector:
    """Deterministic, canonical-only selector for content introduced exactly once."""

    version = SELECTION_ALGORITHM_VERSION

    def __init__(self, items: Iterable[LexicalItem], content_version: str) -> None:
        self._items = tuple(items)
        self._content_version = content_version

    def select(
        self,
        *,
        uid: str,
        local_date: date,
        level: EnglishLevel | None,
        due_count: int,
        introduced_ids: set[str],
    ) -> DailyVocabularySelection:
        target, core_target, phrase_target, upgrade_target = self._budget(due_count)
        effective_level = (level or EnglishLevel.A1).value
        available = [
            item
            for item in self._items
            if item.id not in introduced_ids
            and item.cefr in _LEVELS
            and _LEVELS.index(item.cefr) <= min(_LEVELS.index(effective_level) + 1, 5)
        ]
        words = self._level_biased_words(available, effective_level, uid, local_date, core_target)
        upgrades = self._rank(
            available, {LexicalKind.SYNONYM_UPGRADE}, effective_level, uid, local_date
        )
        phrases = self._rank(
            available,
            {LexicalKind.PHRASE, LexicalKind.COLLOCATION, LexicalKind.PHRASAL_VERB},
            effective_level,
            uid,
            local_date,
        )

        selected_words = words[:core_target]
        selected_word_ids = {item.id for item in selected_words}
        phrases.sort(
            key=lambda item: (
                not bool(selected_word_ids & set(item.related_item_ids + item.related_ids)),
                self._rank_key(item, effective_level, uid, local_date),
            )
        )
        selected_phrases = phrases[:phrase_target]
        selected_upgrades = upgrades[:upgrade_target]
        missing = target - len(selected_words) - len(selected_phrases) - len(selected_upgrades)
        if missing > 0:
            selected_words.extend(words[len(selected_words) : len(selected_words) + missing])
        return DailyVocabularySelection(
            core_word_ids=tuple(item.id for item in selected_words),
            synonym_upgrade_ids=tuple(item.id for item in selected_upgrades),
            phrase_ids=tuple(item.id for item in selected_phrases),
        )

    @staticmethod
    def _budget(due_count: int) -> tuple[int, int, int, int]:
        if due_count < 10:
            return 30, 20, 5, 5
        if due_count < 30:
            return 20, 12, 4, 4
        return 10, 6, 2, 2

    def _rank(
        self,
        items: list[LexicalItem],
        kinds: set[LexicalKind],
        level: str,
        uid: str,
        local_date: date,
    ) -> list[LexicalItem]:
        return sorted(
            (item for item in items if item.kind in kinds),
            key=lambda item: self._rank_key(item, level, uid, local_date),
        )

    def _level_biased_words(
        self,
        items: list[LexicalItem],
        level: str,
        uid: str,
        local_date: date,
        target: int,
    ) -> list[LexicalItem]:
        current_index = _LEVELS.index(level)
        current_count = round(target * 0.7)
        lower_count = round(target * 0.2) if current_index > 0 else 0
        higher_count = round(target * 0.1) if current_index < len(_LEVELS) - 1 else 0
        current_count += target - current_count - lower_count - higher_count
        ranked = self._rank(items, {LexicalKind.WORD}, level, uid, local_date)
        bands = {
            0: [item for item in ranked if item.cefr == level or item.cefr is None],
            -1: [item for item in ranked if item.cefr == _LEVELS[current_index - 1]]
            if current_index > 0
            else [],
            1: [item for item in ranked if item.cefr == _LEVELS[current_index + 1]]
            if current_index < len(_LEVELS) - 1
            else [],
        }
        chosen = bands[0][:current_count] + bands[-1][:lower_count] + bands[1][:higher_count]
        chosen_ids = {item.id for item in chosen}
        return chosen + [item for item in ranked if item.id not in chosen_ids]

    def _rank_key(
        self, item: LexicalItem, level: str, uid: str, local_date: date
    ) -> tuple[int, int, int, str]:
        current = _LEVELS.index(level)
        item_level = _LEVELS.index(item.cefr) if item.cefr in _LEVELS else current
        delta = item_level - current
        digest = self._digest(uid, local_date, item.id)
        level_penalty = abs(delta)
        quality_penalty = (
            0
            if any(
                signal.casefold() in tag.casefold()
                for signal in _QUALITY_TAGS
                for tag in item.source_tags
            )
            else 1
        )
        metadata_penalty = int(not item.ipa) + int(not item.examples) + int(not item.definition_en)
        return level_penalty, quality_penalty, metadata_penalty, digest

    def _digest(self, uid: str, local_date: date, item_id: str) -> str:
        value = f"{uid}:{local_date.isoformat()}:{self._content_version}:{self.version}:{item_id}"
        return hashlib.sha256(value.encode()).hexdigest()
