# Alua safe production deploy — 2026-11-11

**Healthy backend/frontend deployed; Reading AI activation BLOCKED.**

- Application release: `233f8715c85d68bed25fe5c3bd5e7c83264b0604`, pushed on `release/ai-reliability-safe-20261111`. Original `main` remains at `97a70d3b2656c62df92c63966dea697c4771da30` with its original dirty state.
- Oracle: `/opt/alua/releases/reading-ai-reliability-20261111-233f8715c85d`.
- Worker: `3b94c08a-6b19-464c-a2dc-c197bab1d972`, 100%; deployment `df920bbf-147c-4d0c-8861-c18580a7dba3`; domain `alua.study`.
- Existing production Orchestrator V2 and Hotfix 41/41 preserved. No Cambridge content, answer-key, scoring, schema, auth, secrets or privacy-policy changes.

## Release gates and real smoke

64 focused backend checks and 97 AI/API contracts passed; TypeScript, full ESLint, scoped Ruff and production/OpenNext build passed. Listening browser gates: first run 7 PASS/1 FAIL, then the failing Chromium clip test passed after replacing a timing-sensitive current-time poll with an observed `timeupdate` maximum. Its short clip had completed/restored between polls. Temporary clip restore and Part 1–4 position tests passed in desktop Chromium/mobile WebKit.

The final Matching Information prompt was exercised in a separately deployed, QA-token-hash guarded Worker with native Cloudflare AI, disposable PostgreSQL and an explicitly enabled QA backend. Its OpenNext implementation matches the release; only the callback origin was substituted in the isolated preview bundle. No production secrets were copied; Groq was unavailable in that preview and Gemini/OpenRouter remained privacy-gated. Two bounded preview generation requests returned controlled unavailable. The diagnostic trace confirms real Cloudflare/Gemma generation rejected as **`invalid_candidate / prose_reference`**. Candidate/source checks were not weakened. No further model retries; preview Worker/tunnel/disposable backend were removed. Evidence highlight/backend FOUND-cache activation gate: **FAIL / not achieved**.

Production homepage/login/health, authenticated existing `ALUA QA Release` account, Reading and Listening catalogs, Reading result, unauthorized-request guards and controlled disabled Reading AI passed. Real Smart Translation returned 200 with exact-selection/Russian validation. Existing Listening AI returned valid 200, then cached:true on the repeat after rollout. Final authenticated Reading Review/Results and Listening Review AI browser smoke passed in **Chromium desktop and WebKit mobile**. Smoke used existing QA attempts and issued no answer/state/Submit mutation requests. The pre-existing GET `/reading/books` lifecycle nevertheless automatically expired one overdue `ALUA QA Release` attempt (`in_progress` → `expired`), creating its normal deadline result. This side effect was found by final row fingerprints and is explicitly retained; no manual data reversal or grading change was attempted. Listening attempts/mutations, Reading mutation records and Firebase identities retain identical aggregate hashes; the Reading-attempt aggregate differs. Atomic Submit passed in isolated QA and its production contract/code are preserved; a new production Exam→Submit flow was **NOT VERIFIED**.

## Corrective rollback during rollout

The initial isolated frontend build omitted the **public** Firebase API key because an overly broad variable-name filter excluded it. Browser smoke caught the resulting authenticated UI failure. Both backend and Worker were restored to the saved previous pair; then the frontend was rebuilt with the complete required public Firebase variables. Their actual values were asserted present in the browser bundles without printing them. The corrected artifact passed both browser engines on an unactivated version preview before redeployment, then again on production. Rejected Worker `81c62fb6-de59-4820-b006-eae970dd6588` is not active. No secrets or production environment files were modified.

## Safety and preservation

`READING_AI_ENABLED=false` remains enforced by the original, unmodified safety drop-in. No activation override was created. Reading cache now uses the private persistent `/opt/alua/shared/ai-cache/reading`; Listening retains `/opt/alua/shared/listening/ai-review`. Directories/entries are protected; old cache content was not deleted. Runtime callback remains `https://alua.study/api/reading/explain`. Worker AI binding and three provider secret names were checked, with no values printed. Reading external-provider approval remains absent.

Original checkout verification: same branch/HEAD/status, **6169 file hashes**, private env hashes and original frontend/backend/PostgreSQL PIDs. All three localhost health/proxy checks returned 200; PostgreSQL read-only check preserved all three pre-existing attempt snapshot hashes; existing cache files remain. Local callback/API configuration is unchanged. `~/Desktop/Listening` was already absent before any release action and remains absent; no audio was deleted or reconfigured. Only isolated build/test processes were stopped.

## Rollback

Previous backend: `/opt/alua/releases/ai-review-20261111-f83ef7da00ba`; previous Worker `b4d95ed7-6551-4a0e-8c16-3eaeadc3f2a4`, deployment `fa6d1879-62c8-4920-9e22-30ccbdd13c10`. The compatible pair rollback was exercised during this release.

Backend backup: `/var/backups/alua/pre-reading-ai-reliability-20261111-233f8715c85d/`. Under sudo, run its `release.py --meta release-meta.json --rollback`; restore the previous Worker with `wrangler versions deploy b4d95ed7-6551-4a0e-8c16-3eaeadc3f2a4@100 --yes`. Retain the independent Reading AI safety drop-in; no DB restore.

Sanitized operational evidence and browser screenshots are retained locally outside the active checkout at `/tmp/alua-safe-deploy-20261111-xswcz9jl/`. Temporary QA credentials and full tail transport records are removed. The original development checkout is not used for deployment/builds. **Final: BLOCKED for Reading AI activation; compatible backend/frontend deployment complete.**
