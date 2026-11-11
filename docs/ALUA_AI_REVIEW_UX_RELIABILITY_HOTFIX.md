# Alua AI Review UX & Reliability Hotfix

Local implementation and targeted QA, 2026-11-11. Reference: deployed application `7d1e32fb7daf50653dc6490eb42525e302ac8558`; newer mixed checkout preserved, including pending Results/Review V2 and content fixes. No commit, push, production SSH, live provider calls or deployment. Production `READING_AI_ENABLED=false` is untouched.

## Root causes

| Defect | Finding |
| --- | --- |
| Reading evidence | **CONFIRMED**: old protocol required models to reconstruct exact quotes. Recorded safe Q7 diagnostics failed exact quote matching, including after whitespace normalization. The precise per-provider Q6/Q10 historical outputs were not retained: **UNKNOWN** individually. There is no evidence that timeouts or normalization caused those recorded Q7 failures. |
| Reading grounding heuristics | **CONFIRMED** in code: literal accepted-answer/focus overlap and a 60% heading quote were additional acceptance barriers, not semantic entailment checks. They run after quote validation, so they are not asserted as the cause of the recorded quote failures. |
| Review answer colors/layout | **CONFIRMED**: selection styling did not consult saved verdicts; inline Review metadata lived inside the source sentence. |
| Reading scroll jump | **CONFIRMED**: card layout effect changed scroll/focus on mount/loading; closing did the same. |
| Listening first click/multi-open | **CONFIRMED**: focus cleared one global `opened`; focusing could collapse/move another card, and all playback/cache callbacks depended on that global question. One open slot could not support multiple cards. |
| Persistence | **CONFIRMED**: browser state was transient; default cache roots were `/tmp`, and Listening lacked bounded TTL/revalidation. Actual production filesystem/restart configuration is **NOT VERIFIED** in this task (no SSH). |
| Translation | **CONFIRMED** locally: busy and quota were conflated, identical upstream requests were not deduplicated, abort/retry could encounter a still-busy generation, and 15s inference plus auth/context could exceed the UI's 20s timeout. The cause of each historical production intermittent failure remains **UNKNOWN** without its diagnostic category. |

## Implemented behavior

Backend deterministically creates bounded sentence windows from the **frozen passage**, preserving whitespace, Unicode and occurrences. Candidate IDs hash passage/block/exact range/text. The model emits only `{candidate_id, kind}` (maximum three ordered, nonoverlapping selections), never quotes or offsets. Worker checks IDs against authenticated context; backend independently rebuilds candidates from its frozen source, checks IDs, relation kinds, paragraph/heading targets and prose, and calculates UTF-16 offsets. Unknown/foreign/stale IDs, added quote/offset fields and invalid kinds fail and allow provider fallback. Context/candidate counts and existing payload budgets remain bounded; over-budget source fails closed.

Lexical overlap is a search hint, not a proof or hard acceptance barrier. Heading selection has no arbitrary 60% length requirement. Exact anchoring **does not certify semantic correctness**; UI says the model-selected relationship may be wrong. NOT GIVEN is relevant context only, never proof of absence; FALSE/NO cannot use support. Saved verdicts, answer keys, grading, historical snapshots, ownership, private policy and disabled behavior are preserved. Protocol/fingerprint version is `reading-review-v1.2-candidates`, invalidating incompatible old Reading raw-cache entries.

Completed Review uses green correct answers/choices, red saved wrong answers/choices, distinct green corrections and grey unanswered states. Unordered choices use saved group verdicts. Inline blanks retain the source sentence; numbered Review metadata follows the group. Editing mode is untouched. These rules are scoped in the existing question renderer, independently of pending Review V2 styling.

Reading cards open independently and retain question-owned state. Opening/loading/retry/close does not scroll or focus. Scroll anchoring is disabled only in completed question panels. Explicit Show/Back scroll and focus their own container; Back also verifies the card enters the question viewport. Listening uses a set of open questions, question-bound cache/play callbacks and short-lived owner/attempt/question request promises. Remounts and rapid interactions reuse an in-flight/result promise, not a second provider call. Audio player code is unchanged.

Both modules retrieve authenticated server caches when reopened after navigation/reload. No persistent browser plaintext is introduced. Disk cache is owner/fingerprint scoped, private-directory/owner checked, 0600 atomic files, 30-day TTL, max approximately 1000 × 20KB per module. Reads revalidate context/evidence; unsafe cache roots fail before generation. Listening's additive `cached` flag is shown as Saved explanation. Existing source-unavailable reasons remain intact.

Translation rechecks auth, ownership, private policy and exact source selection **before** reuse. It hashes verified owner/attempt/content/selection context, shares identical in-flight requests and reuses only validated results for 60s in a bounded isolate map. Different concurrent requests receive `translate_busy` + Retry-After 1; the existing verified-request allowance remains 12/min, including cache hits and followers (no rate-limit bypass). Invalid/failed results are not cached. One bounded 15s budget covers normal server processing/auth/context/inference; a caller budget can shorten but never extend the task budget. Timeouts become controlled 504, invalid output 502, auth/policy remain distinct. UI retries and owner/attempt cache keys are corrected. Structured logs contain only task/category/status/provider status; existing orchestrator telemetry contains provider/model/outcome/latency/fallback reason. No selected text, prompts, credentials or responses are logged.

## Operational gate — do not activate yet

Nonproduction defaults: `/tmp/alua-ai-cache/{reading,listening}`. Production defaults: `/opt/alua/shared/ai-cache/{reading,listening}`, outside backend release directories and temporary service namespaces. Existing explicit `READING_AI_CACHE_ROOT` / `LISTENING_AI_CACHE_ROOT` overrides still take precedence.

For the next authorized release, verify effective paths and provision the existing shared directory as service user `alua`, directory mode 0700, files 0600. If a prior explicit `/tmp` path is configured, migrate verified existing Listening cache files to the persistent root and update that **non-secret** setting through the existing release workflow. Do not change secrets or `.env` in this task. Preserve compatible Listening cache filenames/fingerprints; old Reading quote-protocol cache entries are intentionally incompatible. Exercise a backend restart and prove cache hits without generation. If provisioning is absent, AI returns a controlled cache-unavailable error rather than generating into an unsafe location.

Before any Reading activation, use an authorized QA account and frozen synthetic/QA attempts only. Require real Groq success on C07 Q6/Q7/Q10 and the small known-good case with known candidate IDs and independently checked exact offsets, valid Russian reasoning, Show/Back and cache reuse after reload **and backend restart**. Verify a native Cloudflare candidate-ID response on nonpersonal data. Reject any invented ID, incorrect relation or unsupported explanation. Keep Reading disabled on failure; do not relax validators or enable Gemini/OpenRouter sensitive-task processing to obtain a green smoke. Actual live semantic/model quality remains **NOT VERIFIED** by this local hotfix.

## Targeted QA

- Reading candidate acceptance: C07 Q6/Q7/Q10 + small synthetic example **4/4 PASS, 0 FAIL**. Fabricated IDs in the three C07 cases **3/3 rejected**; changed historical source IDs also **3/3 rejected**. Additional schema/NG/paragraph/UTF-16/security tests pass.
- Backend: **45 PASS** (Reading AI, Listening AI and legacy compatibility; excludes content audit/browser fixture), plus **5 atomic Submit checks PASS**. Cache survives an actual new Python process; TTL, permissions and disabled Reading are exercised.
- Real local Next → FastAPI → Worker route → mock Groq → backend candidate resolution → UI: **one pytest fixture PASS / two browser configurations PASS**.
- AI/API contracts: **80 PASS**, including direct Groq, Cloudflare fallback, invalid candidates/output, auth-before-generation, Translation exact occurrence, dedup and unchanged request allowance. Native local workerd: **10 PASS**.
- Focused UX: **8 PASS / 0 FAIL**, Chromium desktop and mobile WebKit. Reading multiple cards, three scroll offsets, explicit evidence/back, reload cache, text/radio/unordered/inline verdict colors; Listening Q1/Q3 independent cards and own loop; Translation 429/504/502 messages, selection reuse and dedup. Browser transport mocks are explicit; they are not live model verification.
- TypeScript, full ESLint, Ruff, Next production and OpenNext Worker builds pass. No Cambridge corpus/content audit or entire app browser suite.

Screenshots: [Reading desktop](../web/docs/ai-ux-hotfix/reading-chromium-desktop.png), [Reading mobile](../web/docs/ai-ux-hotfix/reading-webkit-mobile.png), [Listening desktop](../web/docs/ai-ux-hotfix/listening-chromium-desktop.png), [Listening mobile](../web/docs/ai-ux-hotfix/listening-webkit-mobile.png), [answer semantics desktop](../web/docs/ai-ux-hotfix/answer-semantics-chromium-desktop.png), [answer semantics mobile](../web/docs/ai-ux-hotfix/answer-semantics-webkit-mobile.png), [Translation desktop](../web/docs/ai-ux-hotfix/translation-chromium-desktop.png), [Translation mobile](../web/docs/ai-ux-hotfix/translation-webkit-mobile.png). Synthetic accounts/data only.

## Changed scope

Backend: `app/core/config.py`; `modules/reading/{ai_review,evidence}.py`; `modules/listening/ai_review.py`; new `modules/private_ai_cache.py`; targeted Reading/Listening AI tests.

Web: `features/reading/ai/{contract.ts,prompt.ts,explanation.tsx}`; Reading explain route; `reading/exam/{reading-exam.tsx,question-renderer.tsx,question-options.module.css}`; `listening/{review.tsx,ai-explanation.tsx,workspace-questions.tsx}`; Translation route/popover; `lib/ai/{orchestrator,providers}.ts` bounded caller deadline/error classification. Tests/config/scripts/shared candidate fixture and these QA screenshots/documentation. Existing unrelated working-tree edits remain.

Commands: from `web`, `node scripts/test-ai-ux-hotfix.mjs`, `pnpm test:ai`, `pnpm test:ai:worker`, `pnpm typecheck`, `pnpm lint`, `pnpm build:workers`; from `backend`, targeted pytest names above and Ruff on changed modules/tests. No real credentials are needed.

**Verdict: READY FOR LIVE SMOKE. Production Reading remains disabled; deployment, persistent-root provisioning and live acceptance are separate gates.**
