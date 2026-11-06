# Cambridge 21: nine transcript tails repaired

Local repair only. No Oracle connection, deployment, migration, commit or push.

Recovered 272 segments, 19.73 minutes of segment speech; restored timeline spans 26.68 minutes including the mid-Part instruction pauses. Existing segment dictionaries (IDs, text and timestamps) were preserved exactly. The other 279 JSON transcripts and all nine source audio hashes are unchanged.

| Test | Part | Previous end (s) | Repaired end (s) | Decoded audio (s) | New segments |
|---|---|---:|---:|---:|---:|
| 1 | 1 | 278.71 | 406.900 | 467.305 | 29 |
| 1 | 2 | 273.04 | 415.000 | 445.518 | 22 |
| 1 | 3 | 196.28 | 386.000 | 416.575 | 32 |
| 2 | 2 | 168.79 | 337.560 | 368.091 | 29 |
| 2 | 3 | 268.65 | 415.460 | 446.015 | 30 |
| 3 | 2 | 174.26 | 379.980 | 410.514 | 33 |
| 3 | 3 | 168.28 | 361.400 | 391.941 | 30 |
| 4 | 2 | 180.92 | 402.400 | 432.954 | 33 |
| 4 | 3 | 154.76 | 359.755 | 390.322 | 34 |

Method: the nine CSV-listed MP3s were decoded locally through FFmpeg (`ignore_err`, `discardcorrupt`, timestamp-preserving resampling), then only the missing tails plus ~10 s overlap were recognised with MLX Whisper large-v3-turbo, English, word timestamps. Absolute times include each crop offset. Duplicated opening instructions were discarded; new IDs continue the old sequence. Runtime uses JSON only, so no parallel SRT/TXT files were created.

The final 32 s of speech in each recording were independently recognised again. Test 4 Part 3 needed a focused replacement of the new final segments to recover its closing instruction and remove a duplicated word; a further short crop confirmed it. Silence was measured from PCM: final ~30 s (Test 1 Part 1 ~60 s) is intentional silence. Hallucinated “Thank you” segments in these intervals and one mid-Part pause were excluded (sample peak amplitude 2/32768). No unexplained uncovered non-silent interval longer than 0.6 s remains in any repaired tail. This signal check supports, rather than replaces, the text/independent-ending checks.

The supplied IELTS-Hub pages were used only for targeted comparison/spelling: Lyocell, EcoVero, Jim Clowrie, Saiphin, and two contracted-word spellings. No website timestamps were used. Audio-generated ending phrases were retained where the page abbreviates them. No unresolved lexical uncertainties or substantive speech gaps were identified. These remain machine transcripts; the original `audio_verified: false` is retained rather than claiming a human listening audit of each full Part.

Source map: `~/Downloads/Cambridge_21_9_Gaps_Source_Map/Cambridge_21_nine_gap_sources.csv`. Sources: https://www.ielts-hub.com/exams/listening/cambridge-ielts-21-test-1/transcript, https://www.ielts-hub.com/exams/listening/cambridge-ielts-21-test-2/transcript, https://www.ielts-hub.com/exams/listening/cambridge-ielts-21-test-3/transcript, https://www.ielts-hub.com/exams/listening/cambridge-ielts-21-test-4/transcript.

Validation: nine real-audio duration/prefix/ID/order/range checks PASS; production AIReview context assembled locally with mock completed-attempt storage (no database) includes all new segments; AIReview.validate accepts every new segment quote and returns the correct 2.5 s/3 s padded, audio-bounded clip. These are the intervals consumed by the existing Play Moment/Loop Moment controls; no UI/player/provider code changed. All 288 manifest file digests agree. Existing dataset regression assertions were updated from nine incomplete Parts to zero. Targeted transcript/evidence/safety regression tests: 4 PASS (3 database-dependent tests deselected; no database accessed).

Changed: nine `cambridge-21-test-*-part-*.json` files, `manifest.json`, two dataset expectations in `backend/tests/test_listening_ai.py`, and this report.


## Production data deployment — 2026-11-06

Local commit `599d5df` contains only the nine target JSON files, manifest and `test_cambridge21_transcript_repair.py` (9 tests PASS). These files were previously untracked, so Git records them as additions. Unrelated workspace changes and the prior AI implementation were excluded. No push.

Backend release: `/opt/alua/releases/listening-c21-repair-20261106-599d5df`; copied from retained `/opt/alua/releases/listening-ai-20261106`. Exactly nine JSON files and their manifest were overlaid. Application code and other content were compared unchanged. No dependency install, frontend/Cloudflare change, provider change or migration. Service drop-in: `/etc/systemd/system/alua-api.service.d/zzzzzzzzzz-c21-transcripts-20261106.conf`. Rollback can deactivate this final drop-in and restart only `alua-api`, returning to the preceding release without restoring the database.

Existing backup ran before activation: `alua-20261106T063557Z.dump.age`, SHA-256 `b69a2b0550bd3989b18ac9092866cb7231a5343dcff2d8c7c6db0fc69b967d5b`. Runtime loader and checksum validation: 288/288 available; all nine repairs `complete=true`; no `incomplete_at_pause` flags. No additional hard-coded Cambridge 21 restriction exists.

Two new isolated production smoke attempts were created/submitted through the ordinary API; all 13 pre-existing Listening and 26 Reading attempt/result rows retained their original per-row fingerprints:

- Test 1 Part 1, attempt `4c814db5-8684-4833-aafe-7bec6f4a545c`, Q7: restored `seg-0056`, `seg-0057`, clip 332.60–344.90 s (old cutoff 278.71 s), verbatim towel quote verified against trusted context. PASS.
- Test 2 Part 2, attempt `be91d5af-c015-467c-b6ca-9c8a0090d568`, Q16: restored `seg-0044`–`seg-0046`, clip 243.44–264.70 s (old cutoff 168.79 s), bathhouse/north-of-engine-house quote verified against trusted context. PASS. Q15 map question returned safe `evidence_not_found`; no guard was bypassed.
- Existing production authorize/audio proxy returned real HTTP 206 Range bytes for both Parts. PASS.
- Actual production Play Moment/Loop Moment browser smoke: NOT VERIFIED. Chrome displayed a blank Review page although HTTP SSR and authenticated API/audio checks passed; native computer control then returned `noWindowsAvailable`, followed by a getApp timeout/kernel reset. The browser access host was unavailable. No claim that Play/Loop played these two clips is made. This is an unresolved acceptance blocker, not a proven player regression. Data is deployed; full release acceptance is incomplete.
