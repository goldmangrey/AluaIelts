# ALUA Review V2 — Focus Mode

Implemented in Review variants only. Active Exam rendering retains its existing branch and defaults. Results changes from the earlier task were left as they were.

## Measured workspace at 1366 × 768

Chromium, first Part/Passage, no open dialog. Values come from `getBoundingClientRect()` on the workspace, header, player and footer elements in the same browser fixture before and after implementation. Raw measurements are stored alongside this report.

| Element | Listening before | Listening after | Reading before | Reading after |
| --- | ---: | ---: | ---: | ---: |
| Header | 42 px | 48 px | 84 px | 48 px |
| Player | 148 px | 92 px | 0 px | 0 px |
| Bottom toolbar | 61 px | 0 px | 62 px | 0 px |
| Workspace top | 340.69 px | 151 px | 204.5 px | 84 px |
| Workspace height | 366.31 px | 617 px | 501.5 px | 684 px |
| Workspace gain | | **250.69 px** | | **182.5 px** |

Listening Player is 94 px on mobile. Mobile Source / Questions controls remain available; both pages keep their workspace within the viewport.

## Verification

- **20/20 PASS:** Listening and Reading in Chromium and WebKit at 1440×900, 1366×768, 1280×720, 390×844 and 375×667, against an isolated production build.
- Both headers measure 48 px; no top summary, large Review heading or bottom toolbar remains.
- No document horizontal or vertical overflow. Navigated questions sit below the sticky filters.
- Independent panel scrolling, per-Part/Passage scroll restoration, keyboard divider resizing, filters and Q1–Q40 navigation pass.
- Prepared source images remain available without additional asset GETs when returning to visited Parts/Passages.
- Listening uses the existing V4 Player component and original waveform assets. Native playback, seek, ±5 seconds, independent visible/audio Parts and AI Play/Loop pass.
- **4/4 AI regression checks PASS:** Chromium desktop and WebKit mobile; cached explanations, collapse/reopen, retry, incomplete evidence, loop at audio EOF and restoration of normal playback.
- **3/3 Reading regression checks PASS:** active Exam lifecycle, Results → readonly Review → History, minimal Results and unfinished attempt protection.
- No answer inputs become editable in Review; no attempt mutations occur.
- TypeScript, ESLint and production build: **PASS**.

QA runs in real headless browser engines with test-only auth and API fixtures in a disposable frontend copy. Questions, source images and waveform files come from existing repository content. Audio playback uses a short local WAV fixture; AI responses are supplied fixtures. No real user results or production AI calls are involved.

The existing Listening AI endpoint accepts scored incorrect, non-empty answers only. Unanswered and ungraded answers retain their saved answers/corrections without an unsupported AI action. Reading has no existing explanation endpoint, so no new AI action/API was introduced there.

## Reproduction

From the repository root:

```sh
ALUA_REVIEW_PRODUCTION=1 node web/scripts/test-review-focus.mjs
ALUA_REVIEW_PRODUCTION=1 node web/scripts/test-listening-review.mjs --project=review-chromium-1366 --project=review-webkit-mobile --grep 'AI review is|AI retry'
node web/scripts/test-reading-release.mjs --project=release-chromium --grep 'home →|Result V2'
pnpm --dir web typecheck
pnpm --dir web lint
pnpm --dir web build
```

## Changed files for this Review task

Production UI:

- `src/features/listening/review.tsx`
- `src/features/listening/review.module.css`
- `src/features/listening/workspace-navigator.tsx` — status metadata on the existing header navigator.
- `src/features/listening/workspace-questions.tsx` — optional right-panel toolbar and Review-only reveal-on-navigation; existing scroll/cache owners retained.
- `src/features/reading/exam/reading-exam.tsx` — Review header, filters and navigation using existing Passage/current/modal state.
- `src/features/reading/exam/question-renderer.tsx` — Review verdict metadata, filtered visibility and focusable readonly anchors.
- `src/features/reading/exam/review.module.css` — styles scoped to Review.

QA:

- `playwright.review-focus.config.ts`
- `scripts/test-review-focus.mjs`
- `tests/review-focus-fixture.ts`
- `tests/review-focus.spec.ts`
- `tests/listening-review.spec.ts`
- `tests/listening.spec.ts`
- `tests/reading-release-browser.spec.ts`
- `tests/reading-local-integration.spec.ts`
- `docs/review-focus-v2/` — measurements and representative screenshots.

## Screenshots

- [Listening desktop](listening-chromium-1366.png)
- [Reading desktop](reading-chromium-1366.png)
- [Listening mobile](listening-webkit-375.png)
- [Reading mobile](reading-webkit-375.png)
- [Listening AI desktop](ai-chromium-1366.png)
- [Listening AI mobile](ai-webkit-mobile.png)
