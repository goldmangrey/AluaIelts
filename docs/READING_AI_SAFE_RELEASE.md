# Reading AI reliability release

This isolated release starts at deployed `527b70d` (application `7d1e32f`). It carries the Reading reliability, source-owned evidence and Stage 1/2 contracts, multi-open/cache/Retry UI, and Listening temporary-moment navigation fix. Orchestrator V2, private-provider policy, Translation, Player, auth, grading and Cambridge content remain at the production baseline. Unfinished Results/Review redesign and local-stack infrastructure are excluded.

Production Reading AI remains disabled by its existing independent systemd safety drop-in until the final Matching Information prompt passes real generation, exact frozen paragraph validation, visible highlight, Back navigation and backend cache reuse in a protected isolated preview. The preview uses the release's built OpenNext bundle, changing only the QA upstream origin, plus a one-account route guard; no production secret is copied. Its backend uses disposable PostgreSQL and its own enabled configuration. Production data is not used for that gate.

Release-copy backend workflow: `deploy/reading_ai_reliability_release.py`, with hash-pinned metadata archived outside the source tree. It backs up the prior release, retains file ownership and all non-payload bytes, checks catalog access/contracts, and restarts only production `alua-api`. No migrations or environment-file edits. The separate safety flag survives rollout and rollback.

Rollback: use the generated backup's `release.py --meta release-meta.json --rollback` under sudo, then restore Worker version `b4d95ed7-6551-4a0e-8c16-3eaeadc3f2a4` at 100%. If a separate Reading activation override was added after a successful gate, disable that override before rollback; retain the safety drop-in. No database restore.

Local active checkout, branch, source hashes, service PIDs, private configuration, existing attempt snapshots and cache manifests are checked before/after outside the checkout. The original Next/FastAPI/PostgreSQL processes are never restarted by the release workflow. Isolated dependencies and builds are physical copies.
