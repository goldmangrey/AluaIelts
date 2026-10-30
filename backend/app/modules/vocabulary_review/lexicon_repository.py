import json
from functools import cached_property, lru_cache
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.modules.vocabulary_review.models import LexicalItem, LexicalKind


class CanonicalLexiconRepository:
    """Read-only production repository for the generated local RU corpus."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    @cached_property
    def manifest(self) -> dict[str, object]:
        try:
            return json.loads((self._directory / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Canonical vocabulary manifest is unavailable.") from exc

    @cached_property
    def items(self) -> tuple[LexicalItem, ...]:
        try:
            rows = [
                json.loads(line)
                for line in (self._directory / "lexicon.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
            values = TypeAdapter(tuple[LexicalItem, ...]).validate_python(rows)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise RuntimeError("Canonical vocabulary corpus is invalid.") from exc
        ids = [item.id for item in values]
        if len(ids) != len(set(ids)) or len(values) < 3000:
            raise RuntimeError("Canonical vocabulary corpus is incomplete.")
        return values

    @cached_property
    def initial_pool(self) -> dict:
        return json.loads((self._directory / "initial_pool_v1.json").read_text())["items"]

    @cached_property
    def initial_items(self) -> tuple[LexicalItem, ...]:
        return tuple(
            LexicalItem.model_validate(
                {**item.model_dump(), **self.initial_pool[item.id]["overrides"]}
            )
            for item in self.items
            if item.id in self.initial_pool
        )

    @cached_property
    def aliases(self) -> dict[str, str]:
        try:
            value = json.loads((self._directory / "legacy_id_map.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Canonical vocabulary aliases are invalid.") from exc
        return {str(old): str(new) for old, new in value.items()}

    @cached_property
    def _by_id(self) -> dict[str, LexicalItem]:
        from app.modules.study.catalog import catalog
        values = {item.id: item for item in self.items}
        for c in catalog().cards:
            values[c.id] = LexicalItem(
                id=c.id, kind="phrase" if c.type == "fixed_phrase" else c.type,
                term=c.term, translation_ru=c.translation_ru, definition_en=c.definition_en,
                examples=(c.example_en,), usage_ru=c.usage_note_ru, cefr=c.cefr_level,
                topic=str(c.primary_topic_id), provenance=({"source_line": c.source_line},),
            )
        return values

    def resolve_id(self, item_id: str) -> str | None:
        resolved = self.aliases.get(item_id, item_id)
        return resolved if resolved in self._by_id else None

    def get(self, item_id: str) -> LexicalItem | None:
        resolved = self.resolve_id(item_id)
        return self._by_id.get(resolved) if resolved else None

    def by_kind(self, *kinds: LexicalKind) -> tuple[LexicalItem, ...]:
        allowed = set(kinds)
        return tuple(item for item in self.items if item.kind in allowed)

    @property
    def dataset_version(self) -> str:
        return str(self.manifest["dataset_version"])


@lru_cache
def get_canonical_lexicon_repository() -> CanonicalLexiconRepository:
    path = Path(__file__).parents[2] / "content" / "vocabulary_v2"
    return CanonicalLexiconRepository(path)
