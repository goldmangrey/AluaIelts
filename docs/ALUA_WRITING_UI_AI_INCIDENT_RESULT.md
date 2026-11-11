# ALUA — WRITING UI + AI INCIDENT RESULT

Date: 2026-11-11. Final status: **PARTIAL**.

Light-first Writing redesign and verified error-handling fixes are implemented locally. No new real AI inference calls were made. Real Writing scoring quality remains unverified; production was not changed. Existing learner data and the running local stack were preserved. No commit, push, deploy, production SSH, production secret/configuration changes, or dataset edits.

## A. Confirmed AI root cause

| Environment | Module | Failure point | HTTP status | Root cause | Evidence |
|---|---|---|---|---|---|
| Local | Writing | FastAPI assessment claim, propagated through Next `/api/writing/assess` | 429 | Existing immutable attempt reached lifetime cap of 3 claimed evaluations. Old Next response hid `ai_rate_limit` behind `AI_UNAVAILABLE`. | Existing access logs, unchanged attempt metadata, exact limiter branch and read-only handler reproduction in [initial-429.json](writing-ai-incident/initial-429.json). |
| Local | Writing | Initial 3 accepted claims, followed by completion and failed Next response | 503 | Exact original exception **NOT VERIFIED**: old catch discarded it. Quota was claimed before fallible environment preparation. No Writing provider-dispatch telemetry was present in the complete frontend log. | [Phase A audit](writing-ai-incident/PHASE_A.md), [context probe](writing-ai-incident/context-probe.json). Absence of telemetry is not proof of external quota exhaustion or a definitive count of historical network calls. |
| Production | Reading | `POST https://alua.study/api/reading/review` | 503 | Application `reading_ai_unavailable` confirmed by user Network response. Current exact runtime cause **NOT VERIFIED**. Historical release deliberately disabled Reading; current code also emits the exact supplied message when worker URL configuration is rejected. | [User-provided response](writing-ai-incident/production-reading-user-evidence.json), [historical deployment report](ALUA_AI_PRODUCTION_DEPLOY_RESULT.md). |
| Production | Listening | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED; current production Network/log evidence unavailable. | User report only; older successful release smoke cannot establish current health. |

### Exact Writing request and call sequence

- Browser: `POST http://localhost:3000/api/writing/assess`.
- Upstream: `POST http://127.0.0.1:8000/api/v1/writing/attempts/{attempt_id}/assessment/claim`.
- **FastAPI formed the 429**, code `ai_rate_limit`, message `Writing AI quota reached.` Next returned the old sanitized body `{"error":{"code":"AI_UNAVAILABLE"}}` with status429.
- Old code supplied no Retry-After or request ID for this limiter. Historical raw Network rate-limit headers were not retained; provider headers/IDs cannot be inferred.
- Ordinary sequence: draft save → submit immutable essay → Next assessment route → authenticated own-attempt lookup / claim → environment/input → Orchestrator V2 → eligible providers sequentially → strict validation → signed backend persistence → result. The fix moves environment/configuration preflight before claim and cached-result reads before preparation.
- Three accepted claims were followed by complete200 and Next503 in approximately 0.6–1.2 seconds each. Nine subsequent rejected claims are visible. **Each rejected claim made zero provider calls.** Historical initial dispatch count cannot be conclusively recovered. No evidence establishes duplicate provider dispatches from a single Submit.
- New browser/client coalescing and backend lease/idempotency tests prevent overlapping retries; reload reads saved results rather than regenerating them. A permitted fallback can still create sequential calls to different providers; this is distinct from duplicate submission.

### Provider availability versus quota

The successful no-inference probe found Cloudflare AI binding present and local Groq key absent. It did not invoke `AI.run`. Current inference transport, provider quota and final model output quality are **NOT VERIFIED**. The local429 is an application attempt cap, not confirmed Cloudflare exhaustion.

Writing's persistent application quota is separate from Reading/Listening user request limiters. Provider/model cooldowns and provider account quotas can affect several modules; a shared external quota incident has not been established here. Reading's historical disabled flag must not be mistaken for a provider rate limit.

No Cloudflare/Groq dashboard action is currently justified as a confirmed remedy. If later metadata identifies provider429, inspect that provider account's usage/limits and reliable Retry-After; wait for its reset or use only an already approved configured fallback. Do not raise application limits or enable sensitive-content providers as a workaround. Groq is not configured locally; configuring it would require separate user-managed credentials/authorization and would not resolve the existing attempt cap.

## B. Fixed issues

- Writing Next route now reads authorized cached results first and prepares provider context before consuming a claim. It preserves safe application/provider/environment/transport classifications, HTTP status and supplied Retry-After. Adds request IDs and metadata-only diagnostics; no raw essays, tokens, keys, headers or raw exception text in operational logs.
- Shared Orchestrator V2 retains terminal provider429 and reliable cooldown wait/request ID instead of turning it into generic503. Unknown provider wait is not invented from the internal cooldown. Parsing failures remain distinct from transport failure. Existing provider routing/privacy/capability gates and evidence validators remain enforced.
- Backend source distinguishes lifetime attempt cap from the rolling hourly cap, computes an hourly Retry-After, and persists typed failure status through an opt-in backward-compatible completion protocol. Existing limits remain **3 per immutable attempt / 6 per owner-hour**. No counters reset or refunded.
- Client coalesces parallel assessments per owner/attempt. Human EN/RU/KK errors distinguish rate limiting, unavailable providers and unreliable output. Reliable waits survive reload; Retry is disabled while pending/waiting or for nonretryable caps. No fabricated score is displayed. Checking a pending result does not initiate generation.
- Removed Writing's independent dark wrapper and media-query theme. Shared Alua page tokens now determine background, borders, text and mint/teal accents. Topics have compact filters and a responsive grid; editor has full readable prompt, white textarea and useful writing space; results use simple criterion sections and accessible issue controls.
- Native mobile selects have explicit 44px control height and 16px text. No global styles were changed.

**Activation limitation:** the existing persistent backend process does not hot reload. Backend source changes were tested with a disposable backend but were **not loaded into the current running persistent process**, because restarting/stopping local-stack is prohibited. The updated Next route supports its legacy responses. The original attempt still has three spent claims and no assessment; this incident did not restore its allowance or prove the cause of its first503.

## C. Validation

| Check | Result / scope |
|---|---|
| TypeScript | PASS — `pnpm typecheck` |
| ESLint | PASS — `pnpm lint` |
| Ruff | PASS — changed backend Writing router/test files |
| Whitespace | PASS — `git diff --check` |
| AI/Reading/Smart Translation contracts | PASS — 112 tests, all providers mocked |
| Backend regressions | PASS — 110 tests, 2 browser tests deselected; Writing, Reading/Listening AI, legacy compatibility, Firebase auth and existing catalogs |
| Focused backend Writing | PASS — 15 tests; schema/evidence rejection, ownership, quotas, idempotency, persistence and failure status |
| Writing browser | PASS — Chromium desktop and WebKit mobile; real 32-task catalog, mock assessments/failures, disposable PostgreSQL/backend |
| Listening browser | PASS — 4 focused desktop/mobile audio-loop restoration and Part1–4 navigation tests |
| Search/filter/sort | PASS in browser |
| Editor/autosave/reload/race/retake | PASS in isolated browser/backend tests |
| Submit, unavailable, invalid output, rate limit, retry | PASS with mocks; no automatic retry storm, reliable cooldown survives reload |
| Assessment persistence/cache/review mistakes | PASS with mock validated result; no valid saved live assessment available for inspection |
| Persistent dataset | PASS — master326, READY32, pending288 excluded, aliases6 excluded; CSV/JSON validation passed, database tasks32 |
| Local-stack | Frontend/backend RUNNING; persistent PostgreSQL readable; no stop/restart |
| Existing data | Preserved; original attempt remains version1 / 346 words / submitted / ai_calls3 / no assessment |
| Production live regression | NOT VERIFIED; no production access or changes |

The seven adapter calls in [browser-result.json](writing-ai-incident/browser-result.json) are **MOCK calls**, not real Groq/Cloudflare requests. New real calls: **0**. Firebase/browser UI auth was stubbed only in the copied QA frontend; actual ownership enforcement was tested in the disposable backend. This does not replace a production Firebase login smoke.

## D. Visual QA

Actual browser screenshots, synthetic essay and mock AI data:

| Screen | Desktop | Mobile |
|---|---|---|
| Topics | [PNG](writing-ai-incident/desktop-topics.png) | [PNG](writing-ai-incident/mobile-topics.png) |
| Editor | [PNG](writing-ai-incident/desktop-editor.png) | [PNG](writing-ai-incident/mobile-editor.png) |
| AI unavailable | [PNG](writing-ai-incident/desktop-unavailable.png) | [PNG](writing-ai-incident/mobile-unavailable.png) |
| Rate limited | [PNG](writing-ai-incident/desktop-rate-limited.png) | [PNG](writing-ai-incident/mobile-rate-limited.png) |
| Result / issue review, MOCK | [PNG](writing-ai-incident/desktop-result.png) | [PNG](writing-ai-incident/mobile-result.png) |
| Existing Home reference | [PNG](writing-ai-incident/desktop-reference-home.png) | [PNG](writing-ai-incident/mobile-reference-home.png) |
| Existing Reading reference | [PNG](writing-ai-incident/desktop-reference-reading.png) | [PNG](writing-ai-incident/mobile-reference-reading.png) |
| Existing Listening reference | [PNG](writing-ai-incident/desktop-reference-listening.png) | [PNG](writing-ai-incident/mobile-reference-listening.png) |

Compared shared header, white page/surfaces, neutral borders, teal actions, typography and spacing with existing pages. Inspected final mobile topics/editor/unavailable and desktop issue review. Both viewports reported no horizontal overflow or page errors. Focus/issue activation, native controls and input/reload were exercised. Contexts requested dark color preference; page remained white according to the existing global application, without an independent Writing theme. No global dark-mode mechanism was added. Result screenshots are scrolled to the review area, not a live scoring demonstration. See [artifact notes](writing-ai-incident/README.md).

## E. Live AI status

| Module | Status |
|---|---|
| Writing | **BLOCKED** — existing attempt cap remains; no new real calls authorized; inference and final assessment quality not verified |
| Reading production | **NOT VERIFIED** for working AI; existing503 failure confirmed, exact current runtime branch not verified |
| Listening production | **NOT VERIFIED** |
| Expert calibration | **NOT VERIFIED** |

Actual local available pathway: Cloudflare binding; local Groq absent. No real model tested during this incident. No production fix claimed.

## F. Changed files

Only incident-specific changes are listed below. The checkout contained extensive earlier uncommitted work; those other changes were preserved.

| File | Purpose |
|---|---|
| `backend/app/modules/writing/router.py` | Distinct quota causes/headers and backward-compatible typed failure completion |
| `backend/tests/test_writing.py` | Quota/failure contract tests and incident browser fixture |
| `web/src/app/api/writing/assess/route.ts` | Cached/authorized lookup, preparation before claim, safe error/status propagation and diagnostics |
| `web/src/lib/ai/adapters/common.ts` | Safe provider request ID and reliable Retry-After extraction |
| `web/src/lib/ai/adapters/cloudflare.ts` | Preserve safe Cloudflare error/rate metadata |
| `web/src/lib/ai/orchestrator.ts` | Terminal429/cooldown classification and safe dispatch telemetry |
| `web/src/features/writing/failure.ts` | Typed failure parsing and owner/attempt-scoped session metadata |
| `web/src/features/writing/api.ts` | Client assessment request coalescing and classified failures |
| `web/src/features/writing/messages.ts` | Human localized error/retry copy |
| `web/src/features/writing/pages.tsx` | Error/retry/pending states and compact page hierarchy |
| `web/src/features/writing/writing.module.css` | Scoped light-first responsive redesign |
| `web/tests/ai-orchestrator.spec.ts` | Provider429, metadata, preflight, error parsing and duplicate request tests |
| `web/scripts/test-writing.mjs` | Incident-only mock browser QA and reference captures; refuses live incident mode |
| `docs/ALUA_WRITING_UI_AI_INCIDENT_RESULT.md` | This report |
| `docs/writing-ai-incident/PHASE_A.md` | Pre-edit evidence audit plus supplied production response interpretation |
| `docs/writing-ai-incident/README.md` | Artifact provenance and mock/live distinctions |
| `docs/writing-ai-incident/initial-429.json` | Sanitized original limiter reproduction |
| `docs/writing-ai-incident/context-probe.json` | No-inference binding probe result |
| `docs/writing-ai-incident/production-reading-user-evidence.json` | Sanitized supplied production503 |
| `docs/writing-ai-incident/final-data-check.json` | Read-only persistent dataset/attempt check |
| `docs/writing-ai-incident/validation-summary.json` | QA summary |
| `docs/writing-ai-incident/changed-code-files.json` | Incident code file inventory |
| `docs/writing-ai-incident/browser-result.json` | Mock browser trace/counts |

All 16 PNG files in section D are new incident artifacts and are also part of the changed-file inventory. No temporary diagnostic route remains. No database migration or dataset file was changed in this incident.

## G. Remaining blockers and concrete next actions

1. **Existing Writing attempt exhausted:** retain the essay and limit; no reset was performed. Before any more real review, obtain explicit additional live-call authorization and decide how to handle the exhausted attempt without silently bypassing its cap. Do not create replacement attempts just to evade the limit.
2. **Original503 remains partly unexplained:** old code discarded the exception. New metadata-only diagnostics identify environment/claim/provider/validation/persistence stages on a future explicitly authorized call. Binding presence alone is insufficient to certify the provider. No evidence currently requires a dashboard quota change.
3. **Backend source activation:** load tested backend changes only during a separately authorized local restart; none was performed here. Current Next error handling supports the old process meanwhile.
4. **Production Reading:** user supplied a confirmed503; distinguish current feature flag from rejected worker URL using authorized operator configuration inspection. Do not automatically enable Reading: its historical evidence gate failed. Production Listening still needs existing Network status/body/Retry-After/request IDs/time. Do not send HAR, cookies, Authorization, tokens or essays, and do not generate extra AI calls for diagnosis.

Optional operator command, **not executed here**, on an already authorized production console. It prints only the Reading flag from the service Environment property; no full environment/secrets output:

```sh
systemctl show alua-api.service --property=Environment --value | python3 -c 'import shlex,sys; values=[v for v in shlex.split(sys.stdin.read()) if v.startswith("READING_AI_ENABLED=")]; print("\n".join(values) if values else "READING_AI_ENABLED not explicit in systemd Environment; effective application setting still needs verification")'
```

If it is absent, this command does not establish the effective application value because an EnvironmentFile/default may apply. The operator should report only whether the effective flag is true/false and whether the configured worker URL passes the existing approved scheme/host/path checks; do not dump configuration. An approved URL uses `/api/reading/explain` on `https://alua.study` (local development permits loopback HTTP). This is diagnosis guidance, not authorization to change production.

### Local user QA without spending AI budget

1. Open `http://localhost:3000/writing` and sign in normally.
2. Check 32 tasks, search/topic/type/sort; open a real task with Start writing/Continue.
3. Type several paragraphs; wait for saved status, reload, and confirm the text/paragraphs remain. Switch topics and return.
4. Open the existing submitted attempt to inspect the saved essay and human failure state. Do not press Submit/Retry to test inference while the no-new-calls constraint applies.
5. Inspect the saved screenshots for unavailable/rate-limited/result/issue-review states. Result and retake/persistence interactions were exercised using mocks; no fake assessment was inserted into persistent user data.
6. After separate authorization for a bounded real call and any required local backend activation, verify a fully validated result, exact evidence highlights, saved reopening without generation, and a preserved first attempt when writing a second version.

## H. Final status

**PARTIAL** — local UI redesign and verified application defects are fixed/tested. Existing submitted work is preserved. The running backend still uses its prior code until an authorized restart; the exhausted attempt remains capped. No new real AI quality gate passed, and production Reading/Listening restoration is not verified.
