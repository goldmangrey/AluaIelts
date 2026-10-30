# Alua Firebase-to-PostgreSQL migration report

Date: 2026-10-28 (Asia/Almaty)

No Oracle/FLORA access, deployment, commit, push, or remote source-data mutation was performed.

## 1. Files changed

### Backend configuration, database, migrations, and operations

- `backend/.env.example`, `backend/pyproject.toml`, `backend/uv.lock`
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`
- `backend/alembic/versions/20261028_0001_initial_postgresql.py`
- `backend/app/api.py`, `backend/app/cli.py`, `backend/app/core/auth.py`,
  `backend/app/core/config.py`
- `backend/app/db/__init__.py`, `backend/app/db/database.py`, `backend/app/db/models.py`,
  `backend/app/db/serialization.py`
- `backend/app/modules/enrollment/{__init__,repository,router,schemas,service}.py`
- `backend/scripts/migrate_firestore_export.py`
- `backend/scripts/lexicon/build_local_ru_lexicon.py` (typing-only tuple correction)
- `deploy/alua.service.example`, `deploy/nginx-alua.conf.example`

### Backend repositories/services/routers

- `backend/app/modules/users/{repository,router}.py`
- `backend/app/modules/curriculum/{router,user_state_repository}.py`
- `backend/app/modules/daily_plan/{repository,router}.py`
- `backend/app/modules/learning_events/{repository,router}.py`
- `backend/app/modules/exercises/{repository,router}.py`
- `backend/app/modules/mastery/{repository,router}.py`
- `backend/app/modules/vocabulary_review/{repository,router}.py`
- `backend/app/modules/partner/{repository,router}.py`
- `backend/app/modules/progress/{repository,router,service}.py`
- `backend/app/modules/ai_progress/{repository,router,service}.py`
- `backend/app/modules/student_model/router.py`
- `backend/app/modules/widgets/router.py`

### Removed backend runtime integration

- `backend/app/integrations/firebase/__init__.py`
- `backend/app/integrations/firebase/auth.py`
- `backend/app/integrations/firebase/client.py`
- `backend/app/integrations/firebase/firestore.py`

### iOS application and generated project

- `frontend/project.yml`, `frontend/Alua.xcodeproj/project.pbxproj`
- `frontend/Alua/App/{AluaApp,AppEnvironment,AuthSession,DependencyContainer}.swift`
- `frontend/Alua/Core/Auth/DeviceTokenStore.swift`
- `frontend/Alua/Core/Networking/APIClient.swift`
- `frontend/Alua/Features/Auth/{AuthView,EnrollmentView}.swift`
- `frontend/Alua/Features/Root/RootView.swift`
- `frontend/Alua/Features/Settings/SettingsView.swift`
- `frontend/Alua/Services/EnrollmentService.swift`

### Removed iOS Firebase/login artifacts

- `frontend/Alua/Core/Auth/AuthServiceProtocol.swift`
- `frontend/Alua/Core/Auth/FirebaseAuthService.swift`
- `frontend/Alua/Core/Auth/FirebaseBootstrap.swift`
- `frontend/Alua/Features/Auth/SignInView.swift`
- `frontend/Alua/Features/Auth/SignUpView.swift`
- `frontend/Alua/Resources/GoogleService-Info.plist`
- `frontend/Alua.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`

### Documentation

- `docs/LOCAL_SETUP.md`, `docs/POSTGRESQL_MIGRATION.md`
- `docs/audit/15_firebase_dependency_map.md`
- `docs/MIGRATION_REPORT.md`

The repository already contained extensive uncommitted and untracked application work before this
migration. It was preserved; the list above identifies migration-specific edits.

## 2. Firebase dependencies removed

- Removed `firebase-admin` and its Google Cloud transitive dependency graph from Python/`uv.lock`.
- Removed Firebase Admin initialization, ID-token verification, and Firestore client modules.
- Removed FirebaseCore, FirebaseAuth, and FirebaseMessaging Swift packages.
- Removed Google configuration plist handling and stale Swift package resolution.
- Removed email/password sign-in/sign-up state and UI.
- A runtime-source scan finds no Firebase Admin, Firebase Auth/Core/Messaging, GoogleService plist,
  Google Cloud client, Firestore client, or ID-token verifier references.

The full before/after dependency and ownership map is in
`docs/audit/15_firebase_dependency_map.md`.

## 3. PostgreSQL schema/tables

Alembic revision `20261028_0001` creates:

- `learner_profiles`, `enrollment_codes`, `device_enrollments`
- `daily_plans`, `curriculum_states`
- `vocabulary_packs`, `review_sessions`, `review_responses`,
  `canonical_vocabulary_states`
- `exercise_sessions`, `exercise_answers`
- `learning_events`, `mastery_states`, `mastery_evidence`
- `partner_invitations`, `partner_relationships`, `partner_permissions`
- `progress_analytics`
- `ai_reports`, `ai_conversations`, `ai_messages`

Learner-scoped composite keys prevent cross-learner collisions. Review/learning events and mastery
evidence have immutable repository contracts and idempotency keys. State transitions use database
transactions and row locks. Partial unique PostgreSQL indexes ensure only one active relationship
per learner and per monitoring partner.

The student model remains a deterministic projection of profile, curriculum, and mastery state, so
it does not introduce a duplicate mutable snapshot. Progress responses remain derived and are also
persisted by period.

## 4. Data migration strategy

The optional offline importer accepts a JSON document-path export, validates every recognized
document through the existing Pydantic domain contract, retains the original learner ID, records it
as `legacy_identity_key`, and writes everything in one database transaction when `--apply` is used.
Dry-run is the default and reports unsupported paths. It does not import through, connect to, erase,
or update the remote database.

Supported historical domains are profile, plan, curriculum, learning events, exercise
sessions/answers, mastery states/evidence, vocabulary packs/review sessions/states/events, partner
relationships/permissions/invites, and AI conversations/messages.

If the only artifact is a managed binary export, it must first be converted offline to the
document-path JSON format. With no accessible export, historical progress cannot be reconstructed;
fresh PostgreSQL enrollment remains fully operational.

## 5. Device enrollment implementation

- An administrator creates a high-entropy, short-lived, one-time pairing code from the backend CLI.
- Only the code hash is stored.
- Redemption transactionally creates an independent learner (or links a specifically selected
  migrated learner), consumes the code, and creates a device enrollment.
- The server returns a random 256-bit-class token once; only its SHA-256 hash is persisted.
- iOS stores the raw token with `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` in Keychain.
- `Authorization: Bearer` is added only by the main app API client over the configured HTTPS URL.
- Every protected endpoint resolves the learner from the active token. Request schemas do not accept
  a caller-selected UID.
- Authenticated device listing and learner-scoped revocation are supported. Unlinking the current
  device revokes it server-side, clears Keychain, and clears widget snapshots.

## 6. Endpoint compatibility

Existing learning/profile/progress/partner/widget endpoint paths and response schemas are retained.
Internal `uid`/`user_id` identifiers remain string learner IDs to preserve domain interfaces.

New endpoints:

- `POST /api/v1/enrollment` (the only unauthenticated domain endpoint; accepts one-time code only)
- `GET /api/v1/devices`
- `DELETE /api/v1/device`
- `DELETE /api/v1/devices/{enrollment_id}`

## 7. Widget compatibility

Widget envelope schema remains exactly 5; vocabulary pack schema remains 2. Vocabulary term +
Russian translation, hourly rotation, Review Status/practice, Grammar, Today, Partner, App Group
atomic snapshot activation, version checks, local-day checks, and stale/expiry protection remain.
The extension has no API client, Keychain token, authorization header, or network calls.

## 8. Required Oracle environment variables

Required: `APP_ENV=production`, `DEBUG=false`, `DATABASE_URL`, `DB_POOL_SIZE`,
`DB_MAX_OVERFLOW`, `ENROLLMENT_CODE_TTL_MINUTES`, and `ALLOWED_ORIGINS` (empty is valid for the native
app). OpenAI variables remain required only for enabled OpenAI functionality: `OPENAI_API_KEY`, model,
timeout/retry/token settings, and feature flags.

No Firebase project, credential path, Google application credential, shared iOS secret, or Google
Cloud environment variable is used.

## 9. Deployment commands

Exact database creation, Alembic, enrollment, systemd, Nginx, and HTTPS-oriented command templates
are in `docs/POSTGRESQL_MIGRATION.md`. They deliberately use a separate `alua` role/database,
`alua.service`, port 8101 upstream, and Nginx server block so FLORA is not modified.

No deployment command was executed.

## 10. Validation results

- `uv sync`: passed; Firebase/Google packages removed.
- `ruff format .` and `ruff format --check .`: passed (138 Python files formatted).
- `ruff check .`: passed.
- `mypy app scripts`: passed (133 source files).
- Backend startup without Firebase/Google credentials: passed.
- Alembic initial upgrade and repeat `upgrade head` on disposable databases: passed.
- PostgreSQL offline SQL generation: passed; 21 application tables plus Alembic version table and
  active-partner partial unique indexes emitted.
- Two fresh learners, token-based `/me`, profile isolation, revocation, and post-revocation 401:
  passed.
- Partner direction/ownership and permission redaction: passed.
- Daily plan stable on repeated ensure, exercise session/answer persistence: passed.
- Canonical lexicon exactly 11,196 unique IDs: passed.
- Daily selector cross-process deterministic hash equality: passed.
- Schema-2 daily pack stable across repeated reads: passed.
- Review event replay idempotent; review state survives application restart: passed.
- Progress snapshot persisted: passed.
- Offline migration dry-run validation: passed.
- XcodeGen: passed.
- Xcode Debug app build: passed.
- Explicit `AluaWidgets` scheme build: passed.
- Runtime Firebase/Google dependency scan: zero matches.

## 11. Remaining blockers

- The real Oracle PostgreSQL instance was intentionally not accessed. Production migration execution,
  connection/role verification, Nginx hostname/certificate substitution, systemd installation, and
  HTTPS device testing remain deployment-time tasks.
- Release `API_BASE_URL` intentionally uses `https://alua.example.invalid`; replace it with the final
  HTTPS hostname and regenerate the Xcode project before release.
- No remote database was read. A real offline export is required to confirm and migrate historical
  documents. Any paths reported as unsupported by the dry-run importer require an explicit mapping
  before `--apply`.
- No backend test suite existed in the repository; validation used disposable databases and inline
  integration probes without leaving test files in the repository.
- The existing Pydantic warning that `LexicalItem.register` shadows a base-model attribute remains;
  it does not affect formatting, lint, typing, corpus, or build validation.
