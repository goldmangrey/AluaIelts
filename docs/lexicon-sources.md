# Alua canonical lexicon sources

The production lexicon is built offline. Normal API requests never contact these providers.
Source snapshots and their original license files must be archived together outside Git; the
canonical manifest records counts and provenance retained on every lexical record.

| Source | Source location | Used fields | License / attribution | Stored result |
|---|---|---|---|---|
| NGSL | Official NGSL 1.2 statistics CSV | headword, frequency rank | CC BY-SA 4.0; attribution to Browne, Culligan and Phillips | normalized rank and provenance |
| NAWL | Official NAWL 1.2 statistics CSV | headword, academic membership/rank | CC BY-SA 4.0; attribution to Browne, Culligan and Phillips | academic tag, rank and provenance |
| Princeton WordNet | Princeton WordNet bulk database | synset ID, POS, definition, sense-compatible lemmas | Princeton WordNet License; retain notice | definitions and sense-scoped relation candidates |
| Wiktionary via Kaikki/Wiktextract | Kaikki English JSONL extract and its dump metadata | POS, senses, definitions, Russian translations, IPA, tags, multi-word entries | Wiktionary content is CC BY-SA/GFDL; retain dump attribution and comply with share-alike requirements | normalized lexical fields and provenance |
| Tatoeba | English CC0 sentence export only | English example text and sentence ID; column 4 is date modified, not a license | CC0 | bounded attributed examples |
| Datamuse | Optional cached ingestion-time response | candidate terms/ranking hints only | Review current API terms before use | never canonical truth; candidates must be validated against corpus sources |

The build must not proceed from URLs alone. A reviewer must archive each exact snapshot, license,
checksum, and retrieval date. Items lacking a reliable Russian translation, definition, or example
remain `learner_ready=false` and are excluded from daily packs.

## Repeatability and safety

First run `uv run python scripts/lexicon/prepare_sources.py`, review normalized staging and its
checksum/license manifest, and only then run `uv run python scripts/lexicon/build_lexicon.py`.
Canonical IDs use normalized term and POS rather than array position. Raw senses retain term, POS,
source, and source sense/synset identity. Primary-sense selection deterministically prefers a
non-obsolete Wiktionary sense with a sense-compatible Russian translation; unrelated POS or
WordNet synsets are never collapsed. WordNet relations require matching POS and definition overlap.

Kaikki translations come from entry-level `translations`. Russian text is accepted when its sense
label reliably overlaps the selected English gloss. The fallback accepts one unlabeled Russian
translation only for a single-sense entry; ambiguity leaves `translation_ru` empty. Multi-word
entries are limited to a candidate set prepared before streaming from curated seeds or reviewed
evidence. Arbitrary Wiktionary multi-word entries are not ingested.

The builder reports seed, definition, Russian translation, example, and learner-ready coverage
separately and fails below 3,000 learner-ready records. Legacy references are preserved through
`legacy_id_map.json`; valid unmatched records become Alua-authored canonical records and rejected
records have an explicit reason.
