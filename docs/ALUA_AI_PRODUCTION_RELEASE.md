# Alua AI release — 2026-11-11

Isolated release based on deployed Reading hotfix `e515eda1b0690e0c35fe03df74f8c07abb9efc2d`. The hotfix is already deployed; no content/key changes are repeated. Existing production Reading Review/Results and Listening UI are retained; only Reading AI interaction hunks are transferred from the mixed local checkout. Pending Results/Review V2 and Listening UI are excluded.

Previous backend: `reading-hotfix-20261108-e515eda1b069`.
Previous Worker version: `97c595ce-5264-4f16-b985-92c30ddf8cc9` (same application plus existing provider secrets).
Previous application deployment: `7666c892-2fcf-4858-b73c-1705541311d2` before the secrets-only version.

Release checks: TypeScript, scoped ESLint, production/OpenNext build, 19 Reading AI contracts and 13 backend evidence/security regressions passed. No dependency upgrades, migrations, environment-file changes or privacy approvals.

Real synthetic preview adapter verification: Groq and Cloudflare and Gemini returned valid Russian JSON. OpenRouter Free returned controlled HTTP 429; no paid model was called. Preview is bearer-protected, unactivated and has no production traffic. The production build has no smoke endpoint. Gemini/OpenRouter remain subject to default sensitive-task denial.

Backend workflow: `deploy/ai_review_release.py`, hash-pinned three-file overlay, clone previous release preserving ownership/modes, verify all unchanged non-payload files and catalogs as systemd user, activate drop-in with automatic backend rollback on failure. No DB restore/mutation. The release metadata stored in `/var/backups/alua/pre-<candidate>/` identifies rollback commands and scope.

Worker rollback: `wrangler versions deploy 97c595ce-5264-4f16-b985-92c30ddf8cc9@100 --yes`. Backend rollback: run stored `release.py --meta release-meta.json --rollback` under sudo. Always restore a compatible pair when existing features regress.

Production deployment/smoke identifiers and outcomes are recorded separately after activation. Local implementation report counts describe the original complete local checkout; release gates above describe this isolated artifact.
