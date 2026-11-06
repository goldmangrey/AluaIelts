# Listening AI Review — local implementation (2026-11-06)

Production deployed on 2026-11-06. `GROQ_API_KEY` presence verified from secret metadata only; its value was not read or changed. Existing attempts/results were preserved. No migrations, commit or push. See the production release evidence below.

## Runtime path

The browser sends only attempt ID and question number to `POST /api/listening/review`. Its bounded proxy calls protected FastAPI `POST /listening/attempts/{id}/ai-review/{number}`. FastAPI checks existing identity/ownership, terminal status and the stored incorrect verdict before reading private context/cache. On a cache miss it calls the Worker `/api/listening/explain`, forwarding the user's bearer credential (no additional Oracle secret). The Worker independently obtains trusted context from the protected FastAPI context endpoint; it never accepts client-supplied keys or transcripts. Context transactions end before the HTTP round trip.

The Worker uses Groq `openai/gpt-oss-120b` first, Qwen3 `@cf/qwen/qwen3-30b-a3b-fp8` second. Reading retains its exact existing Gemma prompt/primary invocation and translation validation; only transient failure invokes Groq. One invocation per provider, no retry loop; inference deadlines 18 seconds per provider. Authentication, access, configuration, invalid input and malformed output do not trigger failover. Cloudflare's documented internal quota/timeout/access codes are classified as their corresponding HTTP status. Final assistant content alone is read, never reasoning fields; nothing sensitive is logged.

FastAPI validates strict structured Russian JSON, known consecutive segment IDs, a verbatim quote, bounded evidence span and actual audio duration. It computes the clip with 2.5 seconds before / 3 seconds after, capped at the real file and reviewed transcript boundary. Model timestamps/extra fields are rejected. Guesses about student attention/thoughts are not presented as facts. Missing/invalid evidence is replaced by a neutral server-owned explanation without clip/quote. Known incomplete/identity-mismatched transcripts never invoke AI.

Durations are read locally with small pure-Python Mutagen metadata support for MP3/VBR/M4A; no ffprobe/ffmpeg process or new system service is required on Oracle. Existing audio bytes remain unchanged.

Successful results use an atomic private file cache keyed by owner/attempt/question plus immutable snapshot/key/answer/transcript/audio fingerprint. Default `LISTENING_AI_CACHE_ROOT=/tmp/alua-listening-ai`; production can use `/opt/alua/shared/listening/ai-review` for retention across reboots. Per-owner in-process busy/rate guards (6/minute) plus a Worker isolate guard cover this existing single-process, 1–2 user deployment. No distributed limiter or new table is introduced. Stored attempts/results are never recalculated or mutated by AI review.

## Content and QA

Imported exactly 288 canonical JSON Parts from `~/Downloads/IELTS_Transcripts_QA_Reviewed_04-21.zip` into private `backend/app/content/listening_transcripts_v1`. Stable segment IDs reference original ordered segments; text/start/end are retained. Manifest pins archive and document SHA-256. Re-import produced 289 identical JSON files including manifest. These remain machine transcripts, not claims of independent audio verification.

- Cambridge 05: canonical Test/Part mapping follows the supplied QA source_audio map. Audio manifest and inventory importer now transpose the original physical filenames for new snapshots. Twelve affected historical snapshots are preserved; if their audio identity disagrees with the canonical transcript, AI supplies no evidence. Regression verifies the old snapshot/result is unchanged.
- Cambridge 12: printed Tests 5–8 preserved.
- Cambridge 14 T2 Part 4: only 55 reviewed segments ending at 511.46 seconds; following Test 3 material is excluded from AI input and clip context.
- Cambridge 21 incomplete Parts: T1 P1/P2/P3; T2 P2/P3; T3 P2/P3; T4 P2/P3. Preserved without invented continuation; no exact moment is offered.

## Review/player

Compact inline Explain with AI exists only for scored incorrect saved answers. Opening another question closes it, aborts the pending browser request and stops the loop. An in-page cache plus server cache handles reopen/reload. HTTP failures show Retry. Only the short selected transcript quote reaches the UI, in collapsed details.

Play Moment/Loop Moment reuse the single existing audible Player and its metadata preloader. Cross-Part moments wait for the new recording's metadata (avoiding a stale-duration/pending-seek race). Timer plus native end events enforce the boundary, including clips ending at EOF. Changing question/Part, manual seek/pause, hiding audio, leaving the document/page or turning Loop off stops the moment. Normal playback/seek/part continuation remain available.

## Changed files

- `backend/app/modules/listening/ai_review.py`, `router.py`; two settings in `backend/app/core/config.py`.
- `backend/scripts/listening_transcripts/import_reviewed.py`, private `backend/app/content/listening_transcripts_v1/*.json`.
- `backend/app/content/listening_audio_v1/audio_manifest.json`, `backend/scripts/listening_media/import_inventory.py` (Cambridge 05 mapping only).
- `backend/pyproject.toml`, `backend/uv.lock` (Mutagen only).
- `web/src/lib/ai/providers.ts`; routes `web/src/app/api/listening/explain/route.ts`, `review/route.ts`, existing `web/src/app/api/translate/route.ts`.
- `web/src/features/listening/ai-explanation.tsx`, `review.tsx`, `review.module.css`, `player.tsx`.
- `backend/tests/test_listening_ai.py`; `web/tests/listening-review.spec.ts`, `smart-translate-contracts.spec.ts`, `smart-translate-browser.spec.ts`. Reading's old browser test was aligned with its already existing Translate toggle + word click and current error text; product prompts/UX/cache were not changed. Review's audio fixture now serves real HTTP Range responses rather than misleading Chromium with full WAV responses for byte ranges.

## Validation

- Backend Listening/Reading/auth regression: 39 PASS; additional legacy Cambridge 05 preservation regression: PASS.
- Provider/API/Reading contracts: 16 PASS (including simulated Groq primary, 429/5xx/timeout failover, Cloudflare internal quota/access errors, no fallback on invalid/auth data, ownership and bounded inputs).
- Real Cloudflare binding: Qwen fallback after simulated Groq 429 returned Russian structured JSON with supplied segment ID/verbatim quote; PASS. Reading with its unchanged production prompt returned the existing Russian translation format; PASS. These live calls used controlled test context, not a production user's attempt.
- Groq primary and Reading Groq fallback: deterministic mocked transport PASS. Real Groq calls remain BLOCKED by missing key; no live Groq quality claim.
- Native Chromium/WebKit desktop/mobile: AI moments/cache/retry/reload/switching Part/EOF loops/page exit: 12 PASS. Shared V3 lifecycle/audio/split regressions: 23 PASS in broad run and all 6 targeted Soft Capsules/seek checks PASS after pause-time display synchronization. Existing Review navigation/layout checks passed in the broader run.
- Reading translator browser regression: 2 PASS (Chromium desktop/WebKit mobile), using its existing Translate + word-click UX and unchanged cache/error behavior.
- Import coverage/QA/idempotency, strict evidence and real MP3/M4A duration tests PASS, including M4A bytes with a misleading .mp3 suffix.
- TypeScript, ESLint, Ruff and production OpenNext build PASS. Isolated build preserves current premium Home/Login byte-for-byte and excludes unrelated pending Reading UI edits. Public assets contain no transcripts, private datasets, keys, source maps or fixtures.

## Unblock and deploy

Configure the Worker secret interactively; never put it in NEXT_PUBLIC, a command argument, source control or chat:

```sh
cd /Users/yeskendir/Projects/Alua/web
npx wrangler secret put GROQ_API_KEY
```

For local real Groq development, use ignored server-side `.dev.vars` with the same key; no client public variable is used. For a local FastAPI+Worker pair, set `LISTENING_AI_WORKER_URL` to the local frontend `/api/listening/explain` URL and the existing frontend upstream to the local backend. Default production Worker URL is fixed to `https://alua.study/api/listening/explain`; only this HTTPS host or local HTTP hosts are accepted by the backend.

Before publishing, run live Groq primary and Reading fallback smoke with the configured secret. Then use the existing encrypted database backup workflow, copy the active Alua backend release, install the frozen backend dependencies (`uv sync --frozen`), overlay only the AI modules/config additions/private transcripts/Cambridge 05 audio manifest, retain all historical content-addressed assets and audio, configure the private shared cache directory, and activate only alua-api. No migrations. Build/deploy the isolated premium-preserving frontend through existing OpenNext/Wrangler --keep-vars. Verify saved attempt/result fingerprints before/after. Retain preceding backend release and Worker version for rollback. Do not touch Flora.

Technical references: [Groq API](https://console.groq.com/docs/api-reference), [Qwen3 binding](https://developers.cloudflare.com/workers-ai/models/qwen3-30b-a3b-fp8/), [Cloudflare error classification](https://developers.cloudflare.com/workers-ai/platform/errors/), [Mutagen metadata](https://mutagen.readthedocs.io/en/latest/user/gettingstarted.html).


## Production release — 2026-11-06

- Backend: `/opt/alua/releases/listening-ai-20261106`, copied from `listening-practice-20261105`; AI service/router/settings, private transcripts, Cambridge 05 manifest and frozen Mutagen dependency overlaid. Only `alua-api` restarted. Existing cache directory `/opt/alua/shared/listening/ai-review` is private and writable through a service drop-in. No database migrations.
- Existing encrypted backup succeeded before activation: `alua-20261106T050538Z.dump.age`, SHA-256 `2be759691a356d517647e07f60686a78ae80f8d9de9d7ef655cb241a6a8da62a`. Backup workflow unchanged.
- Cloudflare deployment ID: `cc6514ee-1105-437e-b080-cb67d5092552`; version `01f5530e-d611-40fd-9bb2-38646d18609c` at 100%, deployed with existing OpenNext/Wrangler `--keep-vars`. Previous version `11347369-6938-4e79-bf7a-ede9687607b5` retained. Secret metadata still lists `GROQ_API_KEY` after deployment.
- Deployment integration fix: Workers rejects Fetch `redirect: "error"` before sending the Groq request. Changed to `manual`; non-2xx (including redirects) are rejected, redirects never followed. Verified real Groq primary with Cloudflare fallback explicitly disabled. Added regression asserting manual mode and no fallback for 302. No prompts or Reading UI changed.
- Real remote preview provider smoke: Groq GPT-OSS 120B primary PASS; Qwen3 after synthetic Groq 429 PASS; unchanged Reading Gemma primary PASS; Reading Groq after synthetic Cloudflare 503 PASS. Simulations exist only in a temporary preview harness, never production routes. Secret remains in the Worker binding.
- Production completed attempt `01da64f5-eb13-4339-92fc-67af91142f70`, Cambridge 14 Test 2, question 1: full browser → Worker → backend → Worker AI route returned HTTP 200 (API smoke 2.97 s). Evidence `seg-0042`, quote `It's 219-442-9785.`, clip 186.44–196.52 s. IDs and verbatim quote were independently checked against trusted transcript context; clip padding checked. Reopen returned identical cached review.
- Native Chrome production UI displayed the Russian explanation. Play Moment started inside the interval and stopped at 196.5 s; Loop Moment repeatedly stayed inside the same interval (observed 194.3 → 188.5 s); changing question stopped audio and collapsed the explanation. Chromium desktop and WebKit mobile automated Play/Loop/retry/cache checks passed; initial WebKit EOF-loop test timed out, targeted rerun passed.
- Provider/API contracts: 17 PASS including redirect regression. Public assets contain no private transcripts, PDF keys or source maps. Isolated frontend source comparison against the preceding release confirmed Home/Login and Reading UI unchanged; changes limited to Listening files and provider/API routes.
- Production Reading `/api/translate` with an existing owned passage returned HTTP 200 and the normal Russian translation format.
- All stored attempts/results remained byte-equivalent by database row fingerprints: Listening 10 rows `30332d1244ddca043fbe3e79106c4aa4`; Reading 26 rows `49394b0c8a03c165f64964afa992698c` before and after. No historical attempts were submitted or recalculated. Flora, other application databases and production secret configuration were not changed.

Earlier local-only validation/blocker notes above describe the pre-release state and are superseded by this release evidence.
