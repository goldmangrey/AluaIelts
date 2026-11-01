# Alua: Firebase Email/Password migration

Date: 2026-11-01. Local implementation only; no SSH, deployment, production queries,
production migrations, account creation, commit or push was performed.

## Identity and data contract

Firebase Authentication proves identity. PostgreSQL remains the only server-side
store for Vocabulary/SRS, Reading, Grammar, Curriculum, Today, Progress and partners.
No Firestore/Realtime Database client, collection, rules or data migration was added.

`verified Firebase UID → firebase_identities → existing learner_profiles.learner_id`

`GET /api/v1/me` still returns the existing internal learner UUID in `uid`. No API
accepts a client-supplied learner ID as authentication. Unknown Firebase identities
receive 403 `identity_not_allowed`. There is no email-based linking or automatic
profile creation. Public `/api/v1/bootstrap` remains 404. Existing learner-owned
records and enrollment records are unchanged.

The configured local database is `localhost/alua`; it was unavailable during the
read-only identity check. Therefore this work does **not** claim that either real
household learner exists locally or that both exist in production. Tests provisioned
only disposable PostgreSQL fixtures. Inspect actual learners during the separately
approved rollout before assigning identities.

## Changed implementation

Backend:

- `app/core/config.py`, `.env.example`: independent migration flags.
- `app/core/firebase_auth.py`: singleton Firebase Admin initialization using ADC;
  explicit project, verified ID tokens and `check_revoked=True` on every request.
- `app/core/auth.py`: provider dispatch and PostgreSQL identity lookup.
- `app/db/models.py`: one additional `firebase_identities` mapping table.
- `app/firebase_admin_cli.py`: private list, dry-run/apply binding and explicit provisioning.
- `app/modules/enrollment/router.py`: retain legacy routes; disable enrollment when
  legacy auth is later disabled; Firebase sessions have no current device enrollment.
- `app/modules/users/service.py`: `/me` can no longer create an empty learner.
- `alembic/versions/20261101_0006_firebase_identity.py`: additive successor to `0005`.
- `pyproject.toml`, `uv.lock`: Firebase Admin 7.7.0, pinned by lockfile.
- `tests/test_firebase_auth.py`; Reading migration test updated for new head.

The Admin SDK package declares transitive Google Cloud packages, including Firestore.
They are not imported or initialized by Alua. Only `firebase_admin.auth` is used;
no Firebase database is connected.

Frontend:

- `project.yml`, generated `Alua.xcodeproj/project.pbxproj`, `Package.resolved`:
  Firebase Apple SDK 12.19.3; only **FirebaseCore** and **FirebaseAuth** products linked
  to **Alua**. No Firebase product dependency on AluaWidgets.
- `Alua/Resources/GoogleService-Info.plist`: moved from root, not duplicated;
  bundled as `GoogleService-Info.plist`. `BUNDLE_ID=com.alua.app`, project `alua-6153b`.
  It remains ignored by the existing Git rule; retain/provide this local file when
  building another checkout. No Admin credentials are included in the bundle.
- `Core/Auth/FirebaseSession.swift`: Firebase adapter, SDK-managed credentials,
  listener lifecycle, token retrieval, password reset and sign-out.
- `AuthSession.swift`, `DependencyContainer.swift`, `AluaApp.swift`: single session
  authority and existing dependency injection.
- `AccessTokenProvider.swift`, `APIClient.swift`, `ReadingAPI.swift`: central token
  supply, session identity checks and cancellation of old requests.
- `Features/Auth/AuthView.swift`: native login/reset UI, email keyboard, Password
  AutoFill, visibility toggle, loading/disabled states, neutral human-readable errors,
  scrolling for keyboard/Dynamic Type and labeled accessibility controls.
- `RootView.swift`, `SettingsView.swift`: logout, error-screen exit and existing
  learner-state cleanup. No WidgetKit implementation, entitlements, App Group,
  bundle IDs or signing values changed.
- `AluaTests/FirebaseAuthTests.swift`, `AluaUITests/FirebaseLoginUITests.swift`:
  session/network/UI checks. `scripts/check_reading.py` supports `--unit-only` and
  optional build/package cache paths for isolated regression tests.

## Session and token behavior

Firebase is configured once in the existing SwiftUI composition root before the
session starts; there is no second AppDelegate/session system. An auth listener
restores the Firebase user and `/me` resolves their existing learner. Main content
is shown only after that succeeds. Transient backend failure shows retry and logout,
not a new learner. Unmapped accounts return to login with an access message.

SDK `getIDToken()` supplies an ID token for each protected request and automatically
refreshes expired tokens. Passwords go only to Firebase, never to FastAPI, UserDefaults,
files or Alua's Keychain store. Firebase owns its credential persistence.

A stable session identifier is separate from the rotating bearer token. Account
changes/logout cancel active API tasks and discard late responses, including profile
loads and Reading asset responses. A protected API 401 invalidates the same session;
a stale 401 cannot sign out a different account.

Existing installations can restore their saved legacy device token when there is
no Firebase session. After Firebase login, the local legacy credential is removed
and automatic fallback is disabled; backend enrollment records are **not** revoked.
Other devices remain functional during rollout. Explicit logout signs out Firebase,
clears local credentials and active stores, closes protected screens and shows login.

Reading storage remains `Reading-v1/SHA256(existing learner UUID)`, with unchanged
mutation UUIDs and optimistic versions. Unsynced/unaccepted/corrupt queues are retained
under their original learner and never rebound to Firebase UID or another account.
Synchronized caches may be cleared by the existing logout cleanup. Logging back into
the mapped original learner restores the original queue.

Password reset uses `sendPasswordReset(withEmail:)`; unknown-user results receive the
same neutral confirmation. No custom reset endpoint or Sign Up UI was created.

## Backend verification and configuration

Defaults preserve old production behavior:

```dotenv
FIREBASE_AUTH_ENABLED=false
LEGACY_AUTH_ENABLED=true
FIREBASE_PROJECT_ID=alua-6153b
```

For a prepared environment enable `FIREBASE_AUTH_ENABLED=true`, retaining legacy=true.
Use ADC; if needed set `GOOGLE_APPLICATION_CREDENTIALS` to an access-restricted file
**outside the repository**. No service account contents belong in source or iOS.
The credential must have permission to read Firebase users for revocation/disabled
checks. Missing credentials/backend verification outages fail closed.

JWT-shaped credentials never enter legacy fallback. Opaque legacy credentials require
`alua_dev_` prefix plus an existing unrevoked database token hash. Firebase Admin
checks signature, exp, issuer, audience and subject; revoked/disabled/deleted users
are rejected with 401. Missing mapping is 403; verifier availability errors are 503.
Emulator trust is deliberately rejected even locally; tests mock verification instead.

Reference: [Firebase Admin token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens),
[revocation policy](https://firebase.google.com/docs/auth/admin/manage-sessions),
[Apple password authentication](https://firebase.google.com/docs/auth/ios/password-auth).

## Private administration (examples, not executed on production)

Run from `backend` against the explicitly selected database with protected ADC.
Do not include passwords or bearer tokens in arguments. Firebase UIDs and learner UUIDs
are different identifiers. Inspect names/history and household roles before binding.

```sh
uv run python -m app.cli list-household-candidates
# Apply the additive migration only in the separately approved target environment:
uv run alembic upgrade head
uv run python -m app.firebase_admin_cli list
uv run python -m app.firebase_admin_cli bind --firebase-uid FIREBASE_UID --learner-id EXISTING_UUID
# Same validation, then persist explicitly:
uv run python -m app.firebase_admin_cli bind --firebase-uid FIREBASE_UID --learner-id EXISTING_UUID --apply
```

`bind` verifies that the Firebase account exists and is not disabled. The learner must
already exist and have an assigned household role. The same mapping is idempotent;
a different binding for either UID or learner is refused. Unique constraints, FK
RESTRICT and a PostgreSQL advisory transaction lock protect concurrent administration.
Dry runs roll back. There is no HTTP admin endpoint.

If a role is missing but the person's learner already exists, attach that learner:

```sh
uv run python -m app.firebase_admin_cli provision-missing-learner --role wife --display-name NAME --existing-learner-id EXISTING_UUID
# Review, then repeat with --apply.
```

Only if history/identity inspection confirms this person has **no** existing learner:

```sh
uv run python -m app.firebase_admin_cli provision-missing-learner --role wife --display-name NAME --confirm-new-profile
# Review, then repeat with --apply; record the newly printed learner UUID and bind it.
```

This creates only one explicitly requested missing learner, never silently creates both,
and refuses an occupied household role. It does not copy or reassign another person's
history. Migration downgrade deliberately preserves bindings for application rollback.

## Firebase Console and future rollout

1. Select Firebase project `alua-6153b`. Authentication → Sign-in method → enable
   Email/Password (password provider, not a requirement for email-link sign-in).
2. Authentication → Users → create the two personal accounts with chosen emails and
   passwords. Do not send passwords in chat or put them into source/CI.
3. Copy each Firebase UID and record which real person owns it. Public Firebase account
   creation from external clients cannot grant Alua access without PostgreSQL mapping.
4. Separately approve Oracle rollout. Back up PostgreSQL; inspect existing learner IDs,
   roles, Reading history, vocabulary and partner links. Prepare ADC outside Git.
5. Deploy backend with Firebase=false, legacy=true; apply `0006`; bind and verify each
   UID to the existing learner. Keep legacy credentials/enrollments intact.
6. Enable Firebase=true, legacy=true; verify `/me` and scoped access using each account.
7. Install the new app on both iPhones. Confirm former results and pending offline
   answers under the same learner IDs. Do not ship the new login before backend/mapping.
8. Only after both users pass device QA, separately approve `LEGACY_AUTH_ENABLED=false`.
   This also closes new enrollment redemption. Keep records for rollback/audit; no
   token deletion is part of this task. Re-enable the flag if a rollback is needed.

Existing Debug/Release API URL settings were preserved. All executed simulator tests
explicitly override the API URL to loopback; this work did not exercise production.

## Local verification

- `cd backend && .venv/bin/python -m pytest -q`: **32 passed**. Full regression
  includes real temporary PostgreSQL, existing study/Reading tests and Firebase mocks.
- `.venv/bin/python -m pytest tests/test_firebase_auth.py -q`: **9 passed** after
  adding explicit cross-learner answer/result access assertions.
- `.venv/bin/ruff check app tests alembic`: **passed**.
- `.venv/bin/alembic heads`: `20261101_0006`. Tests exercised both fresh installation
  and an actual simulated `0005 → 0006` upgrade preserving existing learner records.
- Final standalone `xcodebuild -project frontend/Alua.xcodeproj -scheme Alua
  -configuration Debug -sdk iphonesimulator -destination "generic/platform=iOS Simulator"
  -derivedDataPath /tmp/alua-firebase-build -clonedSourcePackagesDirPath /tmp/alua-firebase-packages
  ARCHS=arm64 ONLY_ACTIVE_ARCH=YES CODE_SIGNING_ALLOWED=NO API_BASE_URL=http://127.0.0.1:8765 build`: **BUILD SUCCEEDED**.
- Xcode simulator test builds also succeeded, with ad-hoc signing
  overrides on the command line only. The new plist was inspected in the built main
  app and was absent from the embedded Widget extension; its semantic contents match
  the moved source plist. No duplicated root file remains.
- `xcodebuild -project frontend/Alua.xcodeproj -scheme AluaQA -configuration QA
  -destination 'platform=iOS Simulator,id=<disposable iPhone 16e>'
  -derivedDataPath /tmp/alua-firebase-build
  -clonedSourcePackagesDirPath /tmp/alua-firebase-packages
  CODE_SIGNING_ALLOWED=YES CODE_SIGN_IDENTITY=- API_BASE_URL=http://127.0.0.1:8765
  -parallel-testing-enabled NO -collect-test-diagnostics never
  -only-testing:AluaUITests/FirebaseLoginUITests test`: **1 UI test passed**.
  Covered login rendering/validation, Show/Hide and reset sheet. No real Firebase
  password request was issued.
- Final all-unit/Reading HTTP regression command:
  `ALUA_QA_DERIVED_DATA=/tmp/alua-firebase-build ALUA_QA_PACKAGES=/tmp/alua-firebase-packages
  backend/.venv/bin/python frontend/scripts/check_reading.py --unit-only`.
  **26 tests passed, zero skipped**, including the real Reading HTTP end-to-end test,
  token rotation/session isolation and offline queue persistence.
  Uses its own PostgreSQL cluster, loopback API and disposable simulator; preserves
  existing databases/devices and removes its temporary token file afterwards.

Logs: `/tmp/alua-firebase-backend.log`, `/tmp/alua-firebase-auth-tests.log`,
`/tmp/alua-firebase-ui-tests.log`, `/tmp/alua-reading-stage3-tests.log`,
`/tmp/alua-firebase-final-build.log`.

Backend warnings are pre-existing Alembic `path_separator` deprecation and a Pydantic
`register` field-name warning. Xcode reports no AppIntents metadata for the UI runner;
no AppIntents feature was added. Legacy enrollment-based UI scenarios were not run
against the replaced login screen; new login UI and existing Reading unit/HTTP tests
cover this local migration. Physical device testing and real Firebase email/token
exchange remain the explicit rollout checks below.

## Physical iPhone QA still required

- First login A; `/me.uid` equals A's old UUID; old Vocabulary/Reading/Progress visible.
- Kill/relaunch app; session restored without password; retry after network outage.
- Remain signed in across ID token expiry; protected calls refresh without password UI.
- Enter an incorrect password; verify readable error and usable retry/reset sheet.
- Reset password email arrives; revoked/disabled/unmapped account cannot read Alua data.
- Queue a Reading answer offline, logout, login B: no A data/queue visible; return to A:
  original pending answer still present and synchronizes using its original event UUID.
- Logout during a slow request: no stale profile/results/widgets reappear.
- Small iPhone, large Dynamic Type, VoiceOver, keyboard, password AutoFill and Show/Hide.
- Repeat for both physical devices before disabling legacy auth.

No real Firebase credentials or account passwords were used in automated tests. Actual
email delivery and Google production token exchange require the owner's Console setup
and the separately approved device/rollout verification; they are not claimed tested.
