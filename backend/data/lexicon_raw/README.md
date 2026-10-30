# Lexicon source preparation contract

Original immutable distributions live under `backend/data/lexicon_sources/` and are git-ignored.
Do not manually create normalized JSONL files. From `backend/`, run:

```shell
uv run python scripts/lexicon/prepare_sources.py
```

Expected originals:

- `ngsl/NGSL_1.2_stats.csv` — official NGSL 1.2 CSV with headword and rank columns;
- `nawl/NAWL_1.2_stats.csv` — official NAWL 1.2 CSV;
- `kaikki/kaikki.org-dictionary-English.jsonl.gz` — compressed English Kaikki/Wiktextract dump;
- `wordnet/dict/data.noun`, `data.verb`, `data.adj`, `data.adv` — Princeton WordNet database files;
- `tatoeba/sentences_eng_cc0.tsv.gz` — English CC0 export: sentence ID, language, text,
  date modified;
- optional `phrases/phrase_candidates.txt` — reviewed multi-word candidates, one per line.

Keep original license/readme files in each source directory. Add every incorporated original file
to `data/lexicon_sources/checksums.sha256` using `shasum -a 256`; preparation fails on a missing
file or checksum mismatch.

Compressed and uncompressed readers are supported, but Kaikki intentionally remains `.jsonl.gz`.
It is streamed directly and never expanded to a 20+ GB intermediate.

Preparation writes normalized staging under `data/lexicon_staging/`:

- `headwords.jsonl`
- `kaikki_senses.jsonl.gz`
- `wordnet_synsets.jsonl`
- `tatoeba_examples.jsonl`
- `curated_items.jsonl`
- `curated_relations.jsonl`
- `source_manifest.json`

Only after reviewing staging counts and licenses run:

```shell
uv run python scripts/lexicon/build_lexicon.py
```
