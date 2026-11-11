# ALUA WRITING TASK 2 — IMPLEMENTATION RESULT

11 November 2026, Asia/Almaty. **Final status: PARTIAL.**

Writing Topics, Editor, Results and the PostgreSQL workflow are implemented locally. The remaining gate is **live verification of the final feedback-quality policy**. Three real calls were used: two safely rejected responses and one native Next → Orchestrator → Cloudflare → PostgreSQL success. Content inspection of that success found generic advice about more sophisticated collocations. The final validator now rejects that advice; its tests pass, but no fourth call was made. Writing is not declared fully ready.

## A. Dataset

| Check | Result |
|---|---|
| Master records | 326 |
| READY imported | 32 |
| Pending excluded | 288 |
| Aliases excluded | 6 |
| Dataset validation | PASS |

Exactly one matching version of each requested file was found in Downloads. All 32 ready IDs exist in master and match its prompts, topics, types and requirements. All CSV columns were compared against master, including structured fields and statuses. All public prompts have the situation and complete directive, terminal punctuation and unique IDs/prompts. A legitimate 23-word prompt is retained without rewriting. Titles use existing editorial summaries. No reported dates or unverified official questions appear in the UI.

The master, CSV and provenance report are archived outside public assets/endpoints. Original Downloads files are unchanged. Checksums are in [dataset-checksums.json](writing-task2/dataset-checksums.json). Import was run repeatedly: 32 tasks, no duplicates, no attempt/result changes. Stable task content cannot silently change on reimport.

## B. Frontend

| Feature | Result |
|---|---|
| Writing topics | PASS |
| Search / topic / type / sorting | PASS |
| Essay editor | PASS |
| Autosave / reload / delayed-response race | PASS |
| Results UI / exact source highlights / Russian details | PASS with mocks; live criterion evidence passed |
| Mobile | PASS — WebKit 390×844; no horizontal overflow |

Uses Alua header, typography, colors, spacing and surfaces. Writing-scoped EN/RU/KK controls and dark-mode surfaces are included. Existing Next UI is English; no existing global locale store was found or replaced. Task 1 is honestly disabled. The home Writing card now says Task 2 / 40 minutes.

Native textarea preserves paragraphs, copy/paste and undo/redo. Saves are debounced and serialized; version checks prevent stale overwrites. Owner-scoped IndexedDB uses the existing draft storage, lease and logout cleanup as recovery alongside PostgreSQL. A conflict retains text for copying rather than replacing it. Reload before a server save can recover the local draft. A non-blocking timer never submits or clears text.

Results show a Task 2 estimate, all four criteria, source evidence, three improvements, review details, Russian explanations/translations and previous attempts. Optional style suggestions have a separate category from errors. A new attempt preserves earlier essays/results; comparison is available after two assessed attempts on a topic.

## C. Backend

| Feature | Result |
|---|---|
| Additive PostgreSQL migration | PASS — `20261111_0008` |
| Draft persistence / optimistic versions | PASS |
| Firebase auth / ownership | PASS — existing identity mapping reused |
| Assessment persistence / immutable essay snapshot | PASS |
| Idempotency / concurrent claim / repeated result | PASS |

Two new tables: `writing_tasks` and `writing_attempts`. The latter owns the immutable task snapshot, submitted essay version, assessment JSON, provider metadata and persistent assessment lease/quota. This is the minimal equivalent of separate assessment entities. The owner is the existing learner identity resolved from Firebase UID, following Reading/Listening conventions.

API under `/api/v1/writing`: published tasks, own attempts, create/reuse draft, versioned save, immutable submit. Signed server-only `assessment/claim` and `assessment/complete` endpoints also require learner authentication. Direct client-generated assessment writes fail. HMAC binds timestamp, path and body; completion must match the active lease. Assessment is revalidated in Python before saving.

Limits: 16,000 characters and 2,000 words; review requires at least 250 words. No confident underlength numerical score is generated. AI quota is persistent and owner-scoped: at most 3 generation claims per immutable attempt and 6 per hour per learner (conservatively counted). A pending claim blocks duplicate generation for 180 seconds; Orchestrator deadline is 60 seconds, browser budget 85 seconds. An unavailable result retains the submitted essay and allows bounded retry. SQL storage exceptions are sanitized to keep query parameters/essays out of error logs.

Local bridge secret is a private 0600 file under the existing local-stack state directory, created idempotently during local import. No frontend keys, production env edits or Worker secret changes.

## D. AI

| Field | Actual result |
|---|---|
| Configured primary | Groq; unavailable locally, no successful Groq inference |
| Configured fallback / actual provider | Cloudflare Workers AI |
| Real model tested | `@cf/google/gemma-4-26b-a4b-it` |
| Live assessment/provider calls | **3 total**, all Cloudflare; no fourth call |
| Validated assessment | PASS for schema/evidence/persistence in call 3; **FAIL final live quality gate** |
| Criterion scoring / backend arithmetic | PASS mechanically; expert accuracy unverified |
| Evidence validation | PASS — exact source-owned IDs → UTF-16 ranges, backend revalidation |
| Cached/repeated result | PASS in live call 3; no new model invocation |
| Expert calibration | **NOT VERIFIED** |

The existing Orchestrator V2 is reused. Only Writing routing is enabled, with Writing-specific token/deadline budgets. Groq → Cloudflare order and external provider privacy gates are unchanged. Gemini/OpenRouter were not enabled or used. A small optional success-metadata callback records the actual provider/model without trusting model claims.

The model receives the server-owned immutable prompt, requirements, essay and source candidates, never client-supplied task criteria. Student text is exclusively untrusted user data. The model selects source-owned IDs; it cannot generate accepted quotes or guessed offsets. Unknown IDs, added quote/offset fields, invalid scores, missing criteria, fake evidence, overlaps, duplicate improvements, unsupported certainty and detected generic complexity advice are rejected. There is no post-hoc repair of invented evidence.

Backend computes the equal-weight mean and rounds the *product's Task 2 estimate* to a half band, ties upward. This does not compute overall IELTS Writing, which also needs Task 1. No conservative/optimistic range or expert calibration claim is displayed.

Official references checked:

- [IELTS Academic Writing format](https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-writing).
- [British Council assessment and descriptors](https://takeielts.britishcouncil.org/results/how-is-ielts-assessed).
- [IELTS Writing resources](https://ielts.org/take-a-test/preparation-resources/writing-test-resources).
- [Official Writing Band Descriptors, May 2023](https://takeielts.britishcouncil.org/sites/default/files/%5Bdownloads%5D/ielts_writing_band_descriptors.pdf).

A valid contract does not establish the correctness of an LLM's judgement. The observed high estimate and generic advice are why final readiness is withheld. The new quality guard catches the observed wording; it is not a complete semantic verifier or a substitute for expert benchmarking.

## E. Regression and QA

| Check | Result |
|---|---|
| Reading / Reading AI | PASS |
| Listening / Listening AI | PASS |
| Listening player, loop navigation and position restore | PASS — Chromium desktop + WebKit mobile |
| Smart Translation | PASS — existing contract suite |
| Firebase auth / ownership mapping | PASS — existing backend suite |
| Local stack preserved | YES |
| Existing user data preserved | YES |

Evidence:

- Combined backend suites: **106 passed, 2 browser tests deselected** before the final quality guard; final Writing contract suite adds the two content-quality cases: **13 passed**.
- Final Orchestrator / Reading AI / Smart Translation contracts: **106 passed**.
- Writing browser runner: PASS in Chromium desktop and WebKit mobile, including real PostgreSQL draft/reload/race, search/filter/sort, locale switching, mocked provider failure/retry, exact issue selection, retake and comparison.
- Native Next live runner: one successful model request, real PostgreSQL persist and cache; preceded by two rejected model requests. Final semantic guard was added afterwards and is mock-tested only.
- Focused existing Listening browser regression: **4 passed** (AI Review/loops and temporary clip restore, both engines).
- TypeScript, full ESLint and scoped Ruff: PASS.

Two existing migration tests hard-coded the previous Alembic head. They now query the configured current head while retaining data-preservation assertions. No auth implementation or Reading/Listening contract changed.

Existing warnings: Alembic `path_separator` deprecation and the existing vocabulary model `register` field warning. No unrelated refactoring. Tests used disposable databases and copied frontends; Firebase UI auth was stubbed only in copied browser fixtures. This is not a new real Google/Firebase browser login test. The existing persistent PostgreSQL was not recreated or stopped. Backend was restarted to load new routes; the frontend process was preserved. The persistent local database contains 32 Writing tasks and zero QA-created Writing attempts.

## F. Changed files and purpose

Only this task's additions/edits are listed; the extensive pre-existing checkout changes remain intact.

| Files | Purpose |
|---|---|
| `backend/alembic/versions/20261111_0008_writing.py` | Additive tables; rollback preserves history |
| `backend/alembic/env.py` | Register Writing metadata |
| `backend/app/api.py` | Register Writing router |
| `backend/app/modules/writing/models.py` | Task / attempt / embedded immutable assessment rows |
| `backend/app/modules/writing/catalog.py` | Full validation, publication import, idempotency |
| `backend/app/modules/writing/contract.py` | Typed feedback, scores, exact UTF-16 evidence, quality guards |
| `backend/app/modules/writing/bridge.py` | Signed private server mutations and local key setup |
| `backend/app/modules/writing/router.py` | Ownership, draft versions, submit, quotas, claim/save |
| `backend/app/content/writing_v2/alua-writing-v2-ready.json` | Byte-preserved 32-task import source |
| `backend/app/content/writing_v2/archive/alua-writing-v2.json` | Byte-preserved full master/provenance |
| `backend/app/content/writing_v2/archive/alua-writing-v2.csv` | Byte-preserved reconciliation source |
| `backend/app/content/writing_v2/archive/alua-writing-v2-report.md` | Original source report |
| `backend/tests/test_writing.py` | Contracts, PostgreSQL, concurrency, security and browser fixture |
| `backend/tests/test_reading.py` | Migration-head assertion only; existing changes preserved |
| `backend/tests/test_firebase_auth.py` | Migration-head assertion |
| `web/src/app/page.tsx` | Honest Task 2 home metadata |
| `web/src/app/writing/page.tsx` | Topics route |
| `web/src/app/writing/attempts/[id]/page.tsx` | Editor route |
| `web/src/app/writing/attempts/[id]/results/page.tsx` | Saved result route |
| `web/src/app/api/writing/assess/route.ts` | Authenticated AI orchestration and signed persistence |
| `web/src/features/writing/api.ts` | Existing API client and assessment request |
| `web/src/features/writing/bridge.ts` | Private backend HMAC requests |
| `web/src/features/writing/contract.ts` | Types, word counter, model IDs and result validation |
| `web/src/features/writing/draft.ts` | Debounced serialized saves and existing IndexedDB recovery |
| `web/src/features/writing/messages.ts` | EN / RU / KK interface copy |
| `web/src/features/writing/pages.tsx` | Three screens, history, errors, reviews, comparison |
| `web/src/features/writing/prompt.ts` | Task 2 rubric and strict model wire contract |
| `web/src/features/writing/writing.module.css` | Alua styling and responsive/dark surfaces |
| `web/src/lib/ai/tasks.ts` | Enable only Writing, with its budgets |
| `web/src/lib/ai/orchestrator.ts` | Optional actual-provider metadata callback |
| `web/tests/ai-orchestrator.spec.ts` | Writing contracts and privacy/fallback/quality cases |
| `web/scripts/test-writing.mjs` | Disposable browser/native-live runner; one call cap per live run |
| `web/docs/listening-review-v2/ai/review-chromium-1366.png`, `review-webkit-mobile.png` | Regenerated existing regression screenshots |
| `docs/ALUA_WRITING_TASK2_IMPLEMENTATION_RESULT.md` | This report |
| `docs/writing-task2/README.md` | Artifact provenance and limitations |
| `docs/writing-task2/dataset-checksums.json`, `browser-result.json`, `live-first-result.json`, `live-second-result.json`, `live-result.json`, `live-summary.json` | Dataset and QA evidence |
| `docs/writing-task2/desktop-topics.png`, `desktop-editor.png`, `desktop-result.png` | Desktop UI evidence |
| `docs/writing-task2/mobile-topics.png`, `mobile-editor.png`, `mobile-result.png` | Mobile UI evidence |
| `docs/writing-task2/live-desktop-topics.png`, `live-desktop-editor.png`, `live-desktop-result.png` | Native live flow before final quality guard |

Outside Git: private local bridge key; additive database tables/catalog import. No production configuration, Cambridge data, Speaking implementation, commits, push, deploy or production SSH.

## G. User QA at http://localhost:3000

1. Open **Writing** from home, or `/writing`, and log in with your existing Firebase account. Optionally choose EN/RU/KK.
2. Search **reading and writing**. Open the real task **Adults lacking basic literacy despite widespread education**, stable ID `writing-t2-000004`. Try category/type filters and clear them.
3. Click **Start writing**. Read the complete English prompt and write your own essay. The optional timer has no submission side effects.
4. Wait for **All changes saved**, reload, and confirm your text remains. Return to topics and use **Continue**. Under 250 words, submission is disabled; the server also rejects it.
5. At 250+ words, click **Submit for AI Review**. The essay becomes immutable and a real model request is made. With unavailable/invalid AI output, the submitted essay remains and the results page offers a retry. The final generic-advice guard may currently cause safe refusals; this is the outstanding live gate.
6. For an accepted response, inspect four criteria and source evidence. Click **Review mistakes**, then a highlighted source sentence to see the category, correction, explanation and full Russian translation. A response with no identified issues says so explicitly. Reloading a saved result does not generate again.
7. Click **Try again on this topic**. The new draft starts separately; the old essay/score remains under previous attempts. After assessing the new version, select **Compare with a previous attempt**.

The automated three-call allowance is exhausted. No further automated live smoke was run. Completing the final live gate needs a separately authorized call budget.

## H. Final status

**PARTIAL** — functional local implementation and regression checks are complete; the final content-quality contract needs a successful live verification. Expert scoring calibration remains **NOT VERIFIED**.
