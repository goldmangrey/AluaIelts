"""Immutable, validated editorial catalog. No runtime generation or remote calls."""

import hashlib
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Card(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(pattern=r"^src-\d{6}$")
    source_line: int = Field(gt=0)
    source_term: str = Field(min_length=1)
    term: str = Field(min_length=1)
    type: Literal["word", "collocation", "fixed_phrase", "phrasal_verb"]
    translation_ru: str = Field(min_length=1)
    definition_en: str = Field(min_length=1)
    cefr_level: Literal["A1", "A2", "B1", "B2", "C1"]
    priority: Literal["P1", "P2", "P3"]
    primary_topic_id: int = Field(ge=1, le=50)
    topic_ids: list[int] = Field(min_length=1)
    ielts_skills: list[Literal["Reading", "Writing", "Speaking", "Listening"]] = Field(min_length=1)
    example_en: str = Field(min_length=1)
    example_ru: str = Field(min_length=1)
    usage_note_ru: str
    review_status: Literal["ai_editorial_review"]
    human_review_pending: Literal[True]

    @model_validator(mode="after")
    def consistent(self):
        if self.id != f"src-{self.source_line:06d}" or self.primary_topic_id not in self.topic_ids:
            raise ValueError("Invalid source or primary topic")
        if len(set(self.topic_ids)) != len(self.topic_ids) or not all(
            1 <= t <= 50 for t in self.topic_ids
        ):
            raise ValueError("Invalid topics")
        return self


class Catalog:
    def __init__(self):
        directory = Path(__file__).parents[2] / "content/ielts1500"
        self.manifest = json.loads((directory / "manifest.json").read_text())
        data = (directory / "catalog.jsonl").read_bytes()
        if hashlib.sha256(data).hexdigest() != self.manifest["sha256"]:
            raise ValueError("Catalog checksum mismatch")
        self.cards = [Card.model_validate_json(line) for line in data.splitlines() if line.strip()]
        self.by_id = {c.id: c for c in self.cards}
        if (
            len(self.cards) != 1500
            or len(self.by_id) != 1500
            or len({c.term.casefold() for c in self.cards}) != 1500
            or {c.primary_topic_id for c in self.cards} != set(range(1, 51))
        ):
            raise ValueError("Expected 1500 unique cards and 50 topics")
        self.version = self.manifest["version"]
        self.legacy_links = json.loads((directory / "legacy_links.json").read_text())["links"]
        if not set(self.legacy_links) <= set(self.by_id) or len(
            set(self.legacy_links.values())
        ) != len(self.legacy_links):
            raise ValueError("Ambiguous legacy identity links")

    def program(self, level):
        levels = ["A1", "A2", "B1", "B2", "C1"]
        # Beginners progress upward; experienced learners start near their placement.
        order = (
            levels
            if level not in {"B1", "B2", "C1"}
            else {
                "B1": ["B1", "B2", "A2", "C1", "A1"],
                "B2": ["B2", "B1", "C1", "A2", "A1"],
                "C1": ["C1", "B2", "B1", "A2", "A1"],
            }[level]
        )
        cards = sorted(
            self.cards,
            key=lambda c: (
                order.index(c.cefr_level),
                (c.primary_topic_id - 1) // 5,
                c.primary_topic_id,
                c.priority,
                c.source_line,
            ),
        )
        return [
            {
                "day": i // 30 + 1,
                "ids": [c.id for c in cards[i : i + 30]],
                "title": " · ".join(
                    self.manifest["topics"][str(t)]
                    for t, _ in Counter(c.primary_topic_id for c in cards[i : i + 30]).most_common(
                        2
                    )
                ),
            }
            for i in range(0, 1500, 30)
        ]


@lru_cache
def catalog():
    return Catalog()
