# Alua Reading AI Review V1

Implemented locally, 2026-11-11. No commit, push, deployment, production DB/secrets or `.env` changes.

## Experience

Result → existing Review → select a question → **✦ Explain with AI** → one active, inline-adjacent/group-footer card → **Show in passage** → exact temporary evidence → **Back to Qn**. All 15 existing types have specific prompt rules. Correct and blank answers get factual labels rather than invented mistakes. Summaries/tables keep their inline HTML; the card is outside the question group, never inside a blank `<span>`. Option banks are not duplicated.

Opening a card scrolls/focuses only the question container. Evidence navigation scrolls/focuses only the passage container; mobile switches the existing Source/Questions panels and returns to the open explanation. Closed/loading/success/cached/unavailable/rate-limit/provider-error/retry states are implemented. Selection changes abort/ignore stale requests. Client cache is component/learner/attempt scoped and kept in memory, not persistent plaintext storage.

Evidence ranges compose with user highlights at shared boundaries, using one `<mark>` per text interval. Green evidence has a gold underline when it overlaps a user highlight. AI does not write drafts, answers or annotations. Review reads existing highlights from the existing owner/hash-scoped draft; bookmarks remain untouched. Smart Translation works over the composed text nodes.

Screenshots (real local browser captures with synthetic AI responses):

| Chromium 1366×768 | WebKit 390×844 |
| --- | --- |
| [Closed](../web/docs/reading-ai-review-v1/desktop-closed.png) | [Closed](../web/docs/reading-ai-review-v1/mobile-closed.png) |
| [Open](../web/docs/reading-ai-review-v1/desktop-open.png) | [Open](../web/docs/reading-ai-review-v1/mobile-open.png) |
| [Evidence](../web/docs/reading-ai-review-v1/desktop-evidence.png) | [Evidence](../web/docs/reading-ai-review-v1/mobile-evidence.png) |
| [Unavailable](../web/docs/reading-ai-review-v1/desktop-unavailable.png) | [Unavailable](../web/docs/reading-ai-review-v1/mobile-unavailable.png) |

## Trusted flow

Browser sends only `attempt_id` and `question_id` to `POST /api/reading/review`. The same-origin bounded route forwards IDs to authenticated FastAPI `POST /api/v1/reading/attempts/{aid}/ai-review/{qid}` with the existing user authorization.

`ReadingAIReview` verifies ownership and terminal `submitted`/`expired` status with a saved result. It reads **only the frozen snapshot**, saved verdict/answer/key, one passage and one question group. It never expires, submits, edits or regrades an attempt. Fingerprint covers learner, attempt, actual frozen snapshot/key, saved result/answers, question and prompt/evidence-policy version.

On a cache miss, backend calls the fixed allowlisted Worker `POST /api/reading/explain`, sending IDs and the existing authorization. The Worker reauthorizes through protected FastAPI `GET .../ai-review/{qid}/context`, then calls the existing `ai.generate` with task `reading_review`. This is the Listening task-specific security pattern, not a universal service endpoint or a Firebase token used as a shared service secret.

Worker strips learner/attempt identifiers from model context, uses a type-specific prompt, and validates every candidate **before accepting it**, so bad JSON/citations/grounding can fall back. Backend checks the returned fingerprint and independently repeats schema, exact-anchor and semantic checks; only backend calculates UTF-16 `start/end`. Frontend rechecks anchors against its saved passage before rendering.

## Evidence and limitations

- Exact five-field model schema, bounded Russian prose, no HTML/URLs/extra fields or claims about student attention. At most three ordered nonoverlapping anchors, exact unique quotes within the correct passage, paragraph blocks only. Duplicate quotes elsewhere in the passage are rejected too. No approximate matching or model-generated offsets.
- Text completions require a whole accepted-answer occurrence **and** relevant vocabulary from the local blank/sentence context. A matching key word in an unrelated paragraph is insufficient. Headings must reference the question's paragraph and cover its main context (at least 60% of the paragraph per quote, maximum 1200 characters). Matching Information checks the keyed paragraph; other selections check source concepts from trusted options/statements. These conservative necessary checks can reject legitimate paraphrases.
- NOT GIVEN permits only `relevant_context`, explicitly labelled as context, never proof of absence. FALSE/NO cannot use `support`. Unordered groups supply the whole saved group; swapped letters do not override the saved verdict.
- Diagrams/flowcharts requiring visual interpretation return `unavailable`, without a model call. A source-image representation can still use its complete restored text/options; missing essential text/options fails closed. There is no OCR/vision pipeline.
- `needs_review` alone does not block a usable context. Broken source characters, missing options, inconsistent frozen key/results, scoped critical integrity warnings and input-budget excess do. No current canonical passage/key replaces historical material.
- Exact source anchoring and deterministic checks **do not prove all AI reasoning correct or certify fidelity to the publisher PDF**. UI identifies the saved-text/PDF-quality limitation. No paid judge or automatic second-model call is used. Live Russian generation quality is NOT VERIFIED.

## Routing, cost and errors

`reading_review` is enabled in existing `tasks.ts`: Groq → Cloudflare → Gemini → OpenRouter Free, 45s total, 2400 output tokens, task validators and existing cooldown/deadline/pricing guards. Listening/Translation task settings and contracts are unchanged.

Privacy defaults deny Gemini/OpenRouter for this sensitive task. They are eligible only after operator-approved data processing and explicit `AI_EXTERNAL_TASKS=reading_review` (or inclusion in its comma-separated list), subject to existing independent enable flags. This implementation does not set that approval or alter any Worker variable/secret.

Backend cache is private, atomic (0600 temporary file + replace), fingerprint scoped, 30-day TTL, maximum approximately 1000 × 20KB entries per cache root. Schema/evidence are checked again on cache reads. Bump `VERSION` after prompt/schema/grounding/model-policy changes. Cached requests bypass generation allowance.

Backend generation, callback context, and Worker inference each have bounded best-effort per-user protection (6/min). Callback quota prevents direct Worker calls from bypassing origin quota. An identical in-flight request gets controlled 429 rather than consuming another generation or blocking origin callback threads. Maps are bounded; protection is per-process/isolate, not distributed. No Redis/new DB.

All provider failures return existing-style controlled unavailable errors. Exhausted invalid citations return explicit evidence-unavailable, never fabricated highlights. API responses are private/no-store. No prompts, transcripts, responses or secrets are logged; orchestrator metadata only.

## Configuration / rollback

No new secrets or dependencies. Existing `GROQ_API_KEY` and `AI` binding are sufficient for default routing. Gemini/OpenRouter use the existing secrets only when policy permits. Local environment currently has no provider keys; mocks keep tests independent of production secrets.

Optional **backend non-secret** settings:

- `READING_AI_ENABLED=true` by default. Set `false` for immediate feature shutdown (controlled unavailable, no generation).
- `READING_AI_WORKER_URL=https://alua.study/api/reading/explain` by default. For local development set it in the process environment to `http://127.0.0.1:<Next-port>/api/reading/explain`; local HTTP is accepted only in local/development environment. URLs, redirects, credentials and arbitrary paths cannot be selected by a client.
- `READING_AI_CACHE_ROOT=/tmp/alua-reading-ai`; configure a private writable directory for durable deployment caching if desired. Without persistence, cold starts regenerate normally.

Rollback: disable backend `READING_AI_ENABLED`; for UI removal revert **only this feature's hunks** in ReadingExam/QuestionGroup/PassagePane and remove the new `features/reading/ai` + `api/reading` files; set `reading_review.active=false`. Keep pre-existing Reading hotfix/UI edits and the V2 orchestrator. No database rollback is needed.

## Targeted QA

- 100 backend regression checks passed: Reading AI validation/context/cache/single-flight, Listening AI, Reading Submit/history and known hotfix fixtures. Includes all 41 known defect checks; no 72-test content re-audit.
- Full real local Next → FastAPI → Worker-route → mock Groq → FastAPI validation → UI journey passed on Chromium desktop and mobile WebKit. Includes actual submitted attempt, keyboard activation, exact scrolling/back, overlap highlights, translation, bookmarks, cached reopening, stale response suppression, passage switching, 429/503/retry, unavailable state, Q16 heading and Q37 action binding. Negative UI transport scenarios are explicitly mocked.
- Existing V2/translation plus new Reading AI contracts/fallback tests and native local workerd checks passed; exact final counts are in the implementation report.
- TypeScript, ESLint, Ruff, Next production build and OpenNext Cloudflare Worker build passed.
- No authenticated live model calls: providers **NOT VERIFIED** against production accounts. All generative calls were mocks.
- Existing unrelated Listening UI baseline failure (`Finish practice` selector) documented in the V2 report remains outside this change; the full unrelated UI suite was not claimed green.

Commands: `pnpm test:ai`, `pnpm test:ai:worker`, `pnpm typecheck`, `pnpm lint`, `pnpm build:workers` in `web`; `.venv/bin/python -m pytest tests/test_reading_ai.py` in `backend` (creates disposable PostgreSQL and local Next/FastAPI fixtures). No production access is needed.

Final counts: **100 backend regression PASS / 0 FAIL**, plus **1 end-to-end pytest fixture PASS** exercising **2 browser configurations PASS / 0 FAIL**; **77 AI/API contract tests PASS / 0 FAIL**; **10 local workerd checks PASS / 0 FAIL**. Feature backend subset: **28 PASS**, plus its browser fixture. Production model quality remains unverified; local implementation is complete, production activation is **PARTIAL pending live smoke** with the existing Worker secrets.

Changed/added source: `backend/app/modules/reading/ai_review.py`, `backend/app/modules/reading/router.py`, `backend/app/core/config.py`; `web/src/features/reading/ai/{contract.ts,prompt.ts,explanation.tsx,review.module.css}`; `web/src/features/reading/exam/{reading-exam.tsx,question-renderer.tsx,passage-pane.tsx}`; `web/src/app/api/reading/{review,explain}/route.ts`; `web/src/lib/ai/tasks.ts`. Supporting changes: `backend/tests/test_reading_ai.py`, `web/tests/reading-ai-contracts.spec.ts`, shared JSON fixture, existing AI routing/workerd tests and configs/scripts, `web/package.json`, this document and the V2 task-status note. Pre-existing unrelated edits remain intact.

Additional existing Exam → atomic Submit → Review browser regression: **12 PASS / 0 FAIL** (six repaired Cambridge fixtures × Chromium/WebKit; opt-in `ALUA_RUN_READING_HOTFIX_BROWSER=1`). Its pre-existing artifacts were backed up and restored. Total browser workflows checked: **14 PASS / 0 FAIL** including the two new AI flows. No full Cambridge corpus audit was run.
