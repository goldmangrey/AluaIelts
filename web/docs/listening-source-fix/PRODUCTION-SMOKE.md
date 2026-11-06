# Production smoke — 2026-11-05

Site: https://alua.study

- Commit: `af0e3590631f42afd24c878c3643466c228e6b83`
- Cloudflare deployment: `169f7ca0-a2e7-4a5e-9814-60da0511fd67`
- Worker version: `a25f11ba-298b-4b91-b378-1c006e6930e2`, 100% traffic.
- Previous version retained for rollback: `33300515-2efb-4465-93ea-be2353de2aa9`.

## Live authenticated Chrome checks

- Cambridge 14 Test 2 Q1: original Total Health Clinic form visibly rendered beside questions. Q1/Q2 navigation retained source. Part 2 and return to Part 1 retained correct originals, switched audio paused.
- Cambridge 04 Test 3 Q1: original Accommodation Request Form visibly rendered, including Test 3 heading. Independent source scroll, Q1/Q2 navigation and reload retained source. Existing attempt answers were not changed or submitted.
- Cambridge 14 Test 1 Q13: original images and shared A–E options visibly rendered. Reload retained Q13 and its materials.
- Real audio: Play, Pause, +5 seconds and timeline seek worked; Test 2 Part 1 duration 07:42. Reload restored paused seek position.
- Compact player and expandable grid with all 40 numbers were checked. Divider keyboard resize 55 → 53 → 55 worked. Pointer dragging was verified locally, but native production automation did not conclusively exercise pointer dragging.
- Autosave and reload restored test answers. Fresh Test 2 smoke attempt submitted and reached Results and readonly Review. Fresh Test 1 smoke attempt submitted with one correct answer and Results showed 1/40. These two deliberate smoke attempts remain in account history.
- Premium Home originals, signed-out Login form with Continue with Google, and authenticated Reading collections were observed. Fresh Google OAuth sign-in was not completed; existing authenticated session worked.

## Build and asset checks

- Typecheck, lint and Cloudflare build passed before deployment.
- Home, Login, Reading and Listening returned HTTP 200. Served Home/Login/Reading JS/CSS matched the built assets byte for byte. All four Home image assets matched local originals.
- Local Chromium/WebKit desktop/mobile verification is documented in the adjacent README and Workspace V3 report. Production authenticated smoke used desktop Chrome; production WebKit/mobile was not repeated.
- No observed production regression required rollback.

## Remaining items

- Cambridge 04 Test 1 remains unavailable because Q34 is absent. No artificial unlock or content change was made.
- Production pointer drag, fresh Google OAuth sign-in and production WebKit/mobile are verification gaps, not confirmed defects.

Only the ten Listening source/test files were committed. Backend, database, Firebase, grading, production secrets and unrelated working-tree changes were untouched. No Git push was performed. This report and screenshots remain local and uncommitted.
