# Phase C — implementation and verification

Date: 2026-11-01. Implementation is in `web/`. No backend/SwiftUI/dataset/production environment changes, SSH, deployment, commit or push. `.env.local` preserved. No new dependencies.

## A. Implemented

Real Start/Continue integration, authenticated attempt route, full viewport exam, all three passages and all 40 question positions from backend snapshot, all 15 enabled question types. Typed content renders without raw HTML. Authenticated source PNGs reserve aspect ratio and expose explicit load error/Retry. Public parser rejects private answer-key fields, invalid IDs, missing assets and unknown types.

Existing saved answers initialize the controls. Basic serial saves debounce 600 ms; only an acknowledged mutation updates Saved. Changes during an in-flight request remain dirty and are sent next. Errors retain the in-memory draft; explicit Retry replays the exact event/payload. A 409 stops edits rather than overwriting another version. Network/token/body reads are bounded by the existing API client's 15-second timeout. Before-unload warns for unsaved edits; the in-app logo flushes before leaving and stays on error.

## B. Backend API

All use Firebase Bearer via the existing same-origin `/api/alua/*` proxy:

- GET `/api/v1/reading/books`: availability and learner-specific active IDs.
- POST `/api/v1/reading/attempts`: `{event_id, exam_id, mode:"full_exam"}`.
- GET `/api/v1/reading/attempts/{uuid}`: saved answers/state and public content snapshot.
- POST `/api/v1/reading/attempts/{uuid}/sync`: `{event_id,expected_version,answers}`.
- GET `/api/v1/reading/assets/{asset_id}`: authenticated PNG blob, object URL revoked on cleanup.

GET exam helper exists but the current screen uses attempt snapshot. No check/submit/result/history calls. No new endpoints or authentication policy changes.

## C. Reading coverage

Local ReadingCatalog audit: 72 extracted exams / 216 passages / 2880 positions, 63 enabled exams / 2520 positions, 538 enabled groups across 15 types. Manifest: 65 needs_review + 7 blocked; backend validation excludes two more exams (nine excluded total). All enabled tests remain not fully proofread.

All 15 types render and have interactive browser coverage using real public content. All 538 enabled groups pass parser/server rendering. Counts, variants and sample IDs: [PHASE_C_COVERAGE.md](PHASE_C_COVERAGE.md).

Tables/flowcharts/diagrams in the actual enabled data are source PNGs with numbered controls, not verified semantic layouts. Source-only choices without typed options use explicit letter fields beside original artwork; no choices are invented. Screen-reader semantics remain limited by source metadata. No enabled format is silently skipped.

## D. Attempts and existing progress

Start only on explicit click, after fresh availability/active-ID check. Existing IDs lead to Continue; multiple active IDs require explicit choice. Create event UUID is stored before POST and reused after an unknown outcome. Ref lock/shared promise protect repeated UI triggers; secure-origin Web Locks add same-origin coordination where available. Mount/refresh/rerender/passage switch never creates an attempt.

Backend idempotency is per event UUID; it does not enforce a unique active attempt per exam across independent devices. HTTP LAN does not provide Web Locks. Full cross-device start coordination belongs to D and is not claimed here.

Real LAN browser: authenticated catalog loaded; Cambridge 04 Test 1 displayed In progress; preparation displayed “Your existing progress is preserved” and enabled Continue test. Agent did not click Continue/Start, GET the attempt, write answers or finish it. Production data was not used as disposable QA data.

## E. UX

Desktop: simultaneous 50/50 Passage and Questions, separate overflow containers, no page scroll, keyboard/pointer separator limited to 40–60%. Passage switching restores each pane's scroll and last question focus; edits keep input DOM identity and do not jump the opposite pane. A−/A+ affects passage only. Source paragraph boundaries are retained while OCR soft line wraps reflow naturally.

Footer uses actual question numbers/ranges, answered/current/review states and All 40 dialog. Escape closes dialog and returns focus. Review marks remain local in memory. Mobile shows Text/Questions toggle and preserves both scroll offsets, including when the other pane is hidden. A hidden-pane scroll restoration issue found during testing was fixed before the passing suite.

## F. Verification and evidence limits

Executed successfully:

| Check | Result |
|---|---|
| `pnpm --dir web typecheck` | passed, strict TypeScript |
| `pnpm --dir web lint` | passed, zero warnings |
| `pnpm --dir web build` | passed, production Turbopack |
| `pnpm --dir web test:phase-c` | 16 passed |
| `pnpm --dir web test:phase-b` | 15 passed, existing regression suite unchanged |

C suite: six contracts + nine desktop tests (Chromium, WebKit, Firefox) + one mobile WebKit test. Desktop viewport sizes: Chromium 1440×1000, WebKit 1280×900, Firefox 1920×1080. Mobile: iPhone 13 emulation. Browser checks cover independent scrolling, stable focus/input identity, real content for all 15 families, actual PNG decoding, passage state restoration, question jumps/All 40/Escape, font size, drag/keyboard divider, no horizontal overflow, reload without create, simulated save failure/Retry and missing asset.

Contract checks cover all 63 public exams / 538 groups, malformed/private content rejection, saved answers, multiple-choice per-position mapping, CAS serialization, edits during flight, exact event replay, conflict protection, resume without POST and pending create UUID reuse.

**Isolation:** the C runner exports local public ReadingCatalog projections to a temporary copy of the app. Attempt IDs/answers/save acknowledgements are synthetic fixtures. Source texts and PNGs are actual local dataset content. No production accounts, attempts or writes are created. Fixture routes do not exist in the production app; temporary app/JSON files are removed by the runner. Screenshot artifact: ignored `.next/reading-qa-screenshots/exam-chromium.png` (fixture UI, not production E2E).

**Real checks:** existing authenticated user session, catalog/book/preparation in native Chrome over `http://192.168.10.18:3000`; Continue state confirmed. Production exam Start/resume/save/refresh and authenticated asset retrieval remain unverified end-to-end. WebKit tests are Playwright WebKit, not a claim of manual Safari certification. No production 60-minute exam was run. Simulated network/server errors are fault tests, not real production incidents.

## G. Remaining scope

D: durable offline draft/outbox, robust autosave across refresh/closing, multi-device conflict resolution/start coordination, background timer reconciliation and final server deadline/auto-submit UX. Current timer displays server_now/deadline_at, blocks inputs at zero and does not submit. Backend may enforce expiry/grade when its endpoints are requested under existing rules. Unsaved drafts/review/scroll are in memory only; current passage changes are not PATCHed.

E: Finish, grading/result presentation, correct-answer review, history. There is deliberately no Finish button. Terminal attempts show an explicit unavailable-for-editing state rather than recreating an attempt. Content proofreading/verified semantic source reconstructions remain dataset work outside this phase.

Implementation and isolated checks are complete; full production acceptance is pending the manual Start/Continue/save checks below. Do not treat the fixture suite as proof of production mutations.

## H. Manual QA

Preserve existing `.env.local`; no additional environment variables are required.

```bash
cd /Users/yeskendir/Projects/Alua/web
pnpm install --frozen-lockfile
pnpm dev --hostname 0.0.0.0
```

If a server already owns 3000, use it or stop that specific process first. Agent verification server is stopped at handoff.

1. Open `http://192.168.10.18:3000/login?next=%2Freading` and sign in (or restore existing session).
2. Open Reading → Cambridge 04 → Test 1: `http://192.168.10.18:3000/reading/cambridge-4/cambridge-04-test-01`.
3. Click Continue test for the existing attempt. Confirm the same attempt UUID and previously saved answers. If backend reports expiry, do not create a replacement silently.
4. Confirm desktop two columns; scroll each independently, resize divider by drag and keyboard arrows.
5. If editing this personal attempt is intended, answer several questions, wait for Saved, switch passages and return. Confirm inputs, review marks and both scroll offsets. The timer continues; no Finish action is available.
6. Open All 40; jump between passages and return. Press Escape and check focus.
7. Refresh only after Saved; confirm backend answers restored and attempt UUID unchanged. Review/scroll are local and may reset on reload.
8. On mobile/WebKit, toggle Text/Questions, rotate/resize and check input focus/overflow.
9. For network error QA, use a disposable authorized test environment: offline save must show unsaved/error + Retry; restoring network and retrying must not claim Saved before acknowledgement. Never close with an unsaved personal draft.
10. Start of a new production attempt is an explicit user action and begins its deadline. Test only when intentionally beginning that exam; do not create disposable production attempts or finish the existing one.
