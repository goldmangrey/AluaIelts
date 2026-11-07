# Listening Player V4 — local implementation and QA

Completed locally on 2026-11-07. No commit, push, deployment, database migration,
production access, original audio edits, answer/key/transcript/image edits.
Existing local Listening answer/UI changes were preserved.

## Interaction and persistence

- The four segments select **visible questions only**. They do not load another
  audio source, pause playback, or reset the source's currentTime.
- The green dot identifies the current audio track. When viewing another Part,
  its segment contains a small play action labelled **Listen to Part N**. This
  explicitly selects that audio, restores its previous position, and starts it.
- Natural end advances audio and visible questions to the next Part. At most
  one audio element plays; the second element only preloads metadata.
- `AudioProgress`, shared with `ListeningDraft` in Exam, stores all four positions
  under `alua:listening:audio:v1:<uid>:<attempt>:<exam>:<audio-metadata-version>`.
  The version is the corresponding waveform package SHA-256.
- Save occurs at five-second playback intervals, pause, seek, source change,
  visibilitychange and pagehide. Failure of localStorage leaves an in-memory store.
  Reload restores after loadedmetadata and does not autoplay.
- Backend State/schema are unchanged. Only the ordinary active audio_part and
  playback_seconds use the existing ListeningDraft sync. Other Parts' positions
  are local to this browser; they are not a new cross-device backend feature.
- Review uses the same player and local progress class, with no answer/result
  writes. The old separate Part tabs, audio select/replay and show/hide controls
  were removed; review filters and AI explanations remain.
- An explicit AI Play/Loop Moment temporarily borrows the audio element. Ordinary
  position is saved first. Clip playback never overwrites ordinary progress.
  Completion, stop, question navigation or hidden-page cancellation restores the
  ordinary source/position paused. Manual transport during a clip first exits
  the temporary clip and returns to normal playback context.
- Safari clip playback waits for a completed seek/canplay before play. EOF loops
  explicitly handle delayed native ended events. UI play state reads native
  paused state, including delayed pause events and timeupdate.

## Real waveform

`web/scripts/build-listening-waveforms.py` reads the existing audio inventory and
local originals in `~/Desktop/Listening` (override `--audio-root`). It never edits
originals or the backend manifest. FFmpeg computes 64 ms RMS frames at 8 kHz mono,
aggregated by actual timestamps into 2048 normalized uint8 bins per audio track.

72 content-hashed JSON packages cover 288 tracks (1,981,024 bytes combined).
They include original audio SHA-256 and duration. The frontend manifest maps exam
IDs to packages and checksums. Playback URLs and audio grants are unchanged.
The browser fetches only the compact JSON and adapts bar count to container width;
it never fetches/decodes audio to build the waveform. Failed metadata leaves an
honest seek rail, not a fabricated waveform. SVG bars are memoized.

## Verification

- TypeScript, targeted ESLint, production build: PASS.
- `node web/scripts/check-listening-player-v4.mjs`: **8/8 PASS**, Chromium and
  WebKit, desktop and emulated mobile, Exam and Review. Real original Cambridge
  04 MP3 are served only on a temporary localhost fixture. Auth/attempt/AI API
  responses are synthetic. No real user data or production endpoints are used.
- Covered: playing Part 1 at 03:00 while viewing Part 2 and returning; explicit
  audio changes with separate positions; paused reload; user/attempt/exam key
  isolation; localStorage failure; native seek via pointer, touch and keyboard;
  +/-5 seconds; natural end; same/cross-Part Play/Loop Moment without overwriting
  positions; one audible player; answer autosave during playback; Submit/Review;
  no horizontal or page overflow. The fixture asserts that no audio fetch is
  initiated for waveform calculation.
- All 288 generated tracks were checked against original audio SHA-256 and all
  72 JSON package hashes, dimensions/counts/ranges, identity and duration metadata.
- Existing targeted Listening Review tests: **12/12 PASS** across Chromium/WebKit
  desktop/mobile (shared editing/navigation, AI caching/moments/EOF loops, retry,
  incomplete evidence and ordinary playback). Command:
  `node web/scripts/test-listening-review.mjs --project=review-chromium-1600 --project=review-chromium-mobile --project=review-webkit-1600 --project=review-webkit-mobile --grep 'AI review is|AI retry|Shared V3'`.
- Existing part coverage script: **72 Tests / 288 Parts / 568 groups**, missing
  coverage 0, duplicate pairs 0, order inversions 0, wrong Part 0. This rerun is
  component coverage, not a new visual audit of all images.
- Full database-backed Exam integration suite was not run. The new Exam fixture
  exercises the actual page, ListeningDraft and controls through Submit/Review.
- Real-device Safari/iOS was not tested; WebKit and mobile emulation were tested.
  Browser seek assertions allow asynchronous playback/codec timing tolerance;
  stored ordinary positions are compared exactly before/after temporary AI clips.

## Files and artifacts

Runtime: `player.tsx`, `player.module.css`, `audio-progress.ts`, `waveform.ts`,
`waveform-manifest.json`, `draft.ts`, `pages.tsx`, `review.tsx`,
`review.module.css`, `workspace.module.css` in `web/src/features/listening/`;
72 files in `web/public/listening-waveforms/v1/`.

QA: `web/scripts/build-listening-waveforms.py`,
`web/scripts/check-listening-player-v4.mjs`, the existing disposable fixture helper
`web/scripts/check-listening-ui.mjs`, and the two existing Listening browser specs.

Results: [machine-readable QA](listening-player-v4/qa.json),
[desktop player](listening-player-v4/chromium-desktop-exam-player.png),
[mobile player](listening-player-v4/chromium-mobile-exam-player.png).
The same folder contains full-page Exam/Review captures for both engines and sizes.
