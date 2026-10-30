"""Reproducible structural checks. These are NOT a linguistic quality certificate.

Run from backend: python -m scripts.lexicon.audit_initial_pool
"""

import csv
import json
from collections import Counter
from pathlib import Path

from app.modules.vocabulary_review.lexicon_repository import get_canonical_lexicon_repository


def main():
    repo = get_canonical_lexicon_repository()
    rows = repo.items
    candidates = [i for i in rows if i.examples and i.definition_en and i.cefr]
    pool = repo.initial_items
    assert len(pool) == 300
    assert len({i.id for i in pool}) == 300
    assert len({i.term.casefold() for i in pool}) == 300
    assert all(
        i.translation_ru
        and i.examples
        and i.definition_en
        and i.cefr
        and i.part_of_speech != "other"
        for i in pool
    )
    output = Path(__file__).resolve().parents[3] / "docs" / "stage2"
    output.mkdir(exist_ok=True)
    summary = {
        "automatically_scanned": len(rows),
        "complete_candidates": len(candidates),
        "initial_pool": len(pool),
        "quarantined_candidates": len(candidates) - len(pool),
        "outside_initial_pool": len(rows) - len(pool),
        "independent_human_reviews": 0,
        "human_review_pending": len(pool),
        "editorial_review": "AI-assisted sense/translation/context review; not certification",
        "rights_review": (
            "Existing alua_legacy_v1 contextual content; independent rights verification pending"
        ),
        "missing_examples": sum(not i.examples for i in rows),
        "missing_definition": sum(not i.definition_en for i in rows),
        "missing_level": sum(not i.cefr for i in rows),
        "duplicate_term_groups": sum(
            n > 1 for n in Counter(i.term.casefold() for i in rows).values()
        ),
        "pool_levels": dict(Counter(i.cefr for i in pool)),
        "pool_kinds": dict(Counter(i.kind.value for i in pool)),
    }
    (output / "content_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    by_id = {i.id: i for i in pool}
    with (output / "content_review.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "id",
                "status",
                "term",
                "difficulty",
                "part_of_speech",
                "translation",
                "definition",
                "example",
                "human_review",
            ]
        )
        for item in candidates:
            value = by_id.get(item.id, item)
            writer.writerow(
                [
                    value.id,
                    "initial_pool_ai_review" if item.id in by_id else "quarantined",
                    value.term,
                    value.cefr,
                    value.part_of_speech,
                    value.translation_ru,
                    value.definition_en,
                    " | ".join(value.examples),
                    "pending",
                ]
            )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
