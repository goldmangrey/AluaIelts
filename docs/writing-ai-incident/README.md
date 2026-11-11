# Writing incident artifacts

Captured locally on 2026-11-11. No new real AI inference calls were made.

`desktop-*` use Chromium 1366×900; `mobile-*` use WebKit 390×844. Browser contexts requested a dark color preference; Writing correctly followed the existing global light application. Screenshots are real browser renders of a copied local frontend with UI auth stubbed for QA and a disposable PostgreSQL/FastAPI backend. They do not show private learner essays.

Topics are the real 32 READY records. Editor essay and all assessments/provider failures are synthetic fixtures. `*-result.png` verifies rendering, issue interaction and persistence only; it is not evidence of live model quality. Result captures are scrolled to the review area. `*-reference-home.png`, `*-reference-reading.png`, and `*-reference-listening.png` use the existing Alua page code for visual comparison. Native development indicator may appear.

`browser-result.json`: seven MOCK adapter invocations, zero new real calls; cached results and both viewport checks passed. `initial-429.json`: old limiter reproduced before any mutation or provider call. `context-probe.json`: context/binding availability only, not inference health. `production-reading-user-evidence.json`: sanitized existing Network response supplied by the user. `final-data-check.json`: read-only final persistent metadata/catalog validation. `changed-code-files.json`: files changed specifically in this incident, separate from pre-existing dirty checkout work.
