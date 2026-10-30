> Авторизация Alua 2.1: команды привязки в этом документе устарели. Используйте [актуальную инструкцию S1](ALUA_2_1_STAGE1_AUTH_TRANSITION.md); публичный bootstrap удалён, новые профили не создаются.

# Alua local setup

## Requirements

- Python 3.12 and `uv`
- PostgreSQL 16 (SQLite may be used only for isolated automated validation)
- Xcode with an iOS 17+ SDK
- XcodeGen
- An optional OpenAI API key for AI-generated exercises and partner analysis

## Backend

Create the dedicated `alua` role/database as described in `POSTGRESQL_MIGRATION.md`. Copy
`backend/.env.example` to `backend/.env`, set `DATABASE_URL`, and keep all credentials out of Git.

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

The health endpoint is `http://127.0.0.1:8000/api/v1/health`. Startup and health do not require
Firebase, Google credentials, or an OpenAI key. OpenAI-backed features fall back or report their
configured unavailability according to their existing service contracts.

Create a fresh one-time pairing code:

```bash
uv run python -m app.cli create-enrollment-code --name User
```

The server stores only the code hash and device-token hash. The raw random device token is returned
once over HTTPS and stored by iOS in Keychain.

## iOS and widgets

```bash
cd frontend
xcodegen generate
xcodebuild -project Alua.xcodeproj -scheme Alua -sdk iphonesimulator \
  -configuration Debug CODE_SIGNING_ALLOWED=NO build
xcodebuild -project Alua.xcodeproj -scheme AluaWidgets -sdk iphonesimulator \
  -configuration Debug CODE_SIGNING_ALLOWED=NO build
```

Debug points to `http://127.0.0.1:8000` for the simulator. Set `API_BASE_URL` in
`frontend/project.yml` to the real HTTPS hostname before a release build, then regenerate the
project. A physical iPhone cannot use the Mac's loopback address.

The main app syncs presentation-only widget snapshot schema 5 into
`UserDefaults(suiteName: "group.com.alua.app")`. The widget extension has no Keychain access,
authorization token, API client, or direct networking. Configure the same App Group capability for
`com.alua.app` and `com.alua.app.widgets` in the Apple Developer portal for signed device builds.

## Validation

```bash
cd backend
uv run ruff format --check .
uv run ruff check .
uv run mypy app scripts
```

Use `alembic upgrade head` against a disposable database to verify migrations. Enrollment, learner
isolation, token revocation, stable daily packs, idempotent review responses, and restart persistence
are covered by the documented validation procedure in the migration report.
