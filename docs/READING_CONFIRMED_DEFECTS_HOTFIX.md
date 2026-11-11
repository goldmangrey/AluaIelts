# ALUA READING HOTFIX RESULT

**41/41 FIXED_VERIFIED · BLOCKED 0 · Local targeted hotfix: GO.**

Implemented only the 41 CORRUPTED findings from V1. The two SOURCE_AMBIGUITY findings, five UNRESOLVED questions and 2,343 unconfirmed candidates were not repaired or re-audited. V1 artifacts remain unchanged. This result does not certify the rest of the Reading library.

## Changes

- Six canonical exam files: C06 T1, C07 T1, C07 T4, C14 T2, C16 T2, C16 T3. Fifteen source-bound passage/group overlays cover exactly 41 original issue IDs.
- Restored summaries, instructions, repeated prompt/context fields, word limits, options/allowed values and numbered inline blanks. Corrected source-confirmed passage titles, punctuation, footnote and paragraph joins.
- Restored 34 missing option labels across five banks and 23 missing inline positions; verified 32 total inline positions across seven affected summary groups.
- Fixed 11 erroneous single-select questions in C14 T2 and C16 T3 back to one-word text fields. Restored 13 source-letter answers as selectors in C06 T1/C07 T1/C07 T4. Total: 24 input-type field changes; IDs/numbers unchanged.
- C07 T1 Q16 now offers v, corresponding to the unchanged original key. Q19/Q20 are Paragraph G/H. The new crop includes all of Q20; the original image ID/path/bytes remain available for frozen attempts.
- The renderer suppresses duplicate title headings regardless of case, and removes only an exact duplicate numbered group heading already supplied by its section. Passage and question wording remain visible; no design or layout redesign.

## Root-cause protection and reproduction

`confirmed_hotfixes.json` binds each repair to original PDF/TXT hashes and reviewed evidence, accepts only explicit known target fingerprints, and validates the exact repaired output. Changes to question IDs/numbers are rejected. Input-type transitions are explicitly allowlisted. The overlays run after existing repairs in normal enrichment, so an ordinary import cannot silently restore the old corrupted fields.

Parser regressions cover A-team/A-major-reason prose, column labels including C_, Roman i–v, and numbered dotted/underscore blanks. Automatic cropping fails closed when a recognized final question lies below its inferred footer; the confirmed Q20 fix uses a hash-bound reviewed crop. Existing unmodified image IDs/bytes are preserved.

Only six tests were replayed in temporary output to check import persistence; no complete dataset reimport was run. Apply is idempotent (second application writes zero exam files):

```sh
backend/.venv/bin/python backend/scripts/reading_dataset/apply_confirmed_hotfix.py
backend/.venv/bin/python backend/scripts/reading_dataset/apply_confirmed_hotfix.py --apply
```

## Answer safety

- 72/72 answer-key files unchanged byte for byte. No key changes proposed or applied. Stable 40 question IDs/numbers in each of the six exams.
- Grading, Atomic Submit, idempotency, deadlines, IndexedDB drafts, auth and API contracts unchanged. Historical snapshots/answers/results are not migrated. The catalog adds only validated retained-asset lookup for old snapshots.
- Compatibility tests exercise representative historical snapshots for all six exams, including former input types and the original crop asset; new attempts do not modify those snapshots or stored answers/results.
- Baseline gate: 365 protected files checked; 15 explicitly intended changes, 350 unchanged, zero unexpected changes. All 66 other exams, 72 keys and 36 source files unchanged. Listening was not modified during this task.

## Targeted QA

| Gate | Result |
|---|---|
| 41 original issue-ID regressions | PASS |
| Backend Reading/hotfix/release suite | 87 PASS |
| Real local API + disposable PostgreSQL, six perfect Atomic Submits | PASS; 40/40 each |
| Historic snapshot/result/asset preservation, six exams | PASS |
| Temporary targeted import replay, six exams | PASS |
| Exam → Finish → Results → Review | PASS; 12 cases |
| Chromium desktop 1366×768 / WebKit mobile 390×844 | PASS, all six tests each |
| Restored options selectable, inline fields unique, correct input types, Review disabled | PASS |
| Source crop Q20, image-cache return, no horizontal overflow | PASS |
| TypeScript / ESLint / Ruff / production build | PASS |
| Fast structural/hash gate (not a source audit) | PASS |

Browser tests use unchanged production pages, the real Next proxy and real local FastAPI. Only the disposable app's browser sign-in identity is stubbed; API routes are not mocked. No production database or real attempts are used. Each browser record includes the exact canonical content hash.

## All 41 original issues

| Original issue ID | Category | Target | Result |
|---|---|---|---|
| RCF1-02B70C3EF7E7 | WRONG_MISSING_OPTIONS | cambridge-06-test-01-p-2-g-23-26 | FIXED_VERIFIED |
| RCF1-0955C13AED76 | WRONG_MISSING_OPTIONS | cambridge-07-test-04-p-3-g-30-34 | FIXED_VERIFIED |
| RCF1-0C06D02228E8 | CHANGED_PUNCTUATION | cambridge-07-test-01-p-1 | FIXED_VERIFIED |
| RCF1-1124A49FF103 | OCR_ARTIFACT | cambridge-07-test-01-p-3-g-37-40 | FIXED_VERIFIED |
| RCF1-172506EE5BCB | CHANGED_WORDING | cambridge-07-test-01-p-3-g-27-30 | FIXED_VERIFIED |
| RCF1-17A052135363 | CHANGED_WORDING | cambridge-07-test-01-p-1 | FIXED_VERIFIED |
| RCF1-1BA74340B43E | CHANGED_WORDING | cambridge-07-test-01-p-3-g-37-40 | FIXED_VERIFIED |
| RCF1-1E4179966DFD | CHANGED_WORDING | cambridge-07-test-01-p-3-g-27-30 | FIXED_VERIFIED |
| RCF1-1E736A3417C1 | OCR_ARTIFACT | cambridge-07-test-01-p-2 | FIXED_VERIFIED |
| RCF1-28CE7C79B031 | WRONG_INPUT_TYPE | cambridge-16-test-03-p-2-g-20-22 | FIXED_VERIFIED |
| RCF1-2AD9ABA7475B | WRONG_MISSING_OPTIONS | cambridge-16-test-02-p-2-g-17-20 | FIXED_VERIFIED |
| RCF1-2CC9ABD3BAC4 | CHANGED_WORDING | cambridge-07-test-01-p-2-g-21-26 | FIXED_VERIFIED |
| RCF1-3A03FFF3B8EB | MISSING_CONTENT | cambridge-07-test-01-p-2-g-14-20 | FIXED_VERIFIED |
| RCF1-4187C52CBDB0 | CHANGED_WORDING | cambridge-07-test-01-p-1-g-01-05 | FIXED_VERIFIED |
| RCF1-4461BA121C86 | OCR_ARTIFACT | cambridge-06-test-01-p-2-g-23-26 | FIXED_VERIFIED |
| RCF1-507F15EEAB8A | MISSING_CONTENT | cambridge-06-test-01-p-2-g-23-26 | FIXED_VERIFIED |
| RCF1-5B0763E3704B | STRUCTURAL_RENDERING | cambridge-07-test-01-p-3 | FIXED_VERIFIED |
| RCF1-665D1C364C75 | CHANGED_WORDING | cambridge-07-test-01-p-3-g-31-36 | FIXED_VERIFIED |
| RCF1-6BD269A17EDC | INCORRECT_BLANKS | cambridge-07-test-01-p-3-g-37-40 | FIXED_VERIFIED |
| RCF1-73F41866BDDF | CHANGED_PUNCTUATION | cambridge-14-test-02-p-2-g-19-26 | FIXED_VERIFIED |
| RCF1-74AB88794267 | INCORRECT_BLANKS | cambridge-06-test-01-p-2-g-23-26 | FIXED_VERIFIED |
| RCF1-85063C0DDF2B | WRONG_MISSING_OPTIONS | cambridge-07-test-01-p-3-g-37-40 | FIXED_VERIFIED |
| RCF1-868BD867D31B | OCR_ARTIFACT | cambridge-07-test-04-p-3-g-30-34 | FIXED_VERIFIED |
| RCF1-985B8844C1C1 | KEY_OPTION_BINDING | cambridge-07-test-01-p-2-g-14-20 | FIXED_VERIFIED |
| RCF1-9A85D18E2721 | OCR_ARTIFACT | cambridge-16-test-02-p-2-g-17-20 | FIXED_VERIFIED |
| RCF1-A55663FA8399 | CHANGED_WORDING | cambridge-14-test-02-p-2-g-19-26 | FIXED_VERIFIED |
| RCF1-AF84CF92A53A | INCORRECT_BLANKS | cambridge-07-test-04-p-3-g-30-34 | FIXED_VERIFIED |
| RCF1-BDB9C38AB823 | OCR_ARTIFACT | cambridge-16-test-03-p-2-g-20-22 | FIXED_VERIFIED |
| RCF1-BEAFF5DED815 | CHANGED_WORDING | cambridge-07-test-01-p-2 | FIXED_VERIFIED |
| RCF1-BFBD4D1320D9 | CHANGED_PUNCTUATION | cambridge-07-test-01-p-1 | FIXED_VERIFIED |
| RCF1-C6F312B02BA3 | STRUCTURAL_RENDERING | cambridge-07-test-01-p-3 | FIXED_VERIFIED |
| RCF1-CBB0CF59E6E4 | STRUCTURAL_RENDERING | cambridge-07-test-01-p-2 | FIXED_VERIFIED |
| RCF1-D2733CD9BC3E | STRUCTURAL_RENDERING | cambridge-07-test-01-p-1 | FIXED_VERIFIED |
| RCF1-D75E9D33A63B | OCR_ARTIFACT | cambridge-07-test-01-p-1-g-06-09 | FIXED_VERIFIED |
| RCF1-D918D2FDC204 | MISSING_CONTENT | cambridge-07-test-01-p-2-g-14-20 | FIXED_VERIFIED |
| RCF1-D93F3E5B82AC | INCORRECT_BLANKS | cambridge-07-test-01-p-1-g-06-09 | FIXED_VERIFIED |
| RCF1-DEBFC960F33E | OCR_ARTIFACT | cambridge-07-test-01-p-1 | FIXED_VERIFIED |
| RCF1-E713EE3A4843 | WRONG_MISSING_OPTIONS | cambridge-07-test-01-p-2-g-14-20 | FIXED_VERIFIED |
| RCF1-EBD22B88D632 | INCORRECT_BLANKS | cambridge-16-test-03-p-2-g-20-22 | FIXED_VERIFIED |
| RCF1-ED9D600CE291 | INCORRECT_BLANKS | cambridge-16-test-02-p-2-g-17-20 | FIXED_VERIFIED |
| RCF1-F36111F42714 | INVENTED_OPTIONS | cambridge-16-test-03-p-2-g-20-22 | FIXED_VERIFIED |

Distinct issue categories: CHANGED_PUNCTUATION=3, CHANGED_WORDING=9, INCORRECT_BLANKS=6, INVENTED_OPTIONS=1, KEY_OPTION_BINDING=1, MISSING_CONTENT=3, OCR_ARTIFACT=8, STRUCTURAL_RENDERING=4, WRONG_INPUT_TYPE=1, WRONG_MISSING_OPTIONS=5.

## Changed files

- `backend/app/content/reading_v1/assets/cambridge_07/cambridge-07-test-01-p-2-g-14-20-pdf-026-diagram-fidelity-v1.png`
- `backend/app/content/reading_v1/corrections.jsonl`
- `backend/app/content/reading_v1/exams/cambridge_06/test_01.json`
- `backend/app/content/reading_v1/exams/cambridge_07/test_01.json`
- `backend/app/content/reading_v1/exams/cambridge_07/test_04.json`
- `backend/app/content/reading_v1/exams/cambridge_14/test_02.json`
- `backend/app/content/reading_v1/exams/cambridge_16/test_02.json`
- `backend/app/content/reading_v1/exams/cambridge_16/test_03.json`
- `backend/app/content/reading_v1/manifest.json`
- `backend/app/modules/reading/catalog.py`
- `backend/scripts/reading_dataset/apply_confirmed_hotfix.py`
- `backend/scripts/reading_dataset/confirmed_hotfixes.json`
- `backend/scripts/reading_dataset/confirmed_hotfixes.py`
- `backend/scripts/reading_dataset/engine.py`
- `backend/scripts/reading_dataset/enrich.py`
- `backend/scripts/reading_dataset/pdf_support.py`
- `backend/scripts/reading_dataset/source_reviews.json`
- `backend/scripts/reading_dataset/validator.py`
- `backend/tests/test_reading.py`
- `backend/tests/test_reading_confirmed_hotfix.py`
- `docs/READING_CONFIRMED_DEFECTS_HOTFIX.md`
- `docs/reading-confirmed-defects-hotfix.json`
- `web/scripts/test-reading-confirmed-hotfix.mjs`
- `web/src/features/reading/exam/passage-pane.tsx`
- `web/src/features/reading/exam/question-renderer.tsx`

Additional evidence is under `docs/reading-confirmed-defects-hotfix/`: 12 screenshots, browser QA, protected-file safety, control deltas, JUnit results and this reproducible report builder.

## Evidence

- [Machine report](reading-confirmed-defects-hotfix.json) — exactly 41 original IDs, source evidence, repaired fields and per-issue QA references.
- [Browser QA](reading-confirmed-defects-hotfix/browser-qa.json), [safety](reading-confirmed-defects-hotfix/safety.json), [control changes](reading-confirmed-defects-hotfix/change-summary.json).

**GO is limited to this confirmed-defect hotfix. Broader Reading fidelity remains uncertified; existing needs_review/blocked release statuses were preserved.**
