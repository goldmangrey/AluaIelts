# ALUA final source release — 7 November 2026

## Final production result

**SUCCESS for the authorized partial-source release at https://alua.study.** Strict original-layout verification remains 287/288; C14 is retained explicitly. The final public runs both passed: four source Exam/Review cases and Listening/Reading 15/15 + 40/40 answer cases, with zero image HTTP errors. The final answer run requires nonempty, decoded source images before navigation assertions. Desktop/mobile production Chromium, checksum rejection/recovery, reload, idempotency, server result counts, continuous audio and zero duplicate image GETs on prepared return passed.

- Backend: `source-fidelity-20261107-9689a3afffa3`.
- Worker: `2a752cce-890a-4860-9350-01741f5877bc`, 100% traffic.
- Cloudflare deployment: `44cf4940-0c27-4b0f-9524-efe8177fe82b`.
- Non-QA row fingerprints: unchanged. Health, 72/72 catalogs and runtime payload hashes pass.
- Rollback is available and was exercised twice during this release. No database restore occurred. The final healthy candidate was subsequently redeployed.
- Release commit: the commit containing this handoff; find it with `git log -1 -- docs/ALUA_FINAL_SOURCE_RELEASE.md`. Remote push is checked after creating that commit; no unrelated working-tree files are staged.

## Current decision

Three of the final four source cases are resolved. **287/288 Parts** have original-source verification; C14 T3 P1 remains an explicitly retained full-page fallback. This is an authorized partial-source release, not a claim of full-library source fidelity. Final deployment status and immutable version IDs are recorded in `listening-final-source-release/production-release.json` after the release checks finish.

| Part | Decision | Evidence |
| --- | --- | --- |
| C04 T1 P4 | FIXED / verified retained pixels | Hasanboy Cambridge 4 PDF, SHA-256 `5fffd323880791928596474e59b78aeb5aae7eeb2ac144d1b992e64853a30499`, physical page 12. Exact RGB equality to existing canonical page at 144 DPI; Q31–40 layout reviewed. NamDU candidate was a university-website printout and was rejected. |
| C06 T2 P1 | FIXED / verified retained pixels | Karatalk Cambridge 6 PDF, SHA-256 `91cccbe5d53c8ae3c236a1e6ac376ab3470bd5bb7d766bb0ad5b65a4174dc403`, physical page 29. Exact RGB equality; table headings and complete Q6–10 reviewed. |
| C07 T4 P1 | FIXED / new original page | PFC Cambridge 7 PDF, SHA-256 `34376d7bb8180d9e1846a505932b16a9512f1ff10c3e3201761d826138f26da7`, physical page 82, Q1–6. Clean original AND/OR instruction; existing Q7–10 page retained and compared to page 83. |
| C14 T3 P1 | UNRESOLVED original layout | Retained complete Flanders Conference Hotel fallback matches the pinned Voxcel PDF pixels; Studylib text corroborates fields. Both are retypes. Local original page 53 is damaged. No original geometry certification or invented text. |

Only one additional final-four PNG was needed: `asset-408349f54c4955e20cd153c541f90c2448383274d258c76c2f2059129988eba9` (1798×2444, 780683 bytes). It is a full original-page render at 250 DPI with a 12px safety margin. The packaged source PNG and deterministic importer registration preserve reproducibility without committing the third-party book. Source Fidelity V2 now adds 37 assets; all 45 Stage 2 repaired canonical images remain protected. C028 stays on its verified complete original-page fallback.

## Release-specific fixes

### Finish while a durable write is pending

The confirmation button previously became disabled during `localSaving`, including audio checkpoints. A write starting during a user click could discard the action. `pages.tsx` now permits invoking the existing safe submit controller during a pending write. It still freezes the final snapshot and waits for the durable commit before sending Submit. Storage failures, conflicts and finalizing states remain blockers. A real IndexedDB transaction is held open in the browser regression: the button stays actionable and no Submit is sent before the transaction is released. Six cases failed before the fix; all twelve Listening cases pass afterward, including 15/15, 40/40, 422 recovery, reload, edit and retry.

### Authenticated original-page image transport

The first production rollout exposed a real 504 for the new 780683-byte original page. The origin returned the correct SHA-256 in about one second; the Worker path exceeded the generic 12-second JSON budget. Both frontend and backend were rolled back to the prior working pair, without restoring the database or deleting any assets. A subsequent public C07 browser wait also timed out at 80 seconds, prompting a second paired rollback. No HTTP diagnosis was captured in that early browser run, so its exact cause is not asserted. Before the next activation, the complete four-Part Exam/Finish/Review flow passed on the immutable Worker preview with explicit HTTP diagnostics, including both C07 pages. Final public diagnostics are stored separately from those failed runs. The subsequent full public four-Part Exam/Review suite passed with no required-image HTTP errors; an independent public PNG probe returned the exact 780683-byte hash in 17.65 seconds. The earlier unexplained wait timeout is retained as a limitation, not assigned an invented cause.

The repair gives only validated Listening attempt image GETs a 60-second proxy budget and the user-scoped image cache a 75-second client budget. Submit, Reading and other JSON requests retain their original budgets. Private/no-store behavior, ownership checks, cancellation, path validation and bounded response sizes remain. The regression uses the actual proxy and cache; it verifies a body arriving after the JSON budget, unchanged mutation deadlines, explicit cancellation and URL cleanup. A separately uploaded Worker preview is checked before activation. The edge can be slow: the first complete preview download took 60.75 seconds including transfer to the client. No claim of instant cold full-page download is made; prepared returns use the existing bounded cache.

## Local gates

- 72 tests, 288 Parts, 568 groups; missing rendered materials, reviewed duplicates, page-order inversions and wrong-Part associations: zero.
- Full source suite: 2304 Chromium/WebKit desktop/mobile Exam/Review cases, exact DOM segment order, actual decoded source pixels, focus independence and original-page comparison evidence.
- Backend contract/source compatibility: 33 tests against disposable PostgreSQL.
- Image/importer tests: 12 tests; deterministic render/registration, protected original assets and keys, all 45 Stage 2 selections retained.
- Reading controller/contract fixtures were explicitly reviewed for the Atomic Submit acknowledgement, durable-save labels and deadline rejection flow; 12 standalone contract tests pass. These QA-only updates are included; unrelated screenshots remain unstaged.
- Listening real-backend browser submit: 12 cases; Reading: 6 cases, including 15/40 answers, deadlines and recovery. These are not synthetic state-only assertions.
- Navigation after transport repair: 8 cases, no extra image GETs on prepared return, separate scroll restoration, durable reload and two-tab editing lease.
- Player: 288 real waveform mappings and 8 real-MP3 browser cases. Compact V5: 10 engine/viewport cases, footer zero, player 108px desktop / 102px mobile.
- TypeScript, ESLint, Ruff and production/OpenNext build pass. Dataset technical integrity passes; legacy editorial-readiness warnings remain separate from source verification.

One navigation run during the preceding build/report activity failed with truncated JSON reads in the temporary Next fixture. A complete isolated rerun passed all eight cases; the failure is retained in the temporary release logs and is not reported as browser PASS. No runtime retry workaround was added.

## Isolated scope and reproducible frontend

Backend payload is exactly 55 hash-pinned files: two Listening runtime files, three metadata files, thirteen exam JSON files and 37 PNGs. Keys, grading, Reading backend, audio, transcripts, auth and database schema are unchanged. The candidate clones the prior release; no unrelated dirty working-tree files are deployed.

Frontend is built from the retained, hash-checked previous deployment plus the explicit twelve-file overlay in `frontend-build-scope.json` and the already-approved reliability/V4 scope. Physical existing dependencies are reused; no dependency upgrade or secret change. The prior deployed Reading CSS is intentionally retained. It is byte-identical to `git show 0f81eb4:web/src/features/reading/exam/exam.module.css` (SHA-256 `d8b56e8da5492738762ede8b9c17d35f00b6cc7969051831656a4842c726ec2b`). HEAD contains a different Reading modal-position rule; this Listening release does not deploy that unrelated styling change. A fresh whole-tree build is therefore not the release recipe: use the documented preserved CSS overlay and the approved file hashes.

## Backend release procedure and durable permission guard

`deploy/listening_source_release.py` is the narrow release-copy/drop-in procedure adapted from the existing hotfix workflow. It accepts a hash-pinned `--meta` file and `--stage`, `--activate`, or `--rollback`. It permits only the reviewed Listening runtime/data paths and refuses private keys/path traversal.

Staging backs up the whole previous backend release, clones it, verifies every payload hash and unchanged non-payload bytes, and preserves ownership/group/modes. It explicitly compares **every Reading path's owner/group/mode** and opens both 72-exam catalogs as systemd user `alua`. This prevents the prior Reading permission regression from recurring in this release procedure. New public assets are published additively before activation, including to the retained rollback tree so QA attempts created during a rollout remain readable after code rollback. No old image is removed.

Only `alua-api` is restarted. No FLORA/other service, `.env`, secret, auth configuration or database migration is touched. Activation checks health and both Atomic Submit OpenAPI schemas. Read-only row fingerprints establish no activation-time data mutations; a second fingerprint excludes only the guarded QA learner when comparing before and after smoke tests.

Candidate backend: `/opt/alua/releases/source-fidelity-20261107-9689a3afffa3`.
Previous backend: `/opt/alua/releases/submit-hotfix-20261107-e32ccee9a645`.
Backup: `/var/backups/alua/pre-source-fidelity-20261107-9689a3afffa3`.
Previous Worker: `df984c2e-270e-45a4-a4cd-a23a8746cd46`.
Rejected Worker after 504: `86ca4cc8-abe2-44e0-b6fd-e459119a2935`.
Image-budget preview Worker: `2a752cce-890a-4860-9350-01741f5877bc`.

Rollback from an active candidate (no database restore):

```sh
ssh -i "$HOME/Desktop/my-server/ssh-key-2026-10-22.key" -o IdentitiesOnly=yes ubuntu@141.144.194.152 \
  'sudo python3 /var/backups/alua/pre-source-fidelity-20261107-9689a3afffa3/release.py --meta /var/backups/alua/pre-source-fidelity-20261107-9689a3afffa3/release-meta.json --rollback'
```

From the isolated OpenNext build with the existing Cloudflare login, restore the retained Worker with:

```sh
OPEN_NEXT_DEPLOY=true node node_modules/wrangler/bin/wrangler.js versions deploy df984c2e-270e-45a4-a4cd-a23a8746cd46@100 --yes --message "Rollback Listening source release"
```

This uses the verified versions deployment mechanism. Keep all backups and additive image files. Never use `rsync --delete` or restore user-data tables.

## Production evidence and limitations

The dedicated learner is guarded by exact display name `ALUA QA Release` and matching learner ID. Smoke creates attempts through ordinary authenticated APIs only; it never writes directly to production tables. The script refuses mutations outside its just-created QA attempt. Tokens and answer text are excluded from reports. No real learner attempt is used.

`web/scripts/smoke-final-source-production.mjs` checks Listening/Reading 15/40 answers, deliberately invalid QA checksum → real 422 → editing/reload/retry, server final snapshot/checksum, same-event replay, changed-payload conflict, Results and Review. Four source cases additionally check canonical IDs, focus independence, source scroll and image decoding in Exam/Review. V5, continuous playback across visible Parts, zero repeat image GETs and desktop/mobile are checked. Production Chromium is separate from the broader local Chromium/WebKit suite.

Persistent artifacts under `docs/listening-final-source-release/`: source decisions/provenance; exact backend/frontend scopes; local gates; image origin/preview diagnostics; guarded browser results and screenshots; final immutable deployment IDs and preservation result. `production-source-browser.json` is the authoritative public four-source run; `production-answer-browser.json` is the stricter final public answer/navigation run (requires decoded images, not an empty-list check). Initial failures are named `initial-*-failure.json`; preview evidence is explicitly prefixed `preview-`. Full original-versus-selected Part evidence remains under `docs/listening-source-fidelity-v2/`.

Remaining limitation: C14 T3 P1 requires a clean authoritative Cambridge original to certify exact layout. Retain its complete fallback until obtained. Do not turn this exception into a PASS by OCR, AI-generated text or a similar exercise. The library is 287/288 source-verified even when the operational partial release is healthy.
