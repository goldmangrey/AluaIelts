# Local QA reproduction

Use one booted simulator at a time on this machine. The iOS 27 runtime may spend several minutes on its first boot/install; subsequent runs are faster.

1. From `backend`, run `uv run python -m scripts.qa.stage5_server`. It creates and migrates a **temporary PostgreSQL cluster**, overrides `DATABASE_URL` before importing the app, disables remote AI and binds only `127.0.0.1:8765`. Stopping it removes the cluster. It does not import production data.
2. Build scheme `AluaQA`, configuration `QA`. Its API URL is loopback. Debug and Release continue to use the existing production URL.
3. In an isolated QA simulator, enter 32 ones for the first learner, 32 twos for the second, using the normal enrollment screen. These codes exist only in that temporary database. Do not use a production-enrolled device for this fixture run.
4. On a fresh QA course, run `AluaProductQATests/testFirstDay` for the first learner. Run `testLongExpressionSmallPhone` on the small simulator for the second learner. The tests intentionally assert real deterministic catalog terms at resume boundaries. Restarting the fixture server requires a new ordinary QA enrollment; do not erase Keychain or modify security to make a test pass.
5. `testBookAndRecallViews` is a repeatable regression for an already introduced first-learner book. XCTest attachments and runner `tmp/alua-qa-*.png` files are actual screenshots of the app.
6. Add **Alua Glance** through native Lock Screen customization. To exercise due recall, advance only the isolated fixture state's due date (or wait for it). Read the exact App Group v5 `glance`; tap the real widget and compare the question. Check server response/event counts before and after a reply. The native editor setup scripts used during this run were temporary and have been removed from the regression suite.

Backend verification: `uv run pytest tests/test_household_bootstrap.py tests/test_learning_quality.py tests/test_study.py`; `uv run ruff check .`.

Signed simulator unit regression command (local API override avoids production traffic):

```sh
xcodebuild -project Alua.xcodeproj -scheme Alua \
  -destination 'platform=iOS Simulator,id=<booted-simulator-UUID>' \
  -parallel-testing-enabled NO \
  API_BASE_URL=http://127.0.0.1:8765 \
  DEVELOPMENT_TEAM=A8DD9HJC4H CODE_SIGN_IDENTITY=- test
```

A device archive uses scheme Alua / Release, `MARKETING_VERSION=2.1 CURRENT_PROJECT_VERSION=5`, generic iOS destination and the existing Apple Development team. Export method `debugging`, signingStyle `automatic`. No upload or provisioning update was requested. Never install that production-URL artifact before the release gates in `RELEASE_CHECKLIST.md` are met.
