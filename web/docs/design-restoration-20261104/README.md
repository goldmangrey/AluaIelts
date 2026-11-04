# Original design recovery — 2026-11-04

Source: Cloudflare Worker `alua-ielts`, version `f2645651-f9a1-488d-a264-ed69acd5bc59` (2026-11-03 10:25 UTC).
All seven inspected Nov 3 preview deployments contain the premium Home and its four original WebP objects.
Git commits `0b83f96` and `0f81eb4` instead contain the simpler homepage. Reflog/stash/unreachable objects provide no recoverable premium frontend source. This establishes a deployed-build / tracked-source mismatch; it does not establish who removed uncommitted files or when.
The first inspected Nov 4 release `0fd69543-45cd-407a-a869-a9746e8e4779` replaced that build with the simpler tracked frontend; `5a1f037c-e0d5-4a65-abc5-0a7d0020f591` retained it while adding Listening V2.

Recovered Home markup, scoped CSS, original assets, Login markup/scoped CSS and Google popup/link flow from the live Nov 3 preview HTML/CSS/JS. No generated replacement images or new visual template. Reading library, exam, Results and Review already retain their scoped designs; their production sources and global CSS were left unchanged. Listening V2 sources were left unchanged.

Original source CSS: `/_next/static/chunks/32_wvd_dnou02.css` (Home), `22zog7nivrhcu.css` (Login). Class prefixes were converted to local CSS-module selectors; declarations retained.

Original asset SHA-256:
- `listening.webp`: `36a82b578304489f66d8f52e57e10e6448a0fe119dbfcee3376c3f430d57b200`
- `reading.webp`: `7cd821881fac52ba63ba08c417e4db106f5b8c1aa9b0fe96ef9522aa7659f929`
- `speaking.webp`: `61f4d43b2cb2e3364f4e63ea0f168d78e17312fb999e452905982bd5473b3bba`
- `writing.webp`: `72998de8bcb1a4eaa384b9e74fb0569e2663beabf4e85ef5d66992f70d0ea56e`

Screenshots here use the actual local frontend. Home/Login are signed out; Reading/Listening use existing isolated test fixtures, not production learner data. Mobile screenshots use the existing browser device profiles. Production browser checks are reported separately.

Regression selectors for Reading now match its pre-existing Quiet Focus interface: no idle Saved label, preset text sizes, and “Finish your test?”. No Reading runtime behavior was changed.

Local validation: lint, TypeScript and OpenNext Workers production build passed. Phase B: 19 passed (including Home/Login mobile and auth contracts). Listening integration: 12 browser scenarios passed via the existing disposable PostgreSQL fixture. Reading: 36 passed in the full run plus both desktop lifecycle scenarios passed on focused rerun after updating the pre-existing dialog title expectation. Original failure expectations were UI labels, not answer persistence failures. Google popup reached the real Google account chooser from localhost; cancelled without selecting or linking an identity.

## Production

Frontend-only deployed using `pnpm deploy:workers` (`--keep-vars`). Version: `33300515-2efb-4465-93ea-be2353de2aa9`.
URLs: https://alua.study and https://alua-ielts.yeskendiriskakov.workers.dev . Both return all four byte-identical original objects.
Browser: restored Home and Login on alua.study; Google popup reached account chooser and was cancelled without selecting/linking an identity. Existing Firebase session on Workers loaded real private Listening catalog and Reading catalog/history/results/readonly review. Fresh password/Google sign-in completion was not performed.
Listening smoke attempt `7db6b224-d2ea-4c04-9900-21f4ab862193`: V2 split panels/source bank, Cambridge 14 audio (08:43), Play/Pause/+5 seconds, Q1 Canadian, autosave, reload restored answer and 00:08 audio position, question navigation, confirmed Finish, result 1/40 and readonly Review all passed. Existing attempts were not edited.
Backend, production PostgreSQL, migrations and secrets were not changed. No commit/push/revert performed.

Screenshots: Home/Login signed out; Reading/Listening authenticated isolated local browser fixtures. Both desktop and mobile images are retained beside this document.
