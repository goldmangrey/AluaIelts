# Stage 5 scenario evidence

“Real UI” means the compiled app using ordinary enrollment and the isolated PostgreSQL/FastAPI fixture backend. Automated evidence does not substitute for the two physical iPhones.

| # | Scenario | Evidence |
|---|---|---|
| 1 | First launch | Real enrollment UI; `27-first-launch-small.png` |
| 2 | 12-question diagnostic | Real first-day UI, 12 answers; `02-diagnostic-result.png`; backend learning_quality tests |
| 3 | 50×30 course | Backend `test_catalog_and_program`, lifecycle/default/A1/B2 tests |
| 4 | Day 1 0/30 | `01-today-0-modern.png` |
| 5 | 10 and pause | Real first-day flow; `03-lesson-pause-10.png` |
| 6 | Resume card 11 | Real UI asserts catalog term `job`; StudyStore/backend resume regressions |
| 7 | Relaunch 18/30 → card 19 | Real UI asserts `street`; Stage4Presentation test; second learner also relaunches with 18 |
| 8 | 30/30 completion | `06-day-completed.png`, actual first-day UI |
| 9 | Completed day in Book | `08-book-days-modern.png`; lifecycle tests |
| 10 | Russian/English search | Real Russian keyboard/search screenshot 18; both languages in backend and Swift presentation tests |
| 11 | Review from Book | Book→Card→Review→Feedback→Progress UI passed; screenshots 10/12/13/22/23 |
| 12 | Independent learners | Isolated DB lifecycle tests + separate enrolled modern/small simulator users (30 and 18 introduced) |
| 13 | Offline/reconnect | StudyStore durable queue and lost-ACK same-UUID tests; actual local network experiment documented in result report |
| 14 | Hide/restore | Backend lifecycle test, history count preserved; widget resolver excludes hidden |
| 15 | Correct widget term | Real WidgetKit `learn`, screenshot 19; confirmed-only publication regression |
| 16 | Tap exact term | Native SpringBoard tap → `learn` question, screenshot 20, UI passed |
| 17 | Open without answer | Isolated DB review_count=0/events=0 after actual tap; resolver/store regression |
| 18 | No duplicate widget event | Actual answer count=1; same event replayed twice, still 1; backend concurrency regression |
| 19 | Finish Day 50, keep Book/reviews | Backend `test_fifty_days_and_legacy`; honest finished-state Swift test |
| 20 | Grammar/diagnostic reachable | Actual UI navigation at largest Dynamic Type, screenshots 28/29; backend legacy checks |

The first-day UI run completed the learning scenario but failed later on an outdated Book selector. Its failure log is preserved; the selector was corrected and the separate Book regression passed. Do not count that first run as an entirely passing test suite. Temporary native widget-editor/fixture-control scripts were removed after evidence was captured.

Physical Lock Screen authentication, real radio loss/recovery, VoiceOver reading/focus, learner separation and all release gates must still be checked on both phones using `RELEASE_CHECKLIST.md`.
