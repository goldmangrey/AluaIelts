# Listening dataset preparation — Stage 1

Offline import of the **new** `~/Desktop/ListTest` collection. No application,
API, migrations, authentication, audio, network fetches, SSH or deployment.
Only the Python dependency installation needs package registry access.

```sh
uv venv /tmp/alua-listening-stage1-env
uv pip install --python /tmp/alua-listening-stage1-env/bin/python -r backend/scripts/listening_dataset/requirements.txt
/tmp/alua-listening-stage1-env/bin/python backend/scripts/listening_dataset/importer.py
/tmp/alua-listening-stage1-env/bin/python backend/scripts/listening_dataset/validator.py --verify-input /Users/yeskendir/Desktop/ListTest
/tmp/alua-listening-stage1-env/bin/python -m unittest discover -s backend/scripts/listening_dataset -p 'test_*.py' -v
/tmp/alua-listening-stage1-env/bin/python backend/scripts/listening_dataset/report.py
```

Run from repository root. `importer.py --input PATH --output PATH --pdf-root PATH`
allows a different source location. Defaults discover the original project PDFs
under `ieltsbooks` recursively. Originals are read only. Do not pass a production
content directory as output.

`validator.py` defaults to checking **consistency of a partially recovered
collection**, not publishing clearance. Every missing/blocked question must have
an addressed QA exception. For the full editorial gate use:

```sh
/tmp/alua-listening-stage1-env/bin/python backend/scripts/listening_dataset/validator.py --require-ready
```

That command intentionally returns **1** until all 72 tests have complete,
renderable, independently source-verified content and verified official keys.
No audio condition is part of Stage 1. Inspect `qa/validation.json`,
`qa/positions.csv` and `qa/exams/*.json` for separate counts and precise issues.
CSV rows for missing expected numbers are audit records, never question objects.

## Contracts and sources

- `schema.py` emits the two closed JSON Schema contracts into `schemas/`.
- `exams/*.json` is the public content projection. Actual prompts, exact options,
  source-line spans, blank tokens, fields and visual references are retained.
- `keys/*.json` is private, including original notation and unordered slot groups.
  Parentheses and composite single-position answers need source-aware grading in
  Stage 2; the importer does not invent spelling variants or a scoring engine.
- `assets/public` contains task/source images. `assets/private` contains official
  key evidence. **Never expose the dataset root, keys, qa or private assets as a
  public static directory.**
- `source_reviews.json` is an explicit, source-hash-pinned editorial change set.
  Add evidence only after viewing the original page. Supplied README/manifest
  assertions and successful JSON parsing do not confer verification.
- Cambridge 04 Test 1 Q34 is explicitly anchored to the recovered original scan, page 12, which prints 34. The defective retyped page printed 43.
- `sources/answer_keys_04_18.txt` is the supplied web compilation, not a publisher original. Its 160 Cambridge 04 keys fill empty slots only and remain unverified. Cambridge 12 ordinals map to printed Tests 5–8.
- `sources/*.png` contains three targeted recovered task pages; URLs and PDF hashes are recorded in `source_reviews.json`. Cambridge 14 Test 3 remains preliminary because its readable replacement is a secondary reproduction.
- Cambridge 19/21 key pages were visually cross-checked against the hash-pinned local PDFs (320 positions); only Test 1 in each book also received a complete question/material review.
- Cambridge 12 preserves printed Tests **5–8** with ordinals **1–4**.
- Damaged supplied image `Cambridge 13 / PDF_036.png` is recovered by rendering
  only that page from the original PDF. No OCR command is used.

Duplicate root/Complete TXT copies are compared by SHA-256 and not counted as
extra tests. Images are deduplicated by bytes, with real dimensions and all source
aliases/associations retained. The importer supports the actual case variants and
nested directories by recursive file discovery.

The importer stages output, validates it, then replaces the target on the same
filesystem. Previous changed documents, schemas and provenance are archived under
`qa/history/<previous-manifest-sha256>/`; old content-addressed image bytes remain.
A different existing dataset producer is refused. Same inputs and review records
produce the same output bytes and do not append a revision. Modification of pinned
sources requires explicit re-review, rather than silently inheriting approval.

## Reviewed visual materials (Listening visual repair Stage 1)

`web/src/features/listening/visual-materials.json` is the single editorial registry
of public, content-addressed materials, question applicability, explicit display
order and confirmed alternatives. The importer uses it to scope image bindings;
the frontend also uses it for recognized immutable older snapshots. Unknown image
bytes require review rather than inheriting authority from a filename. Complete
crop alternatives may be preferred; full pages retain unique text/instructions.

To update an existing **local** dataset without re-importing questions or keys:

```sh
/tmp/alua-listening-stage1-env/bin/python backend/scripts/listening_dataset/visual_materials.py --apply backend/app/content/listening_v1
node web/scripts/check-listening-visuals.mjs
```

The application adds optional `Part.visual_materials` and scopes existing image
references. It retains all public bytes and allowlists. A generated byte-identical
copy under `qa/visual_materials.json` and the manifest checksum allow standalone
backend validation; edit the editorial input, never this packaged copy. Physical
crop repairs remain separate. Full browser QA is a separate release gate.

The future `Part.audio_mapping_key` contains only Book + printed Test + ordinal +
Part identity. No audio filename, duration, checksum or timestamp is inferred.
