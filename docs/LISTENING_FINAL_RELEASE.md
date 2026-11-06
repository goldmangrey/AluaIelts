# ALUA FINAL RELEASE RESULT — 2026-11-06

Production: **https://alua.study**. Stage 3 **GO**, Stage 4 **SUCCESS**. Backend and Cloudflare are active. This is an actual production release and authenticated production smoke, not a local-only result. No commit/push or DB migration.

## Stage 3 — final release gates

| Gate | Result |
|---|---|
| Tests / Parts / groups | **72/72 · 288/288 · 568/568** |
| Missing rendered coverage / problematic Parts | **0 / 0** |
| Duplicate pairs / order inversions / wrong Part | **0 / 0 / 0** |
| New PNG hash/decode/dimensions/manifest | **45/45 PASS** |
| New PNG visual comparison with original pages | **45/45 reviewed**, no newly selected damaged crop |
| Importer reproduction | **72/72 exam JSON byte-identical**, **45/45 PNG hashes identical** after a complete temporary import |
| Dataset/schema validator | **PASS**, technical_integrity=true, errors=[] |
| Python runtime tests | **20 PASS**: Listening lifecycle/ownership/snapshots and AI contracts, disposable DB |
| Dataset/importer regression tests | **32 PASS** |
| Ruff | **PASS**: Listening modules and dataset scripts |
| TypeScript / ESLint | **PASS** |
| Backend syntax build | **PASS**, compileall into temporary pycache |
| Next production build / OpenNext Worker packaging | **PASS** |
| Chromium desktop Exam/Review | **30/30 local mode cases PASS**, including C014/C028 |
| Chromium mobile / WebKit desktop / WebKit mobile | **18/18 local mode cases PASS** |
| Release gate | **GO** with documented C014/C028 limitations |

All 45 approved images were compared again against their complete original material (eight grouped comparison sheets). An additional original-raster boundary check found no dark text/line crossing at the new top/bottom crop boundaries. Hash/decode alone was not treated as visual evidence. No crop selection or range/order changed during final QA.

Browser QA used the real ListeningPage/Workspace/Draft/Navigator and ListeningReview in the existing disposable fixture. It covered Part changes, group changes, independent columns, synthetic API save acknowledgement, return to an earlier question with the entered answer, complete image union, loaded assets and image enlargement. Mobile is a 390×844 viewport/emulated touch; WebKit is installed headless WebKit, not a physical iPhone/Safari certification.

Mandatory desktop cases include C04 T1 P1, C05 T1 P1, C09 T2 P2, C14 T2 P2, C18 T2 P4, C19 T3 P1, C07 T4 P1 and C06 T3 P3. Additional image repair cases include C05 T4 P2, C11 T3 P3, C18 T3 P1, C19 T1 P2 and C21 T2 P3.

### C014 — not repaired, but the task remains usable

C07 T4 P1 retains its complete full-page fallback. The source scan has damaged pixels in part of `AND/OR`; it is **not** declared physically repaired. Its existing question header already displays the full verbatim instruction, `Write NO MORE THAN THREE WORDS AND/OR A NUMBER for each answer.` This was checked in the dataset and actual Exam/Review rendering, including mobile/WebKit. The form and all required ranges remain available. No instruction was invented, rewritten, OCR-replaced or AI-generated. This is a known scan quality exception, not an unreadable task constraint in the current UI; it therefore does not block this release. A clean original is still needed to close the image repair finding.

C028 (C06 T3 P3) remains UNCERTAIN as a tight crop. Its complete original page is canonical, so no task material is lost and it does not block release. Neither exception was silently marked repaired or disabled.

## Stage 4 — production deployment

| Item | Before → after / result |
|---|---|
| Backend | `/opt/alua/releases/listening-c21-repair-20261106-599d5df` → **`/opt/alua/releases/listening-visuals-20261106-61433b63`** |
| Cloudflare Worker | `alua-ielts` |
| Worker version | `01f5530e-d611-40fd-9bb2-38646d18609c` → **`29ce57d8-7263-4957-b3e9-863362890d02`**, 100% |
| Cloudflare deployment ID | `cc6514ee-1105-437e-b080-cb67d5092552` → **`b4561c9f-4c4e-44b9-a223-e92a5334c8b7`** |
| Services updated | Only `alua-api.service` release path and existing Cloudflare Worker |
| API/public health | **PASS** |
| Asset availability | **PASS**, scope below |
| Actual production Exam / Review | **PASS / PASS** |
| Existing results / saved answers | **PASS**, full-row fingerprints unchanged |
| Rollback | **NOT NEEDED**; prepared rollback preflight **PASS** |

### What actually ran

1. Read current service WorkingDirectory/ExecStart/drop-ins and current Worker deployment. Git branch remained `main`, HEAD `599d5df`. Unrelated pending work was identified and excluded.
2. Built an isolated frontend from HEAD plus Listening files and the documented already-deployed AI provider/API carry-forward. Pending Reading UI edits were excluded; Home/Login match HEAD. Production environment files, secret values, users and auth configuration were not edited. Public build output contains no source maps, transcripts, private keys or answer-key artifacts.
3. Used the established Oracle release-copy/systemd drop-in workflow. Retained the entire preceding backend release, and created a separate private Listening dataset archive under `/var/backups/alua/pre-listening-visuals-20261106-61433b63/`. Existing 14 daily encrypted backups remain present; no retention/pruning or database restore was run.
4. Copied the current backend release, overlaid **134 explicitly hash-listed files**: 72 exam JSON (all Stage 1 metadata changes were still local, including the 29 Stage 2 exams), two schemas, manifest/asset QA registry, 45 new PNG and matching offline importer scripts/recipes. Question/answer content in all 72 exams was compared with the preceding production release after removing only visual fields and proved identical. All other copied backend files, including runtime app code, keys, transcripts, audio and configuration, were compared unchanged.
5. Before activation, the candidate's real Catalog.asset loader resolved all **464 unique canonical assets**, including **45 new PNG** with matching hashes/dimensions. The new assets were present before switching the active application.
6. Activated only `/etc/systemd/system/alua-api.service.d/zzzzzzzzzzz-listening-visuals-20261106.conf`, restarted only `alua-api`, and checked its actual loopback health endpoint. No dependency change or migration was needed.
7. Built Next with webpack and the same standalone settings used by OpenNext, then packaged/deployed through existing OpenNext/Wrangler with `--keep-vars`. Initial isolated-build failures were tooling/path issues (Corepack launcher, symlink/root tracing); corrected in the temporary build environment. No application workaround was introduced. The final production build and Worker packaging completed successfully before deployment.
8. Ran actual authenticated API and Chromium smoke on **alua.study** with an existing identity and existing attempts. No test user or attempt was created. Temporary token files were deleted after the smoke; credentials/tokens were never written into the repository or release evidence. Browser mutation requests for real attempts were guarded; one focus-navigation autosave was intentionally blocked rather than changing a real attempt. Actual autosave was validated separately by local real-component synthetic sync and disposable-backend tests.
9. Compared full-row aggregate fingerprints before and after, checked API service error journal count (0), and retained rollback instructions/assets. No Flora service/database or other application's infrastructure was touched.

### Production smoke evidence and precise scope

- `/api/alua/health`, existing-identity `/me`, Listening catalog **72 entries**, all **29 changed exam detail endpoints**, all **45 new PNG references**: PASS.
- Real production Exam displays two source images simultaneously with ten questions; focus actually moved between different groups and kept the same ordered IDs/source scroll. Review was moved to Part 2 and also tested across groups. Source is left, questions right. Browser page errors: **0**. Production screenshots mask the real answers panel.
- **45/45 new PNG** were verified on Oracle by the production Catalog.asset loader and in authenticated exam HTTP metadata. A historical snapshot image was additionally downloaded through its actual protected asset HTTP route and hash-checked. We did **not** create a new real attempt just to fetch all 45 through attempt-specific HTTP routes; old attempts deliberately keep immutable allowlists and use compatible full-page alternatives. This is not a claim of 45 new-image HTTP requests.
- Existing completed Review and existing in-progress Exam opened using real production API/auth. Historical records were not regraded/recomputed. No answers were entered on production.
- Public Home, Login, Reading, Listening, Speaking and Writing shells returned HTTP 200. No browser page error or observed API 5xx. Full historical Worker logs were not enabled/exported; existing observability configuration remains unchanged.
- Audio/AI explanation/Play Moment/Loop Moment were not freshly exercised as playback/provider tests. Their runtime/data were preserved, and relevant Python AI contracts pass. No claim of a new production audio/AI certification is made.

### Data preservation

| Table | Before count | After count | Full-row digest |
|---|---:|---:|---|
| listening_attempts | 16 | 16 | identical |
| listening_mutations | 292 | 292 | identical |
| reading_attempts | 28 | 28 | identical |
| reading_mutations | 324 | 324 | identical |
| firebase_identities | 3 | 3 | identical |

Exact aggregate hashes are in [data-preservation.json](listening-final-release/data-preservation.json), without record payloads, raw answers or credentials.

## Rollback, if later required

The prior release and old Worker version remain available. The prepared backend rollback is **not executed**; its default validation completed PASS. It copies only the new content-addressed images into the prior release if necessary before reverting, so any real attempts created after this deployment can still resolve their immutable new-image references. It never overwrites existing image bytes and never restores the database.

On the Oracle host, validate or apply:

```sh
sudo python3 /var/backups/alua/pre-listening-visuals-20261106-61433b63/rollback_backend.py
# Only when rollback is required:
sudo python3 /var/backups/alua/pre-listening-visuals-20261106-61433b63/rollback_backend.py --apply
```

On the configured Mac checkout, from `web/`:

```sh
pnpm exec wrangler rollback 01f5530e-d611-40fd-9bb2-38646d18609c --message 'Rollback Listening visual release' --yes
```

The backend script deactivates only this release's drop-in, reloads/restarts only alua-api and waits for health. All original lower-priority drop-ins/environment files remain. After either rollback, repeat production health, existing Exam/Review and fingerprint checks. No user data migration/restore is part of this procedure.

## Changed local files and evidence

Final QA changed only formatting/import order in `backend/scripts/listening_dataset/image_repairs.py`, `repair_images.py`, `test_image_repairs.py`, `importer.py`; corresponding generator checksums in the dataset manifest were refreshed. No image byte/selection changed during final QA.

Added/extended release QA scripts:

- `web/scripts/audit-listening-part-coverage.mjs`: final known-exception browser cases.
- `web/scripts/check-listening-release-browser.mjs`: reuses existing disposable fixture for WebKit/mobile/Part/save-return checks.
- `web/scripts/smoke-listening-production.mjs`: real production read-only authenticated browser checks; takes a temporary private token file, never logs tokens or permits attempt mutations.

The deployed scope comprises Stage 1 resolver/UI/metadata and Stage 2's 45 assets, 72 required Stage 1 exam projections (29 include Stage 2 substitutions), schemas/manifest/registry and offline importer recipes/scripts. The full Stage 2 file/asset list remains in [its handoff](LISTENING_STAGE2_IMAGE_REPAIR.md) and [repair manifest](listening-visual-audit/stage2/repair-manifest.json). No unrelated local changes, commit, push, secret/config change or migration was included.

Evidence:

- [Release IDs and gate summary](listening-final-release/release-evidence.json)
- [Isolated release scope](listening-final-release/release-scope.json)
- [All 134 backend payload paths and hashes](listening-final-release/backend-payload-files.json)
- [Full importer reproduction](listening-final-release/importer-reproduction.json)
- [Dataset/schema validation](listening-final-release/dataset-validation.json)
- [WebKit/mobile/Part/save QA](listening-final-release/device-browser-qa.json)
- [Actual production browser](listening-final-release/production-after-browser.json)
- [Actual production API](listening-final-release/production-api-smoke.json)
- [Production runtime asset loader](listening-final-release/production-runtime-assets.json)
- [Rollback preflight](listening-final-release/rollback-preflight.json)
- [All 47 image cases and comparisons](listening-visual-audit/stage2/index.html)

Open issues: C014 physical scan repair and C028 crop boundary classification. No new release-blocking defect was observed. Native device Safari and a fresh production audio/provider exercise remain outside this verification scope.
