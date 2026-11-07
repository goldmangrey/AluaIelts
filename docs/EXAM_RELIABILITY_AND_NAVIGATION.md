# Exam reliability and Listening navigation — implementation handoff

**Production hotfix continuation:** see [ALUA_SUBMIT_HOTFIX.md](ALUA_SUBMIT_HOTFIX.md) for actual contract mismatch, 422 recovery, rollout/rollback incident and production evidence. The local-only statements below describe the earlier implementation phase.

Local implementation, 2026-11-07. No Oracle access, deployment, commits/push, production migrations or changes to real attempts/results. Existing Player V4 / waveform / answer-control work in this dirty checkout was preserved.

## Findings and evidence boundaries

- The initial actual-controller baseline with a blocked first sync retained **15/15 and 40/40** in both Listening and Reading. The reported “15 entered, 5 submitted” was **not reproduced by ordinary debounce/network delay**. It is not honest to identify debounce as its proven cause.
- Proven protocol weakness: both old submit contracts contained only UUID/version. The server graded its current saved answers, without receiving or acknowledging the user's final snapshot. A caller could finalize a 5-answer server snapshot while holding 15 answers locally. This is now covered by atomic submit contract tests, independent of autosave scheduling.
- Listening previously persisted only to localStorage, swallowed storage errors without blocking Finish, lacked a tab lease, and froze input only after awaiting flush. These were unsafe guarantees, although the baseline alone did not demonstrate the reported exact loss path. Listening now freezes before its first await and requires durable storage.
- Reading already had a durable delta outbox and three-way merge. Its final submit still lacked a bound final snapshot/checksum. Expiry could route straight to results with locally unaccepted answers. New acknowledgement checks and explicit rejection UI address these gaps.
- `questions.tsx: Asset` fetched and revoked its own blob URL on every mount/unmount. Part return therefore re-fetched images. `WorkspaceQuestions` explicitly reset left scroll and remounted the right pane without restoration. No exam JSON re-fetch is needed for a Part switch; the existing initial attempt already contains all four Parts.

## Save and submit protocol

1. `changeAnswer()` / `ReliableAnswers.change()` immediately update the authoritative in-memory answers. Every edit queues an immutable full durable record; writes are serialized. Rendering never waits for IndexedDB.
2. IndexedDB database `alua-reading-drafts` (existing schema/version) is reused. Reading key is `[uid, attemptId, contentHash]`; Listening key is `[uid, "listening:" + attemptId, contentHash]`. Record `attemptId` remains the original ID. Lease ownership is checked **inside the same transaction as each draft write**. An older persisted revision cannot overwrite a newer one.
3. Outbox records contain stable UUID, expected server version and exact payload. Reading stores `pendingRevision`, Listening `listening.pendingSerial`; the full record has a monotonic durable `revision`. Unknown outcomes replay the same UUID/payload. A later edit updates current answers but never changes the in-flight payload.
4. One network flight per controller. Sync drains newer edits after older acknowledgements. CAS rejection fetches current server state and reconciles against the old base. Incompatible changes block saving until explicit resolution; independent remote answers are preserved. Reading unordered multi-answer groups conflict as a semantic unit. Repeated automatic retries are bounded (five transient retries; three conflict retries).
5. Finish freezes a complete canonical snapshot **before any await**, disables input, and durably stores it. Existing work is reconciled. A final event contains every question ID (including empty strings), `answers_checksum`, `local_revision`, UUID and expected version. Listening also includes frozen navigation state. Full exams contain 40 IDs; Reading passage practice uses only its selected passage IDs.
6. `/listening/attempts/{id}/submit` and `/reading/attempts/{id}/submit` accept the final snapshot. In the existing learner-locked / row-locked DB transaction they validate scope, checksum, ownership, CAS, status and frozen-question restrictions, replace final answers, run the **unchanged grader**, finalize and record the idempotent response. No schema migration.
7. A successful reply includes authoritative `version`, `answers_checksum`, `final_snapshot_accepted: true`. Clients independently checksum returned answers and verify identity/status before showing success. A timeout retains the final event. Same UUID + different payload is rejected. An already-finished attempt with a different final snapshot conflicts; it is never rewritten.
8. Canonical checksum: SHA-256 of ASCII JSON ordered `[questionId, exactRawAnswer]` pairs, sorted by ID; non-ASCII UTF-16 units escaped as `\uXXXX`. This is integrity checking, **not answer normalization**. Unicode/BMP/supplementary characters are exercised against Python in integration tests.

### Deadlines and errors

Reading expiration still uses server receipt time **after acquiring the transaction lock**. Local timestamps never authorize late answers. Expired final submission returns `final_snapshot_accepted: false`, `rejection_reason: deadline_passed`; only previously server-accepted answers are graded. Unaccepted local answers remain in IndexedDB/in memory and the UI explains the distinction, with an explicit link to the server result. A different device's submitted snapshot is distinguished from deadline expiry.

Storage failure retains in-memory answers, shows a device-save error and blocks unsafe Finish/input; Retry device save attempts a full snapshot commit again. “Saving on device” takes priority over offline/saved labels until durable confirmation. Network failure never becomes a false successful Finish. Return to test is offered only before an uncertain final-submit event exists, and rechecks server status before unfreezing. Once a final event has an unknown outcome, retry that event instead.

### Legacy drafts and clients

- Listening reads the existing `alua:listening:<uid>:<attempt>:<hash>` localStorage record if no IndexedDB draft exists, validates it and copies the snapshot/outbox into IndexedDB. **The source record is not deleted.** Corrupt records are retained and unsafe saving is blocked.
- Reading uses its existing DB and keys. New metadata is optional for old drafts. A legacy version-only pending submit is reconciled against the current server; its exact old event is retained in `legacySubmit` when upgraded to a new atomic event.
- Legacy version-only backend submit remains accepted for existing clients. Its old event fingerprint is preserved by omitting newly added null fields. The new guarantee applies to the new web client/full-snapshot contract; old clients cannot retrospectively prove an untransmitted snapshot.
- An already-finished legacy result is never silently rewritten. Local retained data is not evidence that those answers were server-accepted.
- Cross-tab lease is bounded and transaction-fenced. A background/throttled tab may lose ownership to another tab; it becomes read-only, not a competing writer. Close the other editor and reload to reacquire. Reload waits briefly for the previous page's lease to expire. These lease waits do not provide answer-delivery guarantees; durable commits and CAS do.

## Listening image cache and view state

`ListeningAssetCache` is **private to a workspace identity** `(uid, attemptId, contentHash)` and indexes asset IDs within that identity. No shared public cache and no persistent image/exam cache were introduced. Review receives the attempt content hash in its result response; older/synthetic result responses fall back to the immutable asset metadata identity. Returning to a Part uses existing exam metadata and cached object URLs synchronously.

- Deduplicates concurrent loads; active consumers pin URLs. A single consumer unmount does not revoke a cached URL.
- LRU targets: **64 MiB desktop / 24 MiB mobile of encoded Blob bytes, 48 entries**. Decoded browser image surfaces are managed by the browser, not included in the Blob-byte budget. Visible pinned images are retained even if they temporarily exceed the target. Eviction releases unreferenced object URLs. Workspace teardown aborts pending requests and revokes all remaining URLs. StrictMode lifecycle is handled with owner retention.
- Prefetches the current exam's canonical image union only, with two workers; skips save-data/2G connections. No whole-audio prefetch was added. Cache pressure affects images, never the answer store.
- Original image dimensions reserve layout space. Errors remain retryable.
- `WorkspaceQuestions` keeps independent source/question scroll per Part/filter scope, current/focused question and mobile panel. Only the scrolled panel updates its saved position; hiding a mobile pane must not overwrite it with zero. Split widths are remembered per Part. Exam/Review remember the last question when using player Part navigation.
- Part/filter changes still use `visibleSourceMaterial()` unchanged: all required canonical materials for visible questions, in Stage 1 order. Active question focus does not replace images. Audio source and audio positions remain separate from visible Part.

## Implementation map

| File | Changed responsibility |
|---|---|
| `backend/app/modules/exam_integrity.py` | Canonical scope/checksum validation, independent of grading |
| `backend/app/modules/listening/{schemas,router,service}.py` | Optional atomic Submit, CAS/receipt replay, checksum acknowledgement |
| `backend/app/modules/reading/{schemas,service}.py` | Atomic Submit with unchanged receipt-time deadline/checked-answer policy |
| `web/src/features/exam-reliability/final-snapshot.ts` | Canonical final answer map, checksum, event type |
| `web/src/features/listening/draft.ts` | `initialize`, `persist`, `merge`, `flush/work`, `submit`, `returnToTest`: durable queue, migration, lease, immutable outbox, frozen submit verification |
| `web/src/features/reading/exam/{draft-storage,draft-validation,reliable-answers}.ts` | `browserDraftStore.write`, `validateDraft`, `record`, `finalEvent`, `confirmSubmission`, `acceptTerminal`, `work`, `finish`, `returnToTest`: durable revision/outbox and final validation |
| `web/src/features/reading/exam/{models,parse,reading-exam,messages}.ts*` | Contract fields, save states, explicit unaccepted/unknown outcomes |
| `web/src/features/listening/{models,pages}.ts*` | Contract fields, async initialization, disabled unsafe Finish, retry/return UI, last-question navigation |
| `web/src/features/listening/{asset-cache,questions,workspace-questions,review}.ts*` | `ListeningAssetCache.load/acquire/prefetch/trim/dispose`, `Asset`, `WorkspaceQuestions/saveView`, `ListeningReview/viewPart`: bounded cache and independent view state |
| `backend/tests/test_exam_reliability.py` | Atomic backend contracts and real TS-controller → HTTP → ASGI → disposable PostgreSQL tests |
| `web/scripts/check-exam-reliability.mjs` | Actual-controller fault matrix, backend integration driver, LRU/migration checks |
| `web/scripts/check-listening-navigation.mjs` | Real components + IndexedDB, counted asset requests and pane restoration |
| `web/tests/reading-release-*.ts` | Updated atomic acknowledgement fixtures and explicit durable/deadline UI assertions |
| `web/tests/listening.spec.ts` | Existing integration helper now waits for real IndexedDB acknowledgement, not vacuous localStorage checks |
| `web/scripts/check-listening-ui.mjs` | Existing sandbox now includes the shared durable modules and atomic mock acknowledgement |

The checkout also contains **earlier** Player V4/UI/style/waveform work. Do not infer all `git diff` files belong to this reliability task. No dataset/importer/image/audio/transcript/key changes are required by this implementation. Coverage JSON is regenerated evidence, not exam content.

## Verification and reproducible commands

Run from repository root unless noted. Only the disposable pytest cluster is used; never set production DB credentials.

```sh
node web/scripts/check-exam-reliability.mjs --unit
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_listening.py backend/tests/test_reading.py backend/tests/test_exam_reliability.py -q
ALUA_RUN_LISTENING_BROWSER=1 ALUA_LISTENING_TEST_GREP='owned verified lifecycle|preliminary, recovered' PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_listening_browser.py -q
node web/scripts/check-listening-navigation.mjs
node web/scripts/check-listening-player-v4.mjs
pnpm --dir web test:reading-release
node web/scripts/audit-listening-part-coverage.mjs --assert-complete
pnpm --dir web typecheck
pnpm --dir web lint
pnpm --dir web build
PYTHONPATH=backend backend/.venv/bin/ruff check backend/app/modules/exam_integrity.py backend/app/modules/listening/{schemas,router,service}.py backend/app/modules/reading/{schemas,service}.py backend/tests/test_exam_reliability.py
/tmp/alua-stage2-venv/bin/python -m unittest discover -s backend/scripts/listening_dataset -p 'test_visual_materials.py' -q
/tmp/alua-stage2-venv/bin/python -m unittest discover -s backend/scripts/listening_dataset -p 'test_image_repairs.py' -q
```

The integration pytest creates actual attempts in disposable PostgreSQL and invokes the actual TypeScript controllers through a localhost HTTP bridge into the authenticated FastAPI TestClient. It blocks the first sync, edits further questions and immediately freezes Finish; checks final **backend result rows**, not only client state. Includes 15/40, latest-value replacement, Part switch while saving, rejected post-freeze edits and cross-language Unicode checksum. The synthetic fixture owns its test-only identity; no external auth or real data.

### Recorded results

- Initial delayed-sync baseline: four 15/40 scenarios passed; exact original report not reproduced.
- Actual controller fault matrix: 19 cases passed (reload, timeout replay/reload, offline recovery, device-save failure, newer input during flight, incompatible device conflict, Reading expiry, semantic multi-select conflict, safe Return to test and bounded final CAS conflicts). Separate bounded-LRU/dedup/disposal and legacy-copy checks passed.
- Atomic backend tests: 15/40 direct final snapshots for both modules; exact-scope/CAS/checksum rejection without partial writes; replay and changed-payload rejection; late sync cannot alter final result; Reading deadline and frozen checked answers passed.
- Real controllers + actual PostgreSQL result: Listening 15/15, 40/40; Reading 15/15, 40/40. Delayed sync at 1 and 5 seconds.
- Existing Listening/Reading backend suites + new reliability tests: **28/28 passed**; existing Listening browser lifecycle/review selection passed across six Chromium/WebKit viewport projects (12 selected cases).
- Reading release suite: 42/42 passed (contracts, Chromium/WebKit desktop and mobile). Tests now assert explicit save labels and explicit navigation to the expired server result.
- Navigation: 8/8 Exam/Review × Chromium/WebKit × desktop/mobile; **0 additional asset GETs on return**, independent scroll restoration, durable reload, one writable tab, no horizontal overflow. Evidence: `docs/exam-reliability/navigation-qa.json`. These UI tests use synthetic local API state; they do not replace the separate real-PostgreSQL result tests.
- Player V4: 8/8 real local Cambridge audio browser cases passed; all 288 waveform/source hashes validated. Evidence: `docs/listening-player-v4/qa.json`.
- Stage 1/2: 72 tests / 288 Parts / 568 groups; missing states/Parts, duplicates, inversions and wrong Part = 0. Five visual-registry tests + three repair tests passed. This does not re-certify all physical crops.
- TypeScript strict, ESLint, Ruff and production build passed. Existing Alembic/Pydantic warning messages in backend tests are unchanged.

Local release gate: **GO** for the compatible backend + frontend change set. No tested answer-loss case remains; production itself is unverified.

## Limits and release handoff

- No production smoke/deploy was performed or authorized for this task. Desktop/mobile are Playwright Chromium/WebKit, **not physical iOS/Safari devices**. No long-running overnight crash/power-loss study was performed; recovery claims concern acknowledged IndexedDB commits.
- Images are memory-cached for a workspace, not offline-persisted. A full page reload legitimately fetches images again. Under eviction/slow-network policy a previously evicted image legitimately reloads.
- No application can retain an input lost before the browser acknowledges a durable commit if the browser/process is forcibly killed. UI explicitly reports the uncommitted interval and blocks unsafe Finish. Storage failures are not silently downgraded to “Saved”.
- The original 15→5 anecdote remains untraced to a particular original UI event. The strengthened contract now prevents success being confirmed for a different final snapshot, and no tested loss scenario remains. Do not present the original anecdote as reproduced.
- Known prior C014/C028 image exceptions remain unchanged; this task does not repair them.
- Future release: review this dirty checkout's exact file list and unrelated earlier work; use the existing deployment runbook, backup the previous backend/frontend release and dataset, deploy the backward-compatible **backend contract first**, verify it, then deploy the new web client. No DB migration. An old backend will reject the new final fields; **never downgrade silently to version-only submit**. Production smoke should use only an explicitly authorized test identity/attempt and verify checksum, result rows, new navigation and rollback. Do not print credentials or answer text in technical logs.

## Production hotfix completion — 2026-11-07

Backend `submit-hotfix-20261107-e32ccee9a645` and Worker `df984c2e-270e-45a4-a4cd-a23a8746cd46` deployed successfully after local gates. Dedicated QA production API and Chromium desktop/mobile 15/40 scenarios pass for both modules, including real 422 recovery, edit/reload/retry, canonical result rows and Review. Production schema mismatch is resolved; initial Reading file-ownership deployment failure was rolled back and corrected before the final paired rollout. No non-QA row changes in the protected smoke window. See [the complete hotfix handoff](ALUA_SUBMIT_HOTFIX.md) and `docs/exam-reliability/submit-hotfix-release.json` for exact scope, revisions, evidence and rollback. Earlier local-only/no-deploy statements above are historical.
