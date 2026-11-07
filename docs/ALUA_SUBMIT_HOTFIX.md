# ALUA Atomic Submit hotfix — 2026-11-07

## Confirmed failure and scope

The localhost Next proxy forwarded requests to the deployed Alua API, not the compatible local Python code. Production OpenAPI exposed version-only `Mutation` / `SubmitMutation`, with extra fields forbidden. The new client sends `answers`, `answers_checksum`, `local_revision`, and Listening `state`. Actual requests on the dedicated registered QA learner returned HTTP 422 with `detail[].type=extra_forbidden` and `loc=["body", field]` for these fields. No `final_answers` field is used. Rejected attempts retained their version/status/answers. Sanitized proof: [production-422-before.json](exam-reliability/production-422-before.json), [contract-before.json](exam-reliability/contract-before.json).

A second frontend defect treated definitive schema rejection like an unknown network outcome: the persisted final event kept inputs frozen. General Listening 422 messaging also incorrectly suggested the exam was unavailable. The hotfix restores editing for **explicit request/application validation rejection only**. Network timeouts remain frozen until authoritative status is reconciled.

## Implemented behavior

- `web/src/lib/api/client.ts`: classify Pydantic validation as `request_validation_error`; retain only sanitized `loc`/`type`, never answer input/validation context.
- `web/src/features/exam-reliability/submit-errors.ts`: narrow known-rejection predicate; other 422 application errors are not presumed safe.
- Listening `draft.ts` / Reading `reliable-answers.ts`: preserve rejected event as durable `rejectedSubmit`, clear active finalization/frozen state after definitive validation failure, retain all answers, permit editing and new Finish with a new UUID. Reload restores the rejection and answers without automatically resending the rejected event. A pending unknown Submit checks server status before retrying.
- Reading `draft-storage.ts`: compatible optional archived rejected-event field. Existing drafts remain readable.
- Listening `api.ts` / Reading `messages.ts`: actionable validation message instead of misleading exam-unavailable text.
- Backend Listening `schemas.py`, `router.py`, `service.py`; Reading `schemas.py`, `service.py`; shared `exam_integrity.py`: accept the complete canonical snapshot, validate IDs/checksum/CAS, finalize and grade within existing locked DB transactions, return authoritative answers/checksum/acceptance. Same UUID/payload replays; changed payload conflicts. Version-only old clients remain supported. Reading deadline and checked/frozen-answer restrictions stay server-authoritative. No migrations or grading changes.

## Local release gates

- Controller fault matrix: 25 scenarios plus bounded cache, legacy draft-copy and sanitized error checks PASS.
- Actual Python Listening/Reading/reliability suites: 29 passed; Ruff PASS.
- Real local Next + PostgreSQL Listening: 12 browser cases PASS (15/40, 422 recovery, edit/reload/retry and Review across six engine/viewport projects).
- Real local Next + PostgreSQL Reading: 6 browser cases PASS, including 15/40 recovery/retry and lifecycle on Chromium/WebKit.
- TypeScript, ESLint, production build PASS. Isolated production frontend build and OpenNext packaging PASS.
- Navigation 8/8 and Player V4 8/8 local browser cases PASS. Stage 1/2 coverage 72 tests / 288 Parts / 568 groups, all missing/duplicate/order/wrong-Part counters zero.
- Local offline, unknown timeout/replay, conflict, storage failure and Reading deadline cases are covered by the controller/backend suites. Production connectivity was not intentionally interrupted for real learners.

Reproduction/contract scripts: `web/scripts/check-exam-reliability.mjs --unit`, `backend/tests/test_exam_reliability.py`, `web/scripts/check-atomic-submit-contract.mjs https://alua-api.flora-flowers.kz/openapi.json`. Browser regressions are in `web/tests/listening.spec.ts` and `web/tests/reading-local-integration.spec.ts`.

## Release and rollback history

Source HEAD: `941fefabf1f60cf8601d503c01a8d3a881ce0006` plus explicitly hashed dirty changes; no commit/push. Backend payload is precisely six files in [submit-hotfix-release.json](exam-reliability/submit-hotfix-release.json). Frontend source changes are listed with hashes in [submit-hotfix-frontend-scope.json](exam-reliability/submit-hotfix-frontend-scope.json); unrelated Reading CSS, Home/Login, auth/provider configuration and datasets were excluded. The frontend includes the compatible earlier Listening Player V4, scoped image cache and reliability work.

Previous backend: `/opt/alua/releases/listening-visuals-20261106-61433b63`.
New backend: `/opt/alua/releases/submit-hotfix-20261107-e32ccee9a645`.
Backup: `/var/backups/alua/pre-submit-hotfix-20261107-e32ccee9a645`, including `backend-before.tar.gz`, metadata, activation fingerprints and `release.py`.
Only `alua-api` restarted, using a new systemd drop-in. Previous release/drop-ins preserved. No `.env`, keys, auth settings, migrations, datasets or other services changed.

**Real deployment incident:** first candidate activation passed health/OpenAPI and Listening QA, but Reading returned 500. Backend immediately rolled back successfully before any frontend activation. Root cause was release-copy ownership: Python `shutil.copytree` preserves modes, not UID/GID; private Reading catalog files became unreadable to service user `alua`. A read-only/pure grading diagnostic passed, and catalog construction exposed `PermissionError`. The candidate's copied files/directories were restored to original UID/GID; new helper gets app ownership. Release staging now preserves ownership. A dry submit with transaction rollback passed against the corrected candidate, followed by successful reactivation and real Reading Submit. Neither grading nor catalog bytes were changed to fix deployment permissions.

For rollback, existing backed-up `release.py --rollback` disables only the hotfix drop-in and restarts `alua-api`, restoring the previous release. Frontend rollback uses the retained previous Worker version. Because the previous backend does not accept atomic fields, **roll frontend back first**, verify it, then roll backend back. Never restore production DB just to roll back code. The first backend-only rollback was executed and health checked; a full paired rollback was not required.

Previous Worker: `29ce57d8-7263-4957-b3e9-863362890d02` (deployment `b4561c9f-4c4e-44b9-a223-e92a5334c8b7`).
New Worker: `df984c2e-270e-45a4-a4cd-a23a8746cd46` (deployment `01db8273-ead6-4afb-b1f5-5f094b65f9a1`, 100%).

OpenNext build succeeded. Its deployment subprocess encountered an existing broken Corepack pnpm path before Worker activation; after static-cache preparation, deployment used the same built OpenNext worker via `OPEN_NEXT_DEPLOY=true node node_modules/wrangler/bin/wrangler.js deploy --keep-vars` (OpenNext's documented internal recursion guard). Runtime vars retained. Assets uploaded before Worker activation. Deployment CLI logs remain private in `/tmp/alua-submit-hotfix-*.log`; no secrets were printed.

## Production verification

Only the separately registered **ALUA QA Release** learner was used, guarded by exact Firebase display name and `/me` learner identity. No supplied password was used or retained in the repository. Tests create attempts through normal authenticated APIs, never direct DB writes. Browser requests reject mutations outside their newly created QA attempt.

- Actual API Submit: Listening 15/15 and 40/40; Reading 15/15 and 40/40, confirmed from backend result rows, exact checksum and returned canonical answers. Same-event replay PASS, changed-payload conflict PASS, old version-only Submit PASS. Previously rejected attempts finished successfully after backend update. [production-submit-after.json](exam-reliability/production-submit-after.json).
- Deployed public OpenAPI now advertises both compatible submit schemas: [contract-after.json](exam-reliability/contract-after.json).
- Browser results and final status are recorded in [production-browser.json](exam-reliability/production-browser.json) and [submit-hotfix-release.json](exam-reliability/submit-hotfix-release.json); do not infer browser PASS from the local/API suites alone.
- Production URL: https://alua.study.

The guarded production runner is `web/scripts/smoke-submit-hotfix-production.mjs`; it requires a private short-lived QA Firebase session file at `/tmp/alua-submit-hotfix-qa-private.json`. Never substitute a real learner session or commit that file. Test credentials/tokens and attempt payload files must remain private and be removed after verification.

Known image exceptions C014 (source scan damage/watermark) and C028 (full original retained) are unchanged. Physical Safari/iOS and long-duration production offline/crash behavior are not claimed verified. This release does not certify every legacy result visually; read-only QA result reopening and non-QA table fingerprints provide the stated preservation evidence.

### Final outcome: SUCCESS

- Production Chromium: **4/4 PASS** — Listening 15 desktop / 40 mobile; Reading 15 mobile / 40 desktop. Actual backend checksum-validation 422 was induced by changing only the QA wire request checksum; no mock successful submit. All recovered editable inputs, retained edited answers after reload, used a fresh event and produced the correct 15/40 backend result rows. Exam/Review PASS. No browser page errors.
- Listening Player V4 continued playing through Part browsing; duplicate GETs for prepared assets on return **0**. The runner explicitly waits for question DOM and image decoding before counting repeat navigation, so unfinished first-load prefetch is not misclassified as cache loss. Reload correctly starts a new scoped image cache.
- Production mobile Reading uses its existing Questions panel; it is not visible by default while the Passage panel is selected. The browser runner selects it explicitly, including Review. Early harness attempts missed this step and required correction; this was not a product failure or an application code fix.
- Health, auth, 72 Listening / 72 Reading catalogue entries PASS. Public submit schemas PASS. Both new and legacy submit formats verified on the dedicated QA learner.
- Non-QA Listening/Reading attempts, mutation receipts and Firebase identities have identical before/after read-only row fingerprints across the browser smoke window: [non-qa-data-preservation.json](exam-reliability/non-qa-data-preservation.json). Activation before/after DB fingerprints also matched before QA operations. Existing QA results reopen successfully; real learners' results were never mutated or used for smoke.
- `alua-api` active/healthy; all six deployed backend file hashes match payload; prior release, backup archive and rollback script retained. No exception indicators in `alua-api` journal since corrected final activation (access logging is disabled; HTTP/browser assertions supply endpoint evidence).
- Final deployment readiness: **GO**, backend + frontend **SUCCESS**. No unresolved Submit blocker. First backend-only rollback **COMPLETED**, followed by corrected reactivation; final rollback **NOT NEEDED**.
- Production WebKit was **NOT VERIFIED**; local WebKit scenarios passed. No physical Safari/iOS claim. Network/offline/deadline fault injection is local, not a production outage test.

Screenshots: [Listening desktop](exam-reliability/production-listening-desktop.png), [Listening mobile](exam-reliability/production-listening-mobile.png), [Reading desktop](exam-reliability/production-reading-desktop.png), [Reading mobile](exam-reliability/production-reading-mobile.png).

Emergency commands (existing access only; do not execute unnecessarily):

```sh
# Frontend FIRST if reverting to the old version-only backend.
# Run in the prepared release's web directory with its authenticated Wrangler:
node node_modules/wrangler/bin/wrangler.js rollback 29ce57d8-7263-4957-b3e9-863362890d02 --name alua-ielts --message 'Revert paired submit hotfix'
# Verify old frontend activation, then restore backend, preserving DB:
ssh -i "$HOME/Desktop/my-server/ssh-key-2026-10-22.key" -o IdentitiesOnly=yes ubuntu@141.144.194.152 'sudo python3 /var/backups/alua/pre-submit-hotfix-20261107-e32ccee9a645/release.py --rollback'
```

The rollback helper still reads `/tmp/alua-submit-hotfix-meta.json`; its retained exact copy is `release-meta.json` in the same backup. If `/tmp` was cleared, restore that **metadata file only** to the expected path before invoking the helper. Never replace production `.env` or restore the DB. The previous Worker is retained in Cloudflare version history; full paired rollback was documented, not executed after successful final smoke.
