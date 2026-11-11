# Alua AI Orchestrator V2

Local implementation, 2026-11-10. No deployment, secrets changes or database migrations.

## Architecture and entrypoints

`providers.ts` is the compatibility facade for the existing AI layer. Its `listeningInference()` and `readingInference()` delegate to the single `ai.generate({env, task, messages, validate})` instance in `orchestrator.ts`. Four adapters share a small server-only contract; no new runtime dependencies.

| Entrypoint/task | Route/status | Deadline / attempt caps |
| --- | --- | --- |
| Listening `/api/listening/review` → FastAPI → protected `/api/listening/explain` / `listening_review` | Groq → Cloudflare → Gemini → OpenRouter; external providers require explicit task approval | 45s / 18, 12, 8, 7s |
| `/api/translate` / `smart_translate` | Same order; private passage text also requires external approval | 15s / 5, 4, 3, 3s |
| `reading_review` | Enabled by Reading AI Review V1; same provider order and privacy gate | 45s |
| `writing_assessment`, `speaking_assessment` | Reserved, disabled; no public endpoints | Unset |
| `ai_progress_report`, `ai_progress_chat` (Partner) | Migration **BLOCKED**; existing FastAPI OpenAI provider retained unchanged | Existing backend settings |
| `exercise_generation` | Migration **BLOCKED**; existing FastAPI OpenAI generator and deterministic fallback retained unchanged | Existing backend settings |

No separate Listening AI translation endpoint exists in the current application. Listening backend calls are already integrated through the protected, task-specific explain endpoint. The user credential on this existing path authorizes re-reading the user's context; it is not a universal service credential.

Progress/Partner and Exercise require a separate authenticated service channel before migration. No universal endpoint was added and no new service secret is currently consumed. A future migration must provision a dedicated shared secret on both FastAPI and Worker, authorize only implemented tasks and review the personal-data policy; do not reuse Firebase tokens or existing provider secrets. All AI calls are **not** migrated.

## Adapters and model selection

Central defaults and per-task token/temperature settings: `web/src/lib/ai/tasks.ts`.

| Provider | Model / API contract |
| --- | --- |
| Groq | `openai/gpt-oss-120b`, official Chat Completions, JSON object, low reasoning, `include_reasoning:false`, at least 1200 completion tokens (preserves existing reasoning budget). Keep 120B for short tasks until 20B has passed quality checks. |
| Cloudflare | `@cf/google/gemma-4-26b-a4b-it`, native `env.AI.run`, JSON object, `max_completion_tokens`, thinking disabled via chat template; normalizes `choices` or `response`. AbortSignal passed through native binding options. No additional API key. |
| Gemini | `gemini-3.5-flash-lite`, official `v1beta/models/...:generateContent`, `systemInstruction` + `contents`, `responseMimeType:application/json`; only final non-thought text with `finishReason:STOP` accepted. No Groq reasoning parameters forwarded. |
| OpenRouter | `google/gemma-4-26b-a4b-it:free`, official Chat Completions. Configurable server-side model. Only strict `vendor/model:free` IDs accepted; catalog must confirm zero pricing and JSON/text support. Runtime eligibility cached for 60s; refresh failure denies the request. `max_price` prompt/completion = 0; no alternate model list, router or paid fallback. Provider data collection denied and parameter support required. A free model with no matching privacy-compatible endpoint is unavailable. |

Catalog/contracts verified against official sources on 2026-11-10:
[Cloudflare schema](https://developers.cloudflare.com/workers-ai/models/gemma-4-26b-a4b-it/),
[Gemini model](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite),
[Gemini generation API](https://ai.google.dev/api/generate-content),
[OpenRouter live catalog](https://openrouter.ai/api/v1/models),
[OpenRouter routing/pricing controls](https://openrouter.ai/docs/guides/routing/provider-selection).
The Gemma free variant had zero pricing and `response_format` support in the catalog. Catalog verification is not a live Russian-generation quality test. No Qwen or Z.ai/GLM model is used.

## Failure, deadlines and privacy

- Strictly sequential, one attempt per eligible provider; stop at first **validated** result. HTTP 408/429/5xx, model 404/410, network failures, timeout, empty/invalid JSON and schema/semantic failure advance to the next provider. Other provider failures are contained as well. Provider 401/403 is diagnosed as configuration failure, never a user auth response.
- Monotonic total inference deadline; each attempt is capped by remaining time. Do not start with less than 250ms left. When privacy/kill switches leave only Groq and Cloudflare, the final Cloudflare attempt retains the previous 18s Listening allowance (translation can use its remaining 15s total budget). All HTTP requests and native AI receive cancellation signals. Listening context fetch has a 4s cap, leaving 45s for inference within FastAPI's existing 50s call and the public proxy's 55s timeout. Network/scheduling overhead still requires operational monitoring.
- Best-effort bounded in-memory cooldown per provider/model: rate limit defaults to 30s; parsed Retry-After seconds/date capped at 5min. Other temporary outages get 2s. No global guarantee across isolates. Invalid task output is not cooled down; missing keys produce a configuration diagnostic without blocking healthy reserves.
- Listening keeps backend cache/fingerprint, allowance, ownership, saved verdict and playback timing. Worker additionally validates Russian review fields, exact quotes, contiguous known IDs and duration before accepting a provider; backend still owns timestamps and final evidence validation. Empty evidence must have an empty quote.
- Translation validates the exact selected occurrence **inside each attempt**. Existing private Reading policy, offsets, size/rate limits, auth and no-store remain in place. Exhausted semantic/JSON failures retain the existing 502 codes; provider outages produce existing controlled 503 errors. Listening provider exhaustion remains `ai_review_unavailable`.
- Both active tasks are sensitive by default. No personal answers/private text go to Gemini/OpenRouter unless the operator explicitly approves the task. User/client request fields cannot grant approval or select a model/provider/URL. No new public endpoints. Existing authorization runs before inference.
- Requests: at most 8 messages / 96KB encoded input. HTTP envelopes capped at 64KB, normalized content at 12K characters; OpenRouter catalog separately capped at 2MB. Existing tighter API bounds remain. Fixed official HTTPS endpoints, manual redirects, no raw prompts/responses/reasoning/secrets in diagnostics.
- Telemetry fields only: `task`, `provider`, `model`, `outcome`, `latency_ms`, `fallback_reason`. Worker observability remains unchanged; collecting these events depends on the operator's existing logging setup.

## Configuration and operation

Existing secrets: `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`; existing binding: `AI`. Runtime env is obtained through `getCloudflareContext({async:true})`. Production secrets and `.env` were not edited.

Optional Worker **non-secret** variables (no `NEXT_PUBLIC_` prefix):

| Variable | Default / operation |
| --- | --- |
| `AI_GEMINI_ENABLED` | Enabled at adapter level unless exactly `false`; task privacy gate still applies. |
| `AI_OPENROUTER_ENABLED` | Same; set `false` to disable independently. |
| `AI_EXTERNAL_TASKS` | Empty: denies both external providers for all sensitive tasks. After approved data-processing policy, list approved task IDs, e.g. `smart_translate` or `smart_translate,listening_review`. Do not set solely to enable more fallbacks without policy approval. |
| `AI_OPENROUTER_MODEL` | Optional explicit `:free` model ID; runtime catalog guard cannot be bypassed. |

No new variable is required for the safe Groq → Cloudflare default. For four-provider production activation, policy approval and `AI_EXTERNAL_TASKS` are required in addition to the already provisioned secrets. Locally absent keys are supported; tests use mocks. No production keys were retrieved for testing.

Quick operational rollback to Groq → Cloudflare: set both enable flags to `false` (or remove `AI_EXTERNAL_TASKS`). This keeps validators, cooldown and the supported Gemma fallback. For a source rollback, revert only files introduced/changed by this task from a saved diff; do not reset the repository or other Reading/UI changes. Do not restore the deprecated Qwen model.

To add a fifth provider: implement the Adapter contract with fixed official endpoints and an explicit parameter allowlist; register it in the orchestrator and central order/model/budget/privacy configuration; extend mocks, contract and workerd tests. Keep validators in task/domain code.

## Verification

Commands: `pnpm test:ai`, `pnpm test:ai:worker`, `pnpm typecheck`, `pnpm lint`, `pnpm build`, `pnpm build:workers` from `web`; targeted pytest from `backend`.

Generative provider calls are mocked. Public model catalog/documentation reads are real; **no live authenticated generation smoke** was performed. Groq/Gemma/Gemini/OpenRouter Russian output quality and production account eligibility must be smoke-tested before four-provider activation. Backend Progress/Exercise migrations remain blocked as described above.

Local QA results:

- AI/provider/API contract tests: 58 PASS; real local workerd with mock adapters: 5 PASS.
- Backend Listening (excluding the unrelated full transcript-coverage audit): 6 PASS; legacy Progress/Exercise: 5 PASS.
- Translation UI: 2 PASS (desktop/mobile).
- Listening UI suite: 50 PASS, 4 SKIP, 6 FAIL. All 12 AI review cache/retry/playback cases passed. The six failures are the same existing workspace test expecting a `Finish practice` button (`tests/listening-review.spec.ts:158`); reproduced in Chromium 1600 with the original HEAD AI provider/routes substituted in a disposable copy. No Listening UI code or this existing test was changed.
- Reading hotfix: 41 issue checks + registry integrity PASS (42 total); no broad dataset audit.
- TypeScript, ESLint, Next production build and OpenNext Cloudflare Worker bundle: PASS.

Release status: **PARTIAL**. Local AI integration passes; production generation quality/account availability is unverified, the unrelated UI baseline failure remains, and backend Progress/Exercise migration is blocked. No commit, push or production deploy performed.

Reading task activation is documented in [ALUA_READING_AI_REVIEW_V1.md](ALUA_READING_AI_REVIEW_V1.md). Listening/Translation routes and their budgets were not changed by that feature.
