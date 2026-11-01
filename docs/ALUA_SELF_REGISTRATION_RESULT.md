# Alua — self-service registration

Local implementation, 2026-11-01. This supersedes the previous requirement for
manual Firebase account creation and UID allowlisting for **new registrations**.
Production, existing learners/history, household records, Cambridge content, bundle
IDs, signing, App Groups and WidgetKit implementation were not changed.

## Delivered flow

Install → Register → Firebase account/session → verified Firebase ID token →
`POST /api/v1/auth/register` → new PostgreSQL learner + identity mapping → Alua.
Logout/login and session restoration continue to resolve that same learner UUID.
No per-user Console operation, enrollment code or administrator mapping is required.

Firebase stores authentication credentials. PostgreSQL remains the server store for
learning data and profile ownership. No Firestore/Realtime Database integration was
added. Passwords go only to Firebase and are not stored by Alua or sent to FastAPI.

## Changes

Backend:

- `app/modules/registration/router.py`: authenticated registration endpoint, strict
  request schema, atomic provisioning, idempotency and registration budgets.
- `app/api.py`: router registration.
- `app/core/config.py`, `.env.example`: registration enable flag and rate budgets.
- `tests/test_self_registration.py`: real temporary PostgreSQL integration tests.
- `tests/test_household_bootstrap.py`: authenticated endpoint count includes register.

No additional migration was needed. Existing head `20261101_0006` already provides
`firebase_identities.firebase_uid` primary key, unique learner ID and FK to
`learner_profiles`. Both tables support standalone learners. Household membership
is optional, so registration does not assign `husband`/`wife` or modify relationships.
The existing Partner API returns an unconnected state for a new learner. Existing
invitation functionality was not expanded or changed.

Frontend:

- `Core/Auth/FirebaseSession.swift`: SDK `createUser(withEmail:password:)`, Firebase
  display-name update, verification email, reload/verification status and friendly
  errors for occupied email, weak password and connectivity.
- `Services/UserService.swift`: `register(displayName:)` using the central API client.
- `App/AuthSession.swift`: signup orchestration, duplicate-submit protection,
  provisioning recovery, verification reminder state and resend cooldown.
- `Features/Auth/AuthView.swift`: Login/Register navigation, name/email/password and
  confirmation fields, Show/Hide, validation, loading, keyboard handling, accessibility
  labels and Dynamic Type. Registration uses `.newPassword` for iOS Password AutoFill;
  email uses the system username content type. Existing reset flow remains available.
- `Features/Root/RootView.swift`, `App/AluaApp.swift`: non-blocking verification reminder,
  resend button and refreshed verification status after returning to the app.
- `AluaTests/FirebaseAuthTests.swift`, `AluaUITests/FirebaseLoginUITests.swift`: signup,
  recovery, duplicate signup, restore/login/logout, verification and form checks.

No Firebase SDK duplication or Xcode target/signing changes were needed for this task.

## API contract

```http
POST /api/v1/auth/register
Authorization: Bearer <Firebase ID token>
Content-Type: application/json
```

```json
{"display_name":"New Learner"}
```

`display_name` is optional for account recovery; a missing name defaults to `Learner`
and can be edited later. Name input is trimmed, limited to 80 characters and rejects
blank/control-character values. Extra fields are forbidden, including Firebase UID,
learner ID, email, password and household role. Identity comes only from verified token.

A successful new or repeated request returns HTTP 200 and `Cache-Control: no-store`,
with the same profile shape as `/api/v1/me`, for example:

```json
{
  "uid":"<new PostgreSQL learner UUID>",
  "email":null,
  "display_name":"New Learner",
  "role":"learner",
  "current_level":null,
  "target_ielts_band":null,
  "daily_study_minutes":null,
  "created_at":"<server timestamp>",
  "updated_at":"<server timestamp>"
}
```

Email remains an authentication attribute in Firebase; no client-provided email is
used to find or attach a PostgreSQL profile. An existing mapping returns its original
profile unchanged, even if a retry submits a different display name. Registration
never attaches a new UID to an existing learner by matching email or name.

The existing Admin SDK verifier checks signature, expiry, project/issuer/audience and
revoked/disabled user state. Legacy opaque tokens cannot authorize registration.
`/me` and all learning APIs continue to require a resolved PostgreSQL mapping;
`/api/v1/bootstrap` remains closed.

## Transactions, concurrency and abuse controls

Provisioning uses one PostgreSQL transaction and the same advisory transaction lock
as private identity administration. It reads the UID mapping under the lock, returns
an existing learner or inserts a UUID learner and mapping together. Unique constraints
and FK remain the final integrity protection. A failure inserting/committing either
record rolls back the transaction; database failures return a generic 503 without
SQL, credentials or internal details. A repeated/concurrent request returns one UUID.

Defaults (effective only when Firebase auth is enabled):

```dotenv
SELF_REGISTRATION_ENABLED=true
REGISTRATION_REQUESTS_PER_MINUTE=120
REGISTRATION_CREATIONS_PER_HOUR=20
```

The pre-verification rolling budget is bounded and process-local, protecting expensive
Firebase checks; it does not trust forwarded IP headers. The creation budget counts
recent mappings in PostgreSQL under the lock and is shared across workers/restarts.
Mapped-user retries do not consume the creation budget. Throttling returns 429;
pausing self registration returns 503 while existing `/me` sessions keep working.
Firebase's signup/email quotas also apply. The limits are configurable; this is a
small-app throttle, not a distributed bot-prevention service. The per-process budget
can be multiplied by worker count; the PostgreSQL creation cap cannot.

## Recovery and email verification

The client waits for a real PostgreSQL learner ID before showing protected content.
If `/me` returns `403 identity_not_allowed` for a valid Firebase session, the client
calls register. Other 403 errors do not trigger provisioning. An outage or throttle
keeps the Firebase session and offers retry/logout. Retry, next login or cold restore
repeats provisioning rather than Firebase account creation. Existing mapped users
use `/me` normally without an extra registration request.

During signup, auth-listener profile loading is deferred until Firebase createUser
and the name update complete. Duplicate signup cannot create another Firebase user
once the current session has a UID. The initial name is sent to PostgreSQL and also
stored as Firebase display name for recovery. If both backend and Firebase name-update
operations fail before a cold restart, the recovered profile can use the fallback
name; ownership and account recovery remain intact.

Verification email is best-effort and independent of provisioning. Unverified users
can study immediately. A calm reminder provides resend, with a 60-second UI cooldown;
verification status refreshes after returning to the app. Email delivery failure does
not undo the account. Future sensitive account-linking actions should verify email
on the server; no new linking feature was implemented here.

Existing Reading caches/outboxes remain scoped by PostgreSQL learner UUID. A new
account receives a new UUID and cannot see another account's queue/history. Old data
is retained. Legacy authentication remains enabled for the separately managed rollout.

## Local verification

- Backend full regression: `cd backend && .venv/bin/python -m pytest -q` —
  **37 passed**. Log: `/tmp/alua-self-registration-all-backend.log`.
- `backend/.venv/bin/ruff check backend/app backend/tests backend/alembic` — passed.
  `git diff --check` — passed. `cd backend && .venv/bin/alembic heads` reports
  `20261101_0006`; no new schema change was necessary.
- iOS full unit/HTTP regression:
  `ALUA_QA_DERIVED_DATA=/tmp/alua-firebase-build ALUA_QA_PACKAGES=/tmp/alua-firebase-packages
  backend/.venv/bin/python frontend/scripts/check_reading.py --unit-only` —
  **28 passed, zero skipped**, including real local Reading HTTP end-to-end, offline
  outbox isolation, session restore and registration recovery. The runner used its
  own PostgreSQL cluster/loopback API/disposable simulator and removed its credential
  file afterwards. Log: `/tmp/alua-reading-stage3-tests.log`.
- Selected UI checks: Login/visibility/reset passed; Registration form validation,
  password confirmation visibility and return to Login passed. Logs:
  `/tmp/alua-registration-ui-tests.log` (Login pass),
  `/tmp/alua-registration-signup-ui-tests.log` (Registration pass after adding a
  guarded transition wait for a dropped simulator tap). No real signup was sent.
- UI command used `xcodebuild -project frontend/Alua.xcodeproj -scheme AluaQA
  -configuration QA -destination 'platform=iOS Simulator,id=<disposable iPhone 16e>'
  -derivedDataPath /tmp/alua-firebase-build
  -clonedSourcePackagesDirPath /tmp/alua-firebase-packages
  CODE_SIGNING_ALLOWED=YES CODE_SIGN_IDENTITY=- API_BASE_URL=http://127.0.0.1:8765
  -parallel-testing-enabled NO -collect-test-diagnostics never
  -only-testing:AluaUITests/FirebaseLoginUITests test`.
  The registration rerun selected `.../testRegistrationFormValidationAndReturnToLogin`.
  Signing and API URL overrides apply only to the local commands, not project settings.
- Final focused auth/network rerun after duplicate-signup hardening — **7 passed**,
  including a second signup attempt while the Firebase account already exists.
  Command used the same simulator/build options with scheme `Alua`, configuration
  `Debug`, `-only-testing:AluaTests/FirebaseAuthTests` and
  `-only-testing:AluaTests/AuthenticatedNetworkTests`.
  Log: `/tmp/alua-registration-final-auth-tests.log`.

Backend coverage includes concurrent requests for one UID; distinct UUIDs for two
UIDs; whole-transaction rollback on mapping insert failure and successful retry;
existing mapping idempotency; rejection of forged tokens and identity/body injection;
unchanged old learners/households; standalone learners accessing Vocabulary, Grammar,
Curriculum, Progress, Today and Reading; cross-user Reading and Vocabulary/SRS access
rejection; registration throttling and existing-user access while registration pauses.

Xcode build phases succeeded as part of the passing test commands. No real Firebase
passwords were used: SDK/session behavior is mocked in unit tests, while UI tests
render the native forms and SDK initialization. The original legacy-enrollment UI
journeys were not run against the replaced auth screen. Existing backend and iOS
unit/Reading HTTP regressions were run.

Remaining warnings are the existing Alembic `path_separator` deprecation, Pydantic
`register` field-name warning and Xcode UI-runner AppIntents metadata notice.

## Future rollout — separate approval required

1. Keep the existing database and take the normal backup. This task performs no
   production operation and does not delete or reassign any old learner/history.
2. Ensure Firebase project `alua-6153b` has Email/Password enabled once, appropriate
   password policy, verification/reset email templates and quotas. Users create their
   own accounts in Alua; do not create each user manually in Console.
3. Deploy the prepared backend and existing additive identity migration `0006` if
   it is not yet installed. Configure protected ADC and `FIREBASE_PROJECT_ID`.
4. Enable `FIREBASE_AUTH_ENABLED=true`, retain `LEGACY_AUTH_ENABLED=true`, enable
   `SELF_REGISTRATION_ENABLED=true` and choose suitable registration budgets.
5. Verify signup/provisioning and existing `/me` access before distributing the new
   app. The existing Debug/Release API URL settings were preserved; local tests use
   explicit loopback overrides.
6. Test two real iPhones: signup, verification email, kill/relaunch, offline Reading
   answer, backend outage/retry, logout/login and separate user histories. Confirm
   old household profiles remain accessible through their retained legacy access.
7. Disable legacy authentication only as a separately approved follow-up. Registration
   can be paused independently without disabling existing Firebase sessions.

Automated checks use Firebase mocks and disposable PostgreSQL/simulators, with no
real passwords or production credentials. Real Firebase email delivery, Password
AutoFill saving and physical-device QA remain rollout checks.

References: [Firebase Apple password signup](https://firebase.google.com/docs/auth/ios/password-auth),
[Firebase user management and verification](https://firebase.google.com/docs/auth/ios/manage-users).
