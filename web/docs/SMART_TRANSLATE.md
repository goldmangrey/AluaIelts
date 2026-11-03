# Smart Translate V1

Enabled only for the existing `passage_practice` attempt mode (including its review). Full exams remain unchanged. No new practice mode or backend endpoint was added.

Selection API observes passage text only. A 650 ms settled selection triggers a same-origin POST to `/api/translate`; mouse dragging suppresses requests. Escape, an outside pointer event, scrolling or resizing dismisses the card. No selection cancellation, clipboard handlers, focus trap or scroll lock. Client requests time out after 20 seconds, obsolete responses are discarded, and up to 100 successful translations are cached in memory per mounted passage/account. Input answer fields are outside the selection scope.

The route accepts Firebase-shaped bearer tokens, delegates actual identity verification to the existing protected `/me` API, then reads the owned attempt through the existing protected Reading API. It requires `passage_practice` and verifies the supplied sentence occurs in the specified passage block. It never requests result/answer-key endpoints or sends questions/answers to AI. The AI receives only sentence, selected text and UTF-16 start/end offsets.

Limits: streamed request body 4 KiB, sentence 600 characters, selection 100 characters, model completion 160 tokens, expression 160 characters, translation 240 characters. The expression must be a literal bounded quote covering the actual selected occurrence. Invalid output produces a clear error rather than an invented fallback. Gemma runs only server-side through `getCloudflareContext().env.AI.run()`, using `@cf/google/gemma-4-26b-a4b-it`, JSON output and `chat_template_kwargs.enable_thinking: false`.

No existing shared rate limiter was found in web. The route implements best-effort memory throttling: 12 requests/minute per verified learner, one active request per learner, at most 2,000 tracked learners per Worker isolate. This is not a global quota: different isolates/locations and restarts have independent counters. It does not limit rejected traffic before `/me`. No KV/R2, distributed storage, new dependency or API key was introduced.

## Verification (2026-11-03)

- `pnpm typecheck`, `pnpm lint`, `pnpm build`, `pnpm build:workers`.
- `pnpm exec playwright test --config=playwright.translate.config.ts --project=contracts`: 9 tests for phrases/word, bounded context, wrong occurrences, malformed model output, authentication, practice-only access, source validation, body size and throttling. Server dependencies/AI are mocked in these tests.
- `node scripts/test-smart-translate.mjs --project=desktop --project=mobile`: Chromium desktop and iPhone WebKit viewport; loading/error/cache/reselection, dismissal, bounds and answer-field isolation. Screenshots inspected. The harness is temporary with a synthetic passage and mocked token/AI HTTP response; selection is applied with DOM Range. Native long-press handles on a physical phone are not verified.
- Existing `pnpm preview:workers -- --port 8787` starts real workerd with remote AI binding. Anonymous and invalid Firebase requests return 401 with private/no-store headers.
- Real remote AI binding was also invoked through Wrangler `getPlatformProxy`, using the actual route/prompt/validator with synthetic identity and attempt transport. The final prompt returned `looking forward to` / «с нетерпением ждать», `used to` / «раньше», `am used to` / «привык», `take into account` / «учитывать», `As a result of` / «в результате» and `evidence` / «доказательство». This verifies real model inference independently of authentication; it is not an end-to-end signed-in test. No production attempt was created or changed.

Build artifacts are ready for the existing Cloudflare workflow. No deploy, push, commit or SSH was performed. A signed-in Firebase end-to-end check and physical phone long-press check remain before release. Literal quote validation cannot guarantee semantic translation accuracy.

Reference: [Cloudflare Gemma binding schema](https://developers.cloudflare.com/workers-ai/models/gemma-4-26b-a4b-it/).
