# Alua Reading v1 — D / E / F verification

2026-11-01. Local implementation and acceptance preparation. This report supersedes Phase C's future-scope descriptions; earlier reports remain historical evidence.

## A. Final implementation

Reading now has durable answer drafts/outbox, bounded retry, CAS reconciliation, explicit conflict choices, persistent view preferences, stable passage highlights, server deadline reconciliation, confirmed Finish, server results, readonly review and paginated history. The approved home, catalog cards, renderer and simultaneous desktop columns remain. Listening/Writing/Speaking remain Coming soon.

No new runtime dependencies, PWA/service worker, independent grading implementation or authentication backend. No production users/attempts were created, edited, submitted or finished by this work. The existing Cambridge 04 Test 1 was not used for mutations.

## B. Frontend architecture and changed files

New core modules under `src/features/reading/exam/`:

- `draft-storage.ts`: native IndexedDB, per-UID/attempt/content-hash records and transactional tab leases.
- `draft-validation.ts`: validates restored IDs, revisions, events, scroll preferences and exact source quotes before allowing writes. Unreadable drafts are retained and editing pauses for recovery.
- `reliable-answers.ts`: current answers, durable local snapshot, acknowledged baseline, persisted exact outbox, lifecycle phases, reconciliation and Finish intent.
- `clock.ts`: conservative monotonic/wall elapsed helpers; deadline always comes from the server.
- `results.ts`, `records-page.tsx`: validated server result/history models and protected views.

Updated exam modules: `reading-exam.tsx`, `attempt-page.tsx`, `passage-pane.tsx`, `question-renderer.tsx`, `start.ts`, `models.ts`, `parse.ts`, `messages.ts`. Existing `answers.ts` remains as the small Phase C adapter used by its isolated renderer fixtures; the authenticated production attempt route constructs `ReliableAnswers`.

Auth updates: `features/auth/session.ts` invalidates private UI immediately, preserves drafts for a temporarily rejected session, clears the prior owner's data on account switch/logout, and never stores credentials in drafts. `profile-view.tsx` explains device cleanup; `messages.ts` distinguishes cleanup failure. Firebase SDK still owns token persistence/refresh.

Routes:

- `/reading/attempts/{uuid}` — edit/continue; terminal attempts link to their result.
- `/reading/attempts/{uuid}/result` — real terminal result.
- `/reading/attempts/{uuid}/review` — readonly two-column review.
- `/reading/history` — My attempts, 20 per page.

A small My attempts link is added to Reading. Scoped CSS adds Finish/dialog/result/review styles. `package.json`, `.gitignore`, test runners/configs and documentation are updated. No environment values were changed.

## C. Every backend change

1. `backend/app/modules/reading/schemas.py`: optional `CreateAttempt.reuse_active: bool = False`.
2. `backend/app/modules/reading/service.py`: under the existing per-learner PostgreSQL advisory lock, expire matching stale active attempts, then return an existing active attempt when `reuse_active=true`. Record the create event acknowledgement normally. No answer/state reset.

This gap was demonstrated in the original service: independent create UUIDs always constructed new rows. Web sends `reuse_active:true`; legacy requests retain their previous create behavior. The legacy default field is excluded from the fingerprint so pre-existing event replays keep the same hash. Existing historical duplicates are not deleted; the catalog still lets a user choose among existing active IDs.

New tests: `backend/tests/test_reading_web_release.py` (concurrent devices, legacy compatibility, expiry and ownership) and opt-in `test_reading_browser_integration.py` (real local HTTP + browser runner). No schema migration, grading changes, router changes, auth-policy changes or SwiftUI changes.

**Backend deployment is required before releasing this web version's new-test Start.** An old strict CreateAttempt schema rejects the new field with 422; the client does not silently fall back to unsafe creation. Existing Continue/sync/result/history endpoints already exist. Nothing was deployed.

## D. Actual API contracts

All routes require existing Bearer authentication and use the fixed same-origin Next proxy `/api/alua/*` → configured FastAPI `/api/v1/*`.

| Operation | Method / path | Request / semantics |
|---|---|---|
| Catalog | GET `/reading/books` | availability and learner-scoped active IDs |
| Start | POST `/reading/attempts` | event UUID, exam_id, full_exam, reuse_active:true |
| Continue/reconcile | GET `/reading/attempts/{id}` | public snapshot, answers, version, state, server timestamps; enforces expiry |
| Save | POST `/reading/attempts/{id}/sync` | exact event UUID, expected_version, question-ID → string map |
| Finish | POST `/reading/attempts/{id}/submit` | exact event UUID, expected_version; terminal acknowledgement |
| Result | GET `/reading/attempts/{id}/result` | only after terminal status; backend score and alternatives |
| History | GET `/reading/attempts?limit=20&offset=…` | owner-scoped pagination; GET enforces expiry |
| Assets | GET `/reading/assets/{asset_id}` | authenticated PNG → scoped blob URL |

The application does not call practice `/check` or invent result/grade endpoints. GET exam helper exists; the editor/review use the attempt's content snapshot. UI preferences/highlights are local; no new PATCH state contract was needed.

## E. Reliability

A record is keyed by Firebase UID + attempt UUID + content hash. It holds answers by question ID, a local snapshot revision/modified time, acknowledged version/baseline, pending event, Finish intent/submit event, conflicts and view state. ID tokens/passwords are absent. Local revision/time apply to the entire answer snapshot. Storage failures are explicit and do not become Saved.

Input updates memory immediately and queues an IndexedDB commit. Before any network mutation, its exact UUID/version/payload must commit locally. Writes are serialized. A 600 ms debounce sends only changed answers; edits during a request remain current and are sent after its acknowledgement. Unknown outcomes replay the same event. Retry backs off 1/2/4/8/16 seconds, five scheduled attempts per burst; reconnect/focus/manual Retry can resume. A final 401 refresh failure invalidates the rejected session while keeping its durable draft for the same identity.

On 409 version rejection, GET the current attempt and perform a three-way comparison against the acknowledged baseline. Independent changes merge; incompatible versions remain visible in an explicit choice dialog. Unordered multi-answer groups are treated as a semantic unit. The conflict itself is durable: refresh cannot silently turn an unresolved choice into an overwrite. Repeated concurrent conflicts are bounded per save burst. Other 409 codes are not treated as permission to overwrite.

Same-origin tabs use an IndexedDB lease with ownership checked inside the draft-write transaction. A second live tab is readonly; after closing/reloading a crashed owner, takeover waits for the short lease to expire (normally about three seconds). Losing ownership fences further writes and asks for reload. This works on HTTP LAN without Web Locks. Other browsers/devices are reconciled through backend CAS, not assumed to share local storage.

Answers/preferences/highlights survive normal refresh/reopen after local commit. Offline typing works in an already loaded/authenticated exam; reconnect resumes. A fresh browser start with no network is **not** promised: app code, exam snapshot and Firebase initialization are not an offline cache. No late local answer is claimed accepted after the deadline. Browser eviction/clearing or failure before the local transaction commits cannot be made lossless; pending device writes and unsaved answers warn on leaving.

Logout clears that owner's IndexedDB drafts/leases and hides private UI immediately. Account switch clears the previous owner's records. Cleanup errors are reported; Firebase sign-out still executes. Temporarily refreshed/rejected credentials do not delete the draft. Highlights/view state have no cross-device sync.

## F. Timer and completion

Display anchors to `server_now`/`deadline_at`; elapsed uses the larger monotonic/wall interval to catch sleep and prevent a backward system-clock change extending the interval. A forward clock change can pause conservatively until server reconciliation. Focus, visibility return, reconnect and a 30-second visible interval re-fetch authoritative state. Offline status suppresses attempted reconciliation until reconnect. Timer never resets the server deadline or displays negative time.

At zero, input pauses and GET attempt confirms expiry. Existing backend receipt-time checks under its transaction lock reject late sync and grade exactly once. Closed-browser expiry is enforced by existing GET/catalog/history/result/mutation operations; there is no new scheduler or claim that a database row changes while no operation runs. Reopening after the deadline cannot resume time.

Finish requires confirmation with answered/unanswered/review counts. It first persists intent, drains acknowledged sync, then persists and sends one submit event. Double-clicks cannot send a second lifecycle operation. Unknown submit remains FINALIZING/SUBMISSION_UNKNOWN, never an invented success. Retry/reload uses the stored event or a freshly observed terminal result. Unsynced answers block normal Finish; expiry may legitimately reject them. Results show retained differing local answers separately as **not included in the score**.

## G. Grading, review and security

Raw score, estimate, timing and accepted alternatives come exclusively from existing backend result data. Result parser requires an owner-authorized terminal attempt, matching UUID/exam/hash and all expected question IDs; it verifies response consistency without grading answers. No official band is invented below the server's supported range. Review disables answer controls; unordered groups explain that letter order does not matter. No generated explanations or analytics dashboard.

Existing server ownership is enforced in PostgreSQL queries by learner + UUID, not just hidden links. Backend tests exercise unauthorized access and unfinished result rejection. Public exam parser rejects private answer-key fields. Rich text is typed React content, never raw HTML. Redirects remain constrained by Phase B tests. Proxy target is fixed configuration, bearer auth is explicit, cookies omitted, private fetches no-store, assets private with Authorization Vary. Auth UID changes unmount private content; blob URLs are revoked on cleanup. No dataset/answer-key imports in production browser source/public assets; only terminal result responses expose correct answers.

The local browser integration uses a disposable enrolled test identity through the existing backend auth path. It does **not** claim a real Firebase production login. Firebase validation/provisioning regression tests remain separate. No Firebase project settings or backend security were relaxed.

## H. Executed tests

Recorded successful commands (exit 0). Browser fixture tests and real local backend tests are distinct:

| Check | Result |
|---|---|
| Typecheck / lint / production Turbopack build | Passed; zero ESLint warnings |
| Phase B regression | 15 passed |
| Phase C regression | 16 passed; 63 exams / 538 groups checked, all 15 types |
| D/E/F release suite | 30 passed: 12 contracts + 16 desktop fault-fixture scenarios + 2 mobile emulations |
| Final strengthened contract-only rerun | 12 passed, including mismatched terminal acknowledgement rejection |
| Backend Reading / Firebase / registration + safety additions | 25 passed, real disposable PostgreSQL; 19 pre-existing warnings |
| Real local HTTP browser integration | 2 browser scenarios passed (Chromium + WebKit); enclosing pytest 1 passed |
| Changed backend Ruff / Python compileall / git diff --check | Passed |

The full release suite runs with one worker and zero retries so foreground/timer scenarios do not compete across test windows. Earlier failures were corrected: hidden/reloading writer leases, persisted conflict recovery, offline reconciliation, and isolated-runner configuration. Two parallel Chromium timing failures passed targeted reruns; the final sequential full suite passed. Phase B initially encountered shared output-directory interference while separate runners were concurrent; release/integration now have distinct output directories and Phase B passed again. No existing failing assertion was removed.



- `pnpm --dir web typecheck`, `lint`, `build`: strict compiler, zero-warning ESLint, real production Turbopack build.
- `pnpm --dir web test:phase-b`: existing auth/catalog/transport regression.
- `pnpm --dir web test:phase-c`: existing 63-exam/538-group parser/render and Chromium/WebKit/Firefox/mobile interaction regression.
- `pnpm --dir web test:reading-release`: new persistence/lifecycle contracts + browser fault fixtures. These use real source content/PNG, actual IndexedDB and the production UI, but controlled auth/API responses. Terminal fixture results are generated by the actual Python scorer in the temporary export, not browser grading.
- `backend/.venv/bin/python -m pytest tests/test_reading.py tests/test_reading_web_release.py tests/test_firebase_auth.py tests/test_self_registration.py -q` from backend: real disposable PostgreSQL and existing grading/auth tests.
- `ALUA_RUN_READING_BROWSER=1 .venv/bin/python -m pytest tests/test_reading_browser_integration.py -q -s` from backend: temporary PostgreSQL, existing FastAPI via Uvicorn on loopback 3400, temporary Next app/proxy on 3300, no API mocks, Chromium + WebKit. Browser sign-in is a test identity stub with the actual local enrollment token; no production Firebase operation.
- Ruff on all changed backend Python files and `git diff --check`.

The integration runner refuses arbitrary upstreams and requires its disposable fixture token. Temporary apps/JSON are deleted; browser artifacts are ignored. Never run local browser integration against a configured production database. Normal pytest skips this opt-in browser wrapper unless explicitly enabled.

Measured one local integration run: exam ready plus authenticated PNG decoded in 2816 ms Chromium / 716 ms WebKit. These are single-machine observations, not production latency/SLA or load-test evidence. Input focus/DOM stability, scroll isolation, debounced writes and full renderer coverage have regression checks. Blob URL cleanup was reviewed in the asset component lifecycle. Scroll preference writes are throttled after scrolling, avoiding a React update on every scroll event. No unnecessary question virtualization.

## I. Remaining limitations and acceptance risks

| Severity | Item |
|---|---|
| High — release gate | Backend safety flag is not deployed. Deploy compatible backend before enabling new-test Start in production. No production rollout was performed. |
| High — acceptance pending | Real Firebase production Start → save → Finish → result, actual-device network/sleep and LAN acceptance require deliberate manual user actions. Existing personal attempt was not mutated. |
| Medium | No cold-start offline app/content/auth cache. Durable drafts survive reload but recovery needs the app and authorized snapshot to load. Browser eviction/clearing, uncommitted writes and storage failure remain explicit limits. |
| Medium | Highlights, review marks, font/split/scroll are per-device. Same-origin second tab is readonly; independent devices use explicit conflict recovery. |
| Medium | `reuse_active` is opt-in to preserve legacy behavior. Old clients may still explicitly create additional attempts. Existing duplicates are preserved and offered for selection. |
| Medium — content | All enabled tests remain not fully proofread; source-image tasks have limited verified semantic accessibility. No answer keys or source data were changed. |
| Low — validation coverage | Browser engines/emulations are tested, not a certification of physical Safari/iPhone/Android devices or real OS sleep/clock manipulation. No production load test, monitoring rollout or rights/deployment approval was performed. |

No known critical defect is intentionally accepted. Unverified production conditions are pending, not checked as passed. Storage/device limits are not a promise of perfect losslessness.

## J. Manual acceptance — real mutations explicitly marked

Start local web without overwriting `.env.local`:

```bash
cd /Users/yeskendir/Projects/Alua/web
pnpm install --frozen-lockfile
pnpm dev --hostname 0.0.0.0
```

Use an existing server if 3000 is already owned. Agent verification servers are stopped at handoff. No additional environment variable is needed; retain existing Firebase Web config and API base. Backend safety update must be released separately by the owner before a new Start can pass against production.

1. Open `http://192.168.10.18:3000/login?next=%2Freading`; sign in to the existing account. Check home/catalog and `/reading/history`.
2. Inspect Cambridge 04 Test 1 preparation readonly. **Continue loads a personal attempt and existing backend GET may enforce its elapsed deadline. Do not use it as disposable QA and do not Finish it for testing.**
3. Choose a test you intentionally want to begin. **Start creates a real attempt and begins its deadline.** Confirm one UUID across double-click/refresh/Continue.
4. **Editing saves real answers.** Enter answers in several families, wait for All answers saved, switch passages, use All 40, divider/keyboard, mark review and highlight text.
5. Refresh/reopen. Confirm same UUID and answers/preferences/highlights. Never intentionally close during an uncommitted device write.
6. On an authorized disposable exam/environment, disconnect briefly, edit, confirm Offline/Saved on this device, reconnect and observe acknowledged save. Try another tab (readonly) and another device; choose a conflicting answer explicitly. Do not use a valued personal draft for destructive fault QA.
7. **Finish is irreversible and grades the real attempt.** Inspect counts, cancel once, then deliberately confirm. Pending errors must block success. Confirm server result/raw score and estimate label; no invented result.
8. Open readonly review, check choices/alternatives and navigation, refresh the direct result URL, then history and its pagination. Back/Forward must not create an attempt.
9. Test expiry with controlled time in a local test environment, not by changing production data or waiting 60 minutes.
10. Confirm `/profile` logout clears local device drafts; sign in as another authorized account and confirm no prior-user data. Logout intentionally removes that owner's local-only drafts/highlights.
11. Repeat LAN access on physical Safari/iPhone and Chrome/Android if available, portrait/landscape, keyboard, background/sleep/reconnect. Those checks are still manual acceptance.

## K. Deployment readiness

Code is prepared for staged release/manual acceptance, subject to final recorded tests. Backend update required; **no database migration** and **no new environment values**. Deploy backend before web. Validate Start flag and existing Firebase identity integration in an authorized environment, then perform the manual mutation checklist. Public content publication/rights and production monitoring/operations remain owner decisions. No SSH, deployment, production migrations/settings changes or commit/push performed.

## L. Git / cleanup

Baseline had the entire `web/` directory untracked; it remains untracked, rather than staged/committed by the agent. Tracked modifications are the two backend source files listed in C. The two new backend test files are untracked. Web runtime additions/updates are listed in B; new tests/configs/runners are `reading-release-*`, `reading-local-integration.spec.ts`, `playwright.reading-{release,integration}.config.ts`, `test-reading-{release,integration}.mjs` plus the extended isolated Phase C runner/export. Existing test source assertions were preserved.

SwiftUI, Reading dataset, answer keys, backend authentication rules and `.env.local` were not edited. Dependencies remain the installed Phase C versions. Test servers stop automatically; temporary interrupted runner directories and failed debug artifacts are cleaned at completion. No commit/push.
