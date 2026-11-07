# Listening Source Fidelity V2 — implementation and persistent handoff

Local implementation, 7 November 2026. No commit, push, deployment, Oracle access or production data operations were performed. The pre-existing working tree contains earlier reliability, Player V4 and Compact V5 work; those unrelated changes must not be bundled blindly.

## Final-four follow-up — 7 November 2026
Three remaining cases now have pinned original-page proof: C04 T1 P4 and C06 T2 P1 match retained recovered pixels exactly; C07 T4 P1 uses a new clean original page. Current strict fidelity is **287/288** (258 VERIFIED, 29 REPAIRED_VERIFIED). C14 T3 P1 remains UNRESOLVED: the retained complete fallback is a retype, and an undamaged original layout was not obtained. The earlier 284/288 result below is the historical baseline. A partial production release with this explicit exception is now authorized by the user. See [final release handoff](ALUA_FINAL_SOURCE_RELEASE.md) for deployment, regression and rollback evidence. No claim of 288/288 original-layout verification is made.

## Result and release decision

**NO-GO for a fully verified visual release.** Presentation repairs are implemented and tested. Source fidelity is confirmed for **284/288 Parts**: 258 VERIFIED and 26 REPAIRED_VERIFIED. Three Parts remain UNRESOLVED and one BLOCKED because the available originals cannot establish an undamaged, exact source. These exceptions are retained visibly in the reports, not treated as successful repairs.

- 72 tests / 288 Parts / 568 groups; 496 canonical source images after repair (464 before).
- One additional physical-page order inversion repaired: C20 T3 P2, PDF pages 78,79,81,80 → 78,79,80,81.
- Seven Parts had focus-dependent extracted text (20 active-group states; 17 distinct text groups could disappear). The unified source flow no longer depends on focus.
- 32 missing or partial **original-page contexts** restored; two additional clipped source pages replaced with complete originals. These counts overlap affected Parts and must not be added to the composition count as distinct Parts.
- Two additional pages replace an already complete, single-group text source in C04 T2 P2. They are enhancements, not missing-content defects.
- 36 new full-page PNGs, content-addressed and hash-pinned. No original image was overwritten or deleted. All 45 Stage 2 repaired canonical assets remain selected.
- 27 Parts have changed canonical metadata; 26 are classified repaired, C04 T2 P2 is classified VERIFIED/enhanced. Thirteen exam JSON files changed, exclusively source/image metadata and allowlists. Source question semantics and all private key files are unchanged.
- Two C10 metadata-only bindings corrected from Q10 to Q7–10 (T1 P1, PDF 3) and Q30 to Q25–30 (T4 P3, PDF 77). Both pages already displayed completely; these are not counted as lost page contexts.
- Current structural missing pages, reviewed duplicate pairs, page-order inversions and wrong-Part associations: **0**. This does not erase the four semantic exceptions.

## Confirmed causes and implemented flow

The old source pane combined `visibleSourceMaterial(...all visible groups).assets` with `sourceMaterial(...active group).lines`, rendering every image first and only the focused group's extracted text afterward. A group with any broad image binding also suppressed its text, even when that image did not contain the group's questions. A validator checking asset existence/group coverage could therefore pass while whole page contexts or inactive-group text were absent.

Concrete examples:

- C04 T3 P2: the sole page was PDF 67 (Q15–20), broadly labelled Q11–20. PDF 66 (Q11–14) was missing from the source pane. Both are now selected in original order.
- C04 T3 P3: both Q21–25 and Q26–30 were text-backed, but only the active group appeared. Original pages 68–70 are now present, including the continuation of Q25 option C on page 69 and Q30 options on page 70.
- C04 T3 P4: the Q39–40 continuation on PDF 73 was absent; table instructions/pages 71–72 must remain together, not be replaced by the final page.
- C15: several ranges retained only isolated map crops or one page while the adjacent instructions/question page was absent. Explicit local-PDF boundaries are now recorded for all sixteen Parts.
- C20 T3 P2: Q17–20 map page 80 followed its continuation page 81 due to old range/order metadata. Physical PDF sequence now determines display order.
- C07 T3 P2 PDF 63 cut the ITINERARY heading; C07 T4 P4 PDF 92 clipped the upper frame. Both use new, complete page renders.

New flow:

`pinned local PDF → deterministic full-page recipe → content-addressed asset + allowlist → visual-materials registry → per-group sourceMaterial → visibleSourceMaterial ordered SourceSegment[] → WorkspaceQuestions source pane`

`SourceSegment` is presentation-only: stable ID, Part, question range, explicit order, image/text/options kind and PDF provenance. Page order is editorial physical-page order, **not filename order or question-range sorting alone**. Continuations can intentionally overlap question ranges. All visible groups contribute to the single stream; shared images are deduplicated through existing canonical/alternative families. Text/options fallbacks retain group order and instructions, and are not appended as a separate active-group list. Text fallback is explicitly unverified as a substitute for original geometry.

The source pane's identity uses Part/segment/group IDs, not current question focus. No forced source scrolling was introduced. Existing cache, independently scrolling columns, scroll restoration, V5 layout and player are reused.

## Implementation map

| File | Function / relevant lines | Change and regression protection |
| --- | --- | --- |
| `web/src/features/listening/models.ts` | `SourceSegment`, line 16 | Presentation source model; answer schema unchanged. |
| `web/src/features/listening/source-material.ts` | `sourceMaterial`, line 11; `visibleSourceMaterial`, line 57 | Resolve all suitable reviewed pages, retain allowlist boundaries, emit one ordered stream with text/options fallbacks; mixed/text-only historical model regressions in the source checker. |
| `web/src/features/listening/workspace-questions.tsx` | material selection line 21, materialKey line 40, renderer line 68 | Render every segment in order; remove active-group source text selection. Existing scroll/cache remains. |
| `web/src/features/listening/visual-materials.json` | `parts.*.materials`, `source_fidelity` | Correct physical-page ranges/order, canonical selections and explicit PDF proof/exceptions. |
| `backend/scripts/listening_dataset/source_fidelity.py` + `.json` | `add_source_fidelity_assets`, `apply_current` | 36 reproducible full-page recipes: original pixels, 250 DPI, 12px white safety margin. No OCR/AI replacement text. |
| `backend/scripts/listening_dataset/importer.py` | source asset registration, line 1146 | Normal import invokes the same recipes; targeted update avoids reparsing questions/keys. |
| `backend/scripts/listening_dataset/visual_materials.py` | `apply_visual_materials`, line 25 | Apply explicitly reviewed PDF boundaries only when requested; preserve normal canonical/alternative behavior. |
| `backend/app/modules/listening/source_materials.py` | `semantic_source`, `enrich_sources` | Read-only visual enrichment for semantically identical old immutable snapshots. |
| `backend/app/modules/listening/catalog.py` | `public_exam`, line 212; `asset`, line 230 | Serve approved current canonical images to compatible old attempts without rewriting stored snapshots/answers/results. |
| `backend/tests/test_listening_source_fidelity.py` | four tests | Compatibility guard, private/other-exam rejection, real disposable-PG read projection and asset GET; persisted snapshot/answers/state/version/status/result unchanged. |
| `backend/scripts/listening_dataset/test_source_fidelity.py` | three tests | Regenerate all 36 assets byte-for-byte through normal Assets registration; reject wrong PDF; all 72 metadata projections idempotent. |
| `backend/scripts/listening_dataset/test_visual_materials.py` | continuation regression | Q33–37 keeps first two pages; Q39 obtains the last page. |
| `web/scripts/check-listening-source-fidelity.mjs` | component + browser modes | Actual resolver; old mixed/text snapshots; all 288 Parts in real UI, both modes/engines/viewports. |
| `backend/scripts/listening_dataset/report_source_fidelity.py` | `build` | Rebuild machine report and complete original-versus-selected contact sheet. |

Backend changes are necessary because old attempt snapshots do not allow newly introduced image IDs. Frontend-only changes would leave old attempts unable to request the restored pages. The enrichment checks exact non-visual question/instruction/content equality and same exam, then adds only current canonical public assets. Existing attempt ownership, path confinement and hash checks still apply. It performs no persistence mutation. **Unknown historical question revisions are retained and are not certified as verified.** No submit/sync/grading/auth contract changed in this task.

## Evidence, methods and limits

The 18 local PDFs in `ieltsbooks/` are pinned by SHA-256. No Cambridge PDF was downloaded. All Part page sequences are present in `report.json`, including original-page links, group/range metadata, actual ordered segment IDs and proof methods. Comparison page numbers for recovered assets are local-PDF comparison locations; they are not a claim that the recovered image was derived from that local file. Its original source/recovery metadata remains intact.

Verification combined full-page raster comparison, original page boundaries, continuation inspection, prior hash-pinned Stage 2 pixel reviews, and visual comparisons of alternate scans/crops. Of 464 initial canonical images, 320 had strong normalized full-page pixel correlation; 70 lower-correlation page pairs were visually checked in nine comparison sheets. Additional non-Stage-2 crop/alternate sheets and low-correlation exceptions were inspected. Correlation and OCR were not used alone to certify completeness or rewrite text. OCR was used only to locate/index original material.

The resulting 496 canonical image/page slots cover the reviewed Part PDF pages once, in physical sequence. This is page/layout/context verification, **not an independent manual transcription and proofreading of every glyph on every page**. Existing source damage remains an exception. The technical dataset validator still retains legacy editorial-readiness warnings for 66 exams; technical integrity PASS is not a blanket editorial/grading readiness assertion.

Browser evidence uses the actual Listening Exam/Review components and real image pixels in an isolated local fixture, with synthetic local identity/attempt APIs and tiny audio for this particular source suite. It is not a production smoke test or backend persistence proof. Atomic Submit and real-MP3 player have separate regression suites.

- All 288 Parts × Chromium/WebKit × desktop/mobile × Exam/Review = **2,304 PASS** source-mode cases.
- Checks: exact DOM segment order, all expected images decoded, no source errors/loading residue, aspect ratio and no cover clipping, desktop source-left/questions-right, first/last-question focus invariance, source scroll retained, no horizontal overflow.
- Each exam also returns between already prepared Parts and asserts zero extra image GETs. No new image LRU cache implementation was introduced.
- Component audit covers 568 groups; all source-model groups are independent of active focus. Browser focus probes first/last questions per Part, not every possible user interaction.
- The long run was resumed after a WebKit stability timeout. Resume checks identical source files and canonical material arrays before reusing complete four-Part exam sets. Final artifact has no errors/unverified cases. An earlier mobile harness compared visibility-sensitive `innerText`; it was corrected to compare stable source `textContent`.
- Atomic Submit browser test initially failed after successful server assertions because a test observer was discarded by reload. It now installs across navigation. No runtime save/submit logic was changed.

## Exact remaining exceptions

| Status | Part / range | Available source and reason | Safe next step |
| --- | --- | --- | --- |
| UNRESOLVED | C04 T1 P4 / Q31–40 | Local PDF physical page 8 differs in wording/numbering from the previously recovered source (origin page 12 in its source metadata). Clean recovered full page retained. | Obtain the already referenced secondary PDF/authoritative matching scan and reconcile exact wording; do not infer it from OCR or answers. |
| UNRESOLVED | C06 T2 P1 / Q1–10 | Local PDF 35 has an unreadable table heading. Clean recovered page from a different pinned source PDF page 29 retained; that secondary PDF is not available locally. | Restore the exact referenced secondary source locally and confirm full page. Do not replace the clean recovery with damaged local pixels. |
| UNRESOLVED | C14 T3 P1 / Q1–10 | Local PDF 53 is largely blank/damaged. Recovered Flanders Conference Hotel source (origin PDF page 1) retains fields, but exact fields cannot be independently compared locally. | Supply the existing referenced full secondary source or a verified clean original; retain current recovery meanwhile. |
| BLOCKED | C07 T4 P1 / Q1–10, C014 | AND/OR instruction pixels are damaged in the fallback; the local PDF 85 watermark also crosses the word-limit line. This is an instruction-fidelity blocker for this test. | Obtain a clean original instruction/page and replace from its pixels. No invented letters, no silent test disable. |

C028 / C06 T3 P3 remains the earlier **full original-page fallback**; the uncertain crop is not selected. Its complete source is retained. The four exceptions above do not represent newly hidden content.

## Reproduction and final gates

Run from repository root. Use the existing image tooling environment with pinned PyMuPDF/Pillow and the project's backend environment; do not install a second processing stack.

```sh
node web/scripts/check-listening-source-fidelity.mjs
node web/scripts/check-listening-source-fidelity.mjs --browser
node web/scripts/audit-listening-part-coverage.mjs --assert-complete
PYTHONPATH=backend/scripts/listening_dataset /tmp/alua-stage2-venv/bin/python -m unittest test_source_fidelity test_visual_materials test_image_repairs -q
/tmp/alua-stage2-venv/bin/python backend/scripts/listening_dataset/validator.py --report docs/listening-source-fidelity-v2/dataset-validation.json
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_listening.py backend/tests/test_listening_source_fidelity.py -q
ALUA_RUN_LISTENING_BROWSER=1 ALUA_LISTENING_TEST_GREP='atomic hotfix' PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_listening_browser.py -q
node web/scripts/check-listening-navigation.mjs
node web/scripts/check-listening-player-v4.mjs
node web/scripts/check-listening-compact.mjs
PYTHONPATH=backend /tmp/alua-stage2-venv/bin/python backend/scripts/listening_dataset/report_source_fidelity.py
```

The `/tmp/alua-stage2-venv` path is this machine's already available image environment, not a repository dependency or production requirement. See existing dataset requirements for pinned tooling if reproducing elsewhere. The optional report `--before` argument seeds the persistent `protected-baseline.json` from the safely retained pre-repair snapshot. Future runs verify question/key/old-image hashes directly against that repository baseline; no temporary directory is needed. Do not use `--baseline` to overwrite historical evidence after applying repairs.

Targeted regeneration, if needed (does not parse questions/keys):

```sh
/tmp/alua-stage2-venv/bin/python backend/scripts/listening_dataset/source_fidelity.py --apply-current backend/app/content/listening_v1 --pdf-root ieltsbooks
```

After editing any importer/review generator file, refresh packaged registry and generator hashes with the existing `visual_materials.py --apply backend/app/content/listening_v1`, then rerun validators. No full 72-exam import is needed for this repair. Normal importer wiring uses the same page renderer and canonical registry; the validation here demonstrates deterministic asset regeneration and metadata replay, **not a new full source reimport**.

## Saved artifacts and future release

- `docs/listening-source-fidelity-v2/report.json`: per-Part classification, groups/ranges, ordered source segments, PDF hashes/pages, individual new asset recipes, browser scope and protected-content comparison.
- `docs/listening-source-fidelity-v2/index.html`: all 288 Parts, original PDF thumbnails versus actual selected flow; `thumbs/` contains bounded-size previews.
- `docs/listening-source-fidelity-v2/browser-qa.json`: all 2,304 source UI cases.
- `docs/listening-source-fidelity-v2/component-qa.json` and `baseline.json`: current model versus original active-text failure states.
- `docs/listening-source-fidelity-v2/original-pixel-comparison.json`, `visual-review.json`, `comparisons/`: original raster and explicit visual-review evidence. Thumbnails/contact sheets are not replacements for Cambridge assets.
- Twelve curated desktop/mobile browser screenshots cover the six named regression examples. Audio in source-suite screenshots is a synthetic one-second fixture; the real waveform/player regression is separate.

A future approved release must ship the **new public assets first**, then compatible dataset/manifest/registry and the source-only backend enrichment plus frontend source renderer. Keep old assets and snapshot rows. No migrations are needed. Do not deploy this working tree wholesale: it includes earlier unrelated local work. Resolve or explicitly approve the four source exceptions before describing the whole library as fully source-verified. No deployment is authorized by the current task.

## Final QA results

| Gate | Result / scope |
| --- | --- |
| Source component coverage | PASS: 72 tests, 288 Parts, 568 groups; missing ranges/groups/assets 0. |
| Original source fidelity | 284 confirmed, including 26 repaired; 3 UNRESOLVED, 1 BLOCKED. Full-library gate NO-GO. |
| Full browser source QA | PASS: 2,304 Part-mode cases, Chromium/WebKit, desktop/mobile, Exam/Review. |
| Post-C10 binding browser QA | PASS: 64 additional cases over both complete C10 tests. Same image IDs/content/order; corrected ranges. |
| Stage 1/2 coverage audit | PASS: missing render states/Parts, duplicates, order inversions, wrong Part all 0. |
| Deterministic original pages | PASS: all 36 regenerated byte-for-byte; wrong PDF rejected; all 72 metadata projections idempotent. |
| Existing Stage 2 | PASS: all 45 repaired assets/hashes/canonical choices/full-page alternatives retained. |
| Offline image/metadata tests | PASS: 11 tests; final post-C10 metadata/Stage2 replay 9 tests. |
| Backend contract/source projection | PASS: 17 tests against disposable local PostgreSQL, including 4 source compatibility tests. |
| Real backend Atomic Submit | PASS: 12 browser scenarios across 6 projects; 15/15 and 40/40 accepted server answers, 422 recovery/reload/edit/retry and Review. |
| Navigation/cache | PASS: 8 Chromium/WebKit Exam/Review desktop/mobile cases; duplicate GETs on prepared return 0; separate scroll restored. |
| Player V4 | PASS: 288 real-audio waveform mappings/hash checks and 8 real-MP3 cases including progress, reload, independent navigation/audio, natural end, AI Play/Loop. AI responses are local fixtures. |
| Compact V5 | PASS: 10 engine/viewport cases at 1440×900, 1366×768, 1280×720, 390×844, 375×667; desktop player108px, mobile102px; footer0; no overflow. |
| TypeScript / ESLint / production build | PASS. |
| Ruff | PASS on changed Python source/importer/tests. |
| Dataset/schema/checksums | PASS technical integrity; legacy editorial readiness flags remain, not a blanket editorial PASS. |
| Protected content | PASS: question semantics/all keys and 703 prior asset files unchanged. |

Player regression initially reported WebKit access-control errors from image requests still in flight when its temporary page/context was destroyed. The fixture now forwards the real AbortSignal, waits for network idle before deliberate cross-exam navigation/teardown, and preserves diagnostics safely if a page is already closed. No application audio/cache code was changed. Final full eight-case real-MP3 rerun has zero errors. Instant Part navigation is tested independently without these cross-exam teardown waits.

## Exact changed Part inventory

Full question ranges, asset IDs and recipes are in each matching `report.json.parts` entry.

| Part | Original PDF pages | New pages | Classification |
| --- | --- | --- | --- |
| cambridge-04-test-01-p2 | [3, 4] | [3] | REPAIRED_VERIFIED |
| cambridge-04-test-01-p3 | [5, 6, 7] | [5, 6] | REPAIRED_VERIFIED |
| cambridge-04-test-02-p1 | [33, 34, 35] | [34, 35] | REPAIRED_VERIFIED |
| cambridge-04-test-02-p2 | [36, 37] | [36, 37] | VERIFIED |
| cambridge-04-test-02-p3 | [38, 39] | [] | REPAIRED_VERIFIED |
| cambridge-04-test-02-p4 | [40, 41, 42] | [40, 42] | REPAIRED_VERIFIED |
| cambridge-04-test-03-p1 | [64, 65] | [65] | REPAIRED_VERIFIED |
| cambridge-04-test-03-p2 | [66, 67] | [66] | REPAIRED_VERIFIED |
| cambridge-04-test-03-p3 | [68, 69, 70] | [68, 69, 70] | REPAIRED_VERIFIED |
| cambridge-04-test-03-p4 | [71, 72, 73] | [73] | REPAIRED_VERIFIED |
| cambridge-04-test-04-p2 | [100, 101] | [100] | REPAIRED_VERIFIED |
| cambridge-04-test-04-p3 | [102, 103] | [103] | REPAIRED_VERIFIED |
| cambridge-04-test-04-p4 | [104, 105, 106] | [105, 106] | REPAIRED_VERIFIED |
| cambridge-07-test-03-p2 | [62, 63] | [63] | REPAIRED_VERIFIED |
| cambridge-07-test-04-p4 | [91, 92] | [92] | REPAIRED_VERIFIED |
| cambridge-10-test-01-p1 | [2, 3] | [] | REPAIRED_VERIFIED |
| cambridge-10-test-04-p3 | [76, 77] | [] | REPAIRED_VERIFIED |
| cambridge-15-test-01-p2 | [13, 14] | [13] | REPAIRED_VERIFIED |
| cambridge-15-test-01-p3 | [15, 16] | [15, 16] | REPAIRED_VERIFIED |
| cambridge-15-test-02-p2 | [34, 35] | [34, 35] | REPAIRED_VERIFIED |
| cambridge-15-test-02-p3 | [36, 37] | [36, 37] | REPAIRED_VERIFIED |
| cambridge-15-test-03-p1 | [54, 55] | [55] | REPAIRED_VERIFIED |
| cambridge-15-test-03-p2 | [56, 57] | [56, 57] | REPAIRED_VERIFIED |
| cambridge-15-test-03-p3 | [58] | [58] | REPAIRED_VERIFIED |
| cambridge-15-test-04-p2 | [77, 78] | [77, 78] | REPAIRED_VERIFIED |
| cambridge-15-test-04-p3 | [79, 80] | [79, 80] | REPAIRED_VERIFIED |
| cambridge-20-test-03-p2 | [78, 79, 80, 81] | [] | REPAIRED_VERIFIED |

Exam files changed (source metadata/allowlists only): `cambridge-04-test-01.json`, `cambridge-04-test-02.json`, `cambridge-04-test-03.json`, `cambridge-04-test-04.json`, `cambridge-07-test-03.json`, `cambridge-07-test-04.json`, `cambridge-10-test-01.json`, `cambridge-10-test-04.json`, `cambridge-15-test-01.json`, `cambridge-15-test-02.json`, `cambridge-15-test-03.json`, `cambridge-15-test-04.json`, `cambridge-20-test-03.json`.

Packaged metadata: `backend/app/content/listening_v1/qa/assets.json`, `qa/visual_materials.json`, `manifest.json`; 36 new files under `assets/public/`. Exact new paths are recipe hashes without `asset-`, followed by `.png`. Original images and keys remain unchanged. QA-only fixes also affect `web/tests/listening.spec.ts`, `web/scripts/check-listening-ui.mjs`, `web/scripts/check-listening-player-v4.mjs`. The existing coverage audit refreshed its Stage1 current-coverage JSON.

[Complete contact sheet](listening-source-fidelity-v2/index.html) · [Machine report](listening-source-fidelity-v2/report.json) · [QA summary](listening-source-fidelity-v2/qa-summary.json)
