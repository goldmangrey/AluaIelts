#!/usr/bin/env python3
"""Print one selector result; call from separate processes and compare hashes."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.users.models import EnglishLevel  # noqa: E402
from app.modules.vocabulary_review.lexicon_repository import CanonicalLexiconRepository  # noqa: E402
from app.modules.vocabulary_review.selector import DailyVocabularySelector  # noqa: E402


repository = CanonicalLexiconRepository(ROOT / "backend/app/content/vocabulary_v2")
selector = DailyVocabularySelector(repository.items, repository.dataset_version)
result = selector.select(
    uid="audit-user",
    local_date=date(2026, 10, 28),
    level=EnglishLevel.B1,
    due_count=9,
    introduced_ids=set(),
)
payload = json.dumps(
    [result.core_word_ids, result.synonym_upgrade_ids, result.phrase_ids],
    ensure_ascii=False,
    separators=(",", ":"),
)
print(hashlib.sha256(payload.encode()).hexdigest(), payload)
