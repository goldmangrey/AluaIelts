# Listening Compact Exam V5 — local implementation, 2026-11-07

Variant A is implemented for **Listening Exam only**. No deployment, commit, push, backend/Reading/controller/dataset/audio/image/secret changes were made by this task. The checkout already contains earlier reliability/player changes; they were preserved.

## Behavior and implementation

- `pages.tsx: Workspace`: 44 px header with Library, dynamic Cambridge/Test, Questions and Finish. No Exam footer or previous/next buttons. Finish still invokes the live `ListeningDraft.submit()`; answers are never copied into a UI-owned final payload. The existing confirmation dialog retains the unanswered count. A ref guard and local busy flag prevent repeated submission while the actual submit call runs; its `finally` releases the UI busy flag on failure. Unknown outcomes retain the controller's frozen snapshot and allow safe Retry Finish through the existing protocol.
- `workspace-navigator.tsx: WorkspaceNavigator`: optional `placement="header"` uses an accessible native modal dialog with 40 question buttons, answered/current states from existing props, one-click navigation, Escape/outside close, close button and explicit focus restoration across Chromium/WebKit. Existing Review footer remains unchanged. No new answer/current-question state.
- `player.tsx: Player` + `player.module.css`: optional `compact` presentation class; desktop 108 px, mobile 102 px. Audio-source/progress/Moment logic is unchanged. Global keyboard shortcuts now respect `event.defaultPrevented`, so divider Arrow keys resize without also seeking audio; a browser regression checks both width and unchanged playback time. White floating V4 card, green 48/44 px Play, skip controls, divider, real waveform and four Part segments remain. Review keeps original dimensions. No waveform metadata or audio mapping changes.
- `workspace.module.css`: scoped Exam header/actions, dialog, compact error banner and reduced player wrapper spacing. Existing flex `100dvh` / `min-height:0` workspace, 55/45 split, divider, independent panel scrolling and Part-scoped view/cache state are retained.
- Routine save statuses stay in the controller but are absent from the Exam presentation. One banner shows actionable device failure, conflicts, another-tab read-only state, sync/offline failure, rejected/unconfirmed submission or explicit Finishing. A presentation-only editor subscription keeps a sync warning through retry/pending states and clears it only after acknowledged saving. Local-saving warnings do not claim new inputs are already durable. Storage failure takes priority and exposes Retry device save; Finish remains disabled.

## Measured before / after

Measurements use actual browser DOM, original pre-change component fixture and updated components with the same Cambridge 04 Test 1 data. Real local MP3 playback metadata and original image pixels are loaded; synthetic API/auth isolate the UI fixture from production. These measurements are not backend persistence proof.

| Viewport | Header | Player | Footer | Test workspace | Gain |
|---|---:|---:|---:|---:|---:|
| 1440×900 | 36 → 44 | 148 → 108 | 61 → 0 | 618 → 729 | **111 px** |
| 1366×768 | 36 → 44 | 148 → 108 | 61 → 0 | 486 → 597 | **111 px** |
| 1280×720 | 36 → 44 | 148 → 108 | 61 → 0 | 438 → 549 | **111 px** |
| 390×844 | 36 → 44 | 136 → 102 | 61 → 0 | 538 → 643 | **105 px** |
| 375×667 | 36 → 44 | 136 → 102 | 61 → 0 | 361 → 466 | **105 px** |

Both engines match the after measurements. Workspace bottom equals viewport bottom at every size; no horizontal overflow. Mobile includes the existing Source/Questions tabs. Actual gain is 111/105 px, **not** an asserted 150–180 px.

Evidence: [before.json](listening-compact-v5/before.json), [browser-qa.json](listening-compact-v5/browser-qa.json), [measurements.json](listening-compact-v5/measurements.json).

Screenshots: [desktop before](listening-compact-v5/before-1440x900.png), [desktop after](listening-compact-v5/chromium-1440x900.png), [mobile before](listening-compact-v5/before-390x844.png), [mobile after](listening-compact-v5/chromium-390x844.png). Other tested sizes and WebKit screenshots are in the same directory.

## QA and evidence boundaries

- Compact layout + question dialog/keyboard/Finish dialog/silent-status checks: **10/10**, Chromium and WebKit at all five viewports.
- Real local Next + FastAPI + disposable PostgreSQL: 15/40 rapid answers, backend result counts, first 422 rejection, editing recovery, reload, new event retry and Review; 12 atomic cases across six engine/viewport projects. The accompanying six silent-save/error/Finish-dialog cases passed. These use the real submit endpoints and scorer, not synthetic successful responses.
- Explicit IndexedDB `QuotaExceededError` injection: six browser configurations verify the device-save warning, visible Retry and disabled unsafe Finish. The initial assertion matched Next's separate route-announcer alert as well; it was corrected to scope to the Exam alert, without application changes.
- Additional real-backend compact layout/resize/navigation suite: **6/6 PASS**; divider Arrow keys change 40→42 without changing audio time, drag and reset remain functional. Total real-backend browser cases: **30 PASS**. [functional-qa.json](listening-compact-v5/functional-qa.json).
- Navigation/cache: **8/8** Exam/Review × Chromium/WebKit × desktop/mobile. Zero additional asset GETs on return; separate panel scroll restoration, durable reload and single writable tab pass. [navigation-qa.json](exam-reliability/navigation-qa.json).
- Player V4: **8/8** real local audio browser cases, all **288** waveform/source mappings validated; progress/reload, independent audio/visible Part, seek, natural end, AI Play/Loop Moments and Exam/Review preserved. [qa.json](listening-player-v4/qa.json).
- Reliability controller fault matrix: 25 cases plus bounded-cache, legacy-draft and sanitized-error checks pass. Reliability state machine was not modified.
- TypeScript strict, ESLint, production build and `git diff --check` pass. Existing Alembic/Pydantic warnings in the isolated backend harness are unrelated and unchanged.

Reproduce from repository root:

```sh
node web/scripts/check-listening-compact.mjs
ALUA_RUN_LISTENING_BROWSER=1 ALUA_LISTENING_TEST_GREP='atomic hotfix|exam UI: centered Finish|compact V5 device|V5 compact layout' PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_listening_browser.py -q
node web/scripts/check-listening-navigation.mjs
node web/scripts/check-listening-player-v4.mjs
node web/scripts/check-exam-reliability.mjs --unit
pnpm --dir web typecheck
pnpm --dir web lint
pnpm --dir web build
```

The compact browser script requires existing local audio at `~/Desktop/Listening` (override `ALUA_LOCAL_LISTENING_AUDIO`). Fixtures/logs stay in the OS temporary directory; only useful QA artifacts are stored in the repository. `--before` measures a pre-change fixture when `ALUA_COMPACT_BASELINE_FIXTURE` points to one; running it against current components does not reconstruct historical UI. The preserved before evidence is the comparison baseline.

## Files in this task

Product: `pages.tsx`, `player.tsx`, `player.module.css`, `workspace-navigator.tsx`, `workspace.module.css` in `web/src/features/listening/`.

QA: `web/tests/listening.spec.ts`, new `web/scripts/check-listening-compact.mjs`; existing `check-listening-player-v4.mjs` and `check-listening-ui.mjs` update the renamed Finish selector. Verification artifacts and this handoff are under `docs/`.

No `draft.ts`, Reading component/controller, image resolver, cache implementation, backend contract, grading, data or audio files were changed for V5. Existing earlier dirty changes remain present. Production was not contacted by QA and was not deployed.

Physical Safari/iOS devices, mobile browser chrome changes and production are **NOT VERIFIED** for V5. WebKit results refer to installed Playwright WebKit. Review/Results were preserved, not redesigned. Known C014/C028 source-image limitations remain unchanged.
