# Reading AI reliability fix

Implemented locally, 2026-11-11. No commit, push, deploy, production flag/secret
changes or edits to existing attempts/results, keys or caches. No live model calls.

## Behavior

- Only task-validated `found` succeeds. Valid model-declared unavailable throws
  `model_abstained`, advances through the existing permitted sequential route and
  does not create a provider cooldown. Invalid citations/JSON still fall back.
- Exhausted providers produce controlled unavailable with top-level
  `retryable:true`. Trusted context failures remain deterministic and nonretryable,
  with no model call. Auth, privacy, deadlines and quotas retain their gates.
- Reading disk cache accepts/writes only validated found explanations. Existing
  negative entries remain untouched and are ignored; transient results are not
  written. Found entries keep the existing 30-day TTL and are revalidated on read.
- The existing fingerprint version is intentionally retained: valid found records
  remain reusable. Owner/attempt/question/frozen-snapshot isolation is unchanged.
- Frontend retains only found in memory. Temporary unavailable exposes Retry;
  reopening a temporary failure makes a fresh allowed request. Deterministic
  source failures expose no Retry. Concurrent clicks remain deduplicated.
- Prose length is 900 Unicode code points in both validators. Word boundaries
  reject actual learner accusations, not suffixes inside words such as «Мотивы».
  Paragraph-reference boundaries are aligned. Evidence offsets remain UTF-16;
  exact candidate IDs, quotes, paragraph and NOT GIVEN checks are preserved.

## Targeted QA

- 92 AI/API contract checks passed (91-test run plus one additional four-provider
  abstention/no-cooldown check). Includes Listening and Smart Translation.
- 52 Reading/Listening backend checks passed; one opt-in browser fixture excluded.
- 12 UI checks passed across Chromium desktop and mobile WebKit: Retry, stale
  negative memory bypass, found reuse, no-jump, navigation, multi-open, Listening
  evidence/audio controls, Translation and saved-answer colors.
- 10 native local workerd checks passed. TypeScript, targeted ESLint, Ruff and
  diff whitespace checks passed. No broad content audit or full app suite.
- Existing frozen C05 T2 Q1–Q3 found cache records revalidated in Python and TS.
  Existing C04 T1 Q2 context remains available. Actual C04 Q1 negative cache and
  frozen context were replayed against mocked callbacks in a temporary directory:
  two requests made two callbacks; the original cache bytes were unchanged.
- Eight shared Unicode parity cases are consumed by both test suites, including
  emoji limits, regex distance, word boundaries and UTF-16 evidence offsets.

## Files

`backend/app/modules/reading/ai_review.py`, `backend/tests/test_reading_ai.py`;
`web/src/lib/ai/orchestrator.ts`, `web/src/app/api/reading/explain/route.ts`,
`web/src/features/reading/ai/{contract.ts,explanation.tsx}`;
`web/tests/{reading-ai-contracts.spec.ts,ai-ux-hotfix.spec.ts}`,
`web/tests/fixtures/reading-ai-parity.json`, this document. Existing browser QA
screenshots under `web/docs/ai-ux-hotfix` were refreshed by the UI checks.

## Acceptance gate

**READY FOR LIVE SMOKE**, not a deployment approval. Before deployment activation,
verify a real authenticated found response with exact visible evidence and cached
reuse, plus a controlled failure/Retry. Use approved QA data; do not artificially
mass-fail providers. Production Reading AI stays disabled until that gate passes.
