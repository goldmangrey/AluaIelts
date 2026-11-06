# Listening Review V2 — local verification

Implemented on top of the existing Listening Workspace V3. Existing unrelated working-tree changes were preserved. No commit, push or deployment.

## UI and shared components

- `src/features/listening/review.tsx`: separate read-only Review, compact result strip, part navigation, All / Incorrect / Unanswered filters, collapsible replay player. Band is rendered only when returned by the server.
- `review-status.ts`: presentation-only interpretation of backend verdicts. Blank answers are grey; answered ungraded/ambiguous rows are neutral blue. Ambiguous notation and unavailable keys are never presented as a reliable correction. Preliminary expected answers are explicitly labelled.
- `workspace-questions.tsx`: the existing source resolver, original images, zoom, independent pane scrolling, mobile tabs, keyboard/pointer divider and source-following behaviour. Optional answer renderer and visibility set support Review without duplicating the workspace.
- `workspace-navigator.tsx`: extracted common V3 footer, used in both practice and Review. Review supplies verdict colours and has no mark/finish/editor controls. Escape works without relying on button focus in Safari.
- `review.module.css`: scoped Review presentation, 55/45 split, full viewport height and a smaller navigator height budget on phones. No global page scroll in the tested viewports.
- Shared answer banks remain on the left. On the right, bank questions show the saved choice instead of repeating the whole bank for each question.

Review never instantiates `ListeningDraft` and never calls sync or submit. Playback checkpoints stay local; the existing playback-authorisation request remains necessary for listening. Saved answer values are rendered as text/static options, not editable form controls.

## Verification

Run from `web/`:

```sh
npm run typecheck
node node_modules/eslint/bin/eslint.js src/features/listening/pages.tsx src/features/listening/review.tsx src/features/listening/review-status.ts src/features/listening/workspace-questions.tsx src/features/listening/workspace-navigator.tsx tests/listening-review.spec.ts tests/listening.spec.ts playwright.listening-review.config.ts scripts/test-listening-review.mjs --max-warnings=0
ALUA_REVIEW_PRODUCTION=1 node scripts/test-listening-review.mjs
```

The browser harness builds and serves a disposable copy of the frontend. Only that copy uses a fixture session; repository Firebase modules are unchanged. API responses are intercepted locally, and external browser requests are blocked. PostgreSQL and backend servers are not started. Original dataset files are read without modification, and results are produced by the existing pure Python grading function with bytecode writes disabled.

Coverage:

- Chromium and WebKit: 1600×900, 1366×768 and 390×844.
- Additional 375×667 check in both mobile browser projects, with audio and navigator expanded together.
- Verified Cambridge 14 Test 1; preliminary Cambridge 6 Test 1, including the ambiguous question 7; ungraded Cambridge 4 Test 2.
- Correct, incorrect, unanswered and ungraded statuses; preliminary-key labelling; no invented band or ambiguous correction.
- Original image loading and SHA-256 identity, zoom, independent scroll, divider pointer/keyboard/reset, source-following across groups, all 40 navigator targets, filters, reload and previous/next navigation.
- Playback, seek, part selection, replay and collapse. Audio transport uses a generated local WAV; real Cambridge recording content and backend authorisation are not integration-tested by this harness.
- No answer mutations or editable answer fields in Review. Shared V3 regression checks cover input, marks, navigator and sync against a local intercepted API.

## Screenshots

`before/`: six screenshots of the original Review, captured before implementation.

`after/`: final source/questions views, expanded navigator and preliminary/ungraded results for all six browser/viewport projects, plus short-phone screenshots. Images are local and no artifacts were published.
