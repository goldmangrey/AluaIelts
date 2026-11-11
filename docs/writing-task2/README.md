# Writing QA artifacts

All essays and scores in these screenshots are synthetic QA examples. Browser auth was stubbed only in a copied Next application; FastAPI authentication, ownership checks and PostgreSQL were real and disposable. No QA attempts were inserted into the persistent household database.

- `desktop-*` and `mobile-*`: mocked provider, Chromium 1366×900 and WebKit 390×844; real draft persistence, race handling, search/filter/sort, locale switching, submit, failure/retry, source highlights, Russian explanations/translations, retake and attempt comparison.
- `live-desktop-*`: third real call through the native Next route and existing Cloudflare binding. Four criterion scores were 9, 9, 8.5, 9; backend computed 9.0. This is an observed uncalibrated model estimate, not a verified expert rating. The model returned no issue anchors; actual issue highlighting was verified with mocks, while live criterion evidence was validated and persisted.
- Content review subsequently found generic advice about more sophisticated collocations. The final TS/Python validators reject it, and the prompt requires concrete contextual revisions. This final change has mock coverage but no live verification: the three-call allowance is exhausted. These live screenshots must not be used as evidence that the final quality gate passed.
- `live-first-result.json`, `live-second-result.json`, `live-result.json`: three separate runs; `live-summary.json` is the authoritative combined outcome. The first run's RPC counter did not intercept the call; its count was corrected from provider telemetry, explicitly documented in that artifact.
- `dataset-checksums.json`: byte-preserved imported source files.
