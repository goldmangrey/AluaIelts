# Alua AI production deployment — 2026-11-11

**PARTIAL DEPLOYMENT; READING AI ACTIVATION BLOCKED.** Orchestrator V2 is deployed; Reading AI code is deployed but disabled with `READING_AI_ENABLED=false` after live evidence smoke failed. No invented explanation/highlight was accepted. Existing routes remain healthy.

- Backend: `/opt/alua/releases/ai-review-20261111-f83ef7da00ba`; its three-file payload is unchanged in frontend source commit `7d1e32fb7daf50653dc6490eb42525e302ac8558`.
- Worker application source: `7d1e32fb7daf50653dc6490eb42525e302ac8558`; version `b4d95ed7-6551-4a0e-8c16-3eaeadc3f2a4`; deployment `fa6d1879-62c8-4920-9e22-30ccbdd13c10`, 100% traffic.
- Release branch: `release/ai-v2-reading-v1-20261111`. Original mixed checkout/main and unfinished Results/Review V2/Listening UI edits preserved.
- Hotfix 41/41 was already deployed as `e515eda`; no content/key changes repeated.
- Production Worker secrets checked by names only; Groq/Gemini/OpenRouter keys and native AI binding retained. No production `.env`, database schema, secrets or privacy approvals changed. Gemini/OpenRouter sensitive-task gates remain closed.

## Actual smoke

Real Groq, native Cloudflare AI and Gemini adapters returned valid Russian JSON on fixed nonpersonal synthetic text through a protected **unactivated** preview. OpenRouter Free returned controlled 429, not successful generation; no paid fallback. No artificial provider failures were injected into production.

Production homepage/login HTTP, authenticated dedicated `ALUA QA Release` profile, Reading/Listening catalogs, Reading Review and Smart Translation passed. New dedicated-QA Reading Exam → ordinary atomic Submit → Results passed. Only QA attempts were created/answered through ordinary authenticated APIs; no real learner attempt/result was edited. Listening AI API returned its valid existing 200 contract; clip quality was not independently certified.

Live Reading Q7, Q6 and Q10 in the guarded historical C07 QA attempt returned controlled evidence-unavailable; exact evidence/highlight/back/cache success is **NOT VERIFIED**. Safe synthetic diagnostics found model quotes failing exact source matching. Validators were not weakened. No further generation retries were made. A duplicate Explain button introduced during release-hunk extraction was corrected in `7d1e32f` and the corrected artifact deployed.

Reading AI was disabled through this dedicated systemd drop-in (nonsecret process configuration; environment file untouched):
`/etc/systemd/system/alua-api.service.d/zzzzzzzzzzzzzzzz-reading-ai-safety-20261111.conf`.
It contains `[Service]` and `Environment=READING_AI_ENABLED=false`. After restart: health/auth/Reading/Listening catalogs = 200; authorized Reading AI context = controlled 503; unauthorized AI review = 401. Production model-output/evidence reliability must be corrected and independently smoke-tested before removing this safety flag. Do not automatically enable external sensitive-task processing as a workaround.

Release gates: 19 Reading AI contracts, 13 backend evidence/security checks, TypeScript, scoped ESLint and production/OpenNext builds passed. The broader local report counts were not rerun or claimed as production results.

## Rollback

Original compatible backend: `reading-hotfix-20261108-e515eda1b069` (commit `e515eda1b0690e0c35fe03df74f8c07abb9efc2d`). Original Worker: `97c595ce-5264-4f16-b985-92c30ddf8cc9`; original deployment `b3fcbb1a-2687-4ae8-b5d1-34f7acac77a6`.

Backend backup and checked rollback script: `/var/backups/alua/pre-ai-review-20261111-f83ef7da00ba/`. Run its `release.py --meta release-meta.json --rollback` under sudo. Worker: `wrangler versions deploy 97c595ce-5264-4f16-b985-92c30ddf8cc9@100 --yes`. Retain the safety drop-in until a verified Reading AI activation; the old backend ignores that setting. No DB restore is needed. A paired rollback was not required because existing Reading/Listening remained healthy.

See [sanitized deployment evidence](ai-production-release-20261111/worker-deployment.json). No prompts, user answers, full model responses, tokens or keys are included in these artifacts. Production screenshots and credentials are not committed.
