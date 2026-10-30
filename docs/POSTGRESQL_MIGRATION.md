> Авторизация Alua 2.1: команды привязки в этом документе устарели. Используйте [актуальную инструкцию S1](ALUA_2_1_STAGE1_AUTH_TRANSITION.md); публичный bootstrap удалён, новые профили не создаются.

# Alua PostgreSQL migration and operations

## Local database and migrations

Create a dedicated database and least-privilege role (run as a PostgreSQL administrator):

```sql
CREATE ROLE alua LOGIN PASSWORD 'replace-with-a-generated-password';
CREATE DATABASE alua OWNER alua ENCODING 'UTF8';
REVOKE ALL ON DATABASE alua FROM PUBLIC;
```

Configure `DATABASE_URL=postgresql+psycopg://alua:<password>@127.0.0.1:5432/alua`, then run:

```bash
cd backend
uv sync --frozen
uv run alembic upgrade head
```

Create the two initial independent learner/device links one at a time. Each command prints a
single-use, short-lived code; enter each code on the corresponding iPhone:

```bash
uv run python -m app.cli create-enrollment-code --name User
uv run python -m app.cli create-enrollment-code --name Wife
```

For a learner imported with an existing identity, target that learner instead of creating another:

```bash
uv run python -m app.cli create-enrollment-code --name User --learner-id EXISTING_LEARNER_ID
```

## Offline source-data import

`scripts/migrate_firestore_export.py` never contacts or changes the remote source. It accepts an
offline JSON document export as either a map of document paths to data or:

```json
{"documents": [{"path": "users/original-uid", "data": {}}]}
```

Validate first, inspect `unsupported_paths`, then explicitly apply:

```bash
uv run python scripts/migrate_firestore_export.py export.json --report import-report.json
uv run python scripts/migrate_firestore_export.py export.json --apply --report import-report.json
```

Original learner IDs are retained and recorded in `legacy_identity_key`. The importer covers
profiles, plans, curriculum, learning events, exercise sessions/answers, mastery projections and
evidence, vocabulary packs/sessions/states/events, partner relationships/permissions, and invites.
Owner-pointer documents are intentionally reconstructed from relationship data.

A Google-managed binary export is not parsed directly because doing so would add Google Cloud
libraries to the runtime. Convert it offline to the documented JSON shape first. If billing or
source access is unavailable and no export exists, fresh PostgreSQL enrollment works normally;
unavailable historical progress cannot be recovered.

## Oracle host configuration (commands only; not executed)

Required environment variables:

```dotenv
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+psycopg://alua:REPLACE@127.0.0.1:5432/alua
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
ENROLLMENT_CODE_TTL_MINUTES=30
ALLOWED_ORIGINS=
OPENAI_API_KEY=
OPENAI_EXERCISE_GENERATION_ENABLED=true
OPENAI_PROGRESS_ANALYSIS_ENABLED=true
```

Copy `deploy/alua.service.example` and `deploy/nginx-alua.conf.example`, replace placeholders, and
use a separate Unix user, directory, database, systemd unit, and Nginx server block from FLORA.
Suggested deployment sequence after an explicit deployment decision:

```bash
sudo install -d -o alua -g alua /opt/alua
cd /opt/alua/backend
sudo -u alua uv sync --frozen
sudo -u alua uv run alembic upgrade head
sudo install -m 0644 /opt/alua/deploy/alua.service.example /etc/systemd/system/alua.service
sudo systemctl daemon-reload
sudo systemctl enable --now alua.service
sudo install -m 0644 /opt/alua/deploy/nginx-alua.conf.example /etc/nginx/sites-available/alua
sudo ln -s /etc/nginx/sites-available/alua /etc/nginx/sites-enabled/alua
sudo nginx -t
sudo systemctl reload nginx
```

Back up PostgreSQL before each later migration. Run Alembic once per release before restarting the
unit. Never point Alua at the FLORA database or reuse FLORA's service account, socket, or Nginx
upstream.
