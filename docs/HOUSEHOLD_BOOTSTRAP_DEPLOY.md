> Авторизация Alua 2.1: команды привязки в этом документе устарели. Используйте [актуальную инструкцию S1](ALUA_2_1_STAGE1_AUTH_TRANSITION.md); публичный bootstrap удалён, новые профили не создаются.

# Два профиля Alua: реализация, проверки и обновление Oracle

Дата: 29 октября 2026. Этот документ заменяет инструкции ручного enrollment из ORACLE_IOS_VERIFICATION.md.
Команды ниже подготовлены для владельца сервера, **не выполнялись**. Oracle и FLORA не затрагивались.

## Поведение

Первый запуск: чёрный SwiftUI-экран «Кто будет учиться?» с кнопками «Муж» и «Жена». Без кодов, email, паролей, PIN и QR. Выбор вызывает `POST /api/v1/bootstrap`, сохраняет device token в Keychain и открывает Today. Следующий запуск восстанавливает профиль через существующий `GET /api/v1/me`. Существующие валидные device tokens продолжают работать.

Settings → «Сменить профиль» → подтверждение отзывает текущий токен и очищает Keychain-сессию, learner stores, pending deep link, App Group snapshot и локальные vocabulary notifications. Следующий выбор синхронизирует виджеты. При сетевой ошибке отзыва переключение не завершается, прежняя сессия остаётся доступной, ошибка показывается в Settings. После сбоя восстановления сессии доступны повторная загрузка и выбор профиля.

APIClient использует ephemeral URLSession и отбрасывает ответы со старым токеном. При смене профиля создаются новые store instances. WidgetSyncService проверяет поколение синхронизации, чтобы запоздалый ответ не записал предыдущий snapshot после очистки. WidgetKit schema 5, App Group identifier и формат snapshot не менялись. В extension нет сетевого кода или credentials.

## Модель данных и граница безопасности

`household_profiles` содержит только роли `husband` / `wife`: CHECK + PRIMARY KEY для роли и UNIQUE FK для learner ID. Bootstrap в транзакции создаёт отсутствующие роли; PostgreSQL advisory transaction lock сериализует создание и административные привязки между workers. После подготовки/первого bootstrap присутствуют ровно две постоянные household-привязки.

Старые `learner_profiles`, device enrollments и все таблицы прогресса сохраняются. Количество исторических learner rows может быть больше двух: требование сохранить их исключает их автоматическое удаление. Новые household-профили используют существующий UserRole.LEARNER; это не изменение разрешений Partner Mode.

Привязать существующие данные можно **до первого публичного bootstrap** командой `prepare-household --husband-id ... --wife-id ...`. Она сохраняет старые UUID и весь прогресс без копирования. Повтор той же привязки безопасен. Замена уже назначенной роли или назначение одного learner двум ролям запрещены. Имена не используются для автоматического определения владельца. Если роли уже были созданы на новых UUID, команда не перезапишет их: потребуется отдельное рассмотрение объединения данных.

Bootstrap публичный: любой, кто имеет доступ к API, может выбрать любую из двух ролей и получить токен этого профиля. **Выбор роли не подтверждает личность и не защищает от человека, который намеренно выбирает чужой профиль.** Bearer-токены по-прежнему изолируют запросы между learner ID; без токена защищённые маршруты отвечают 401. Это разделение данных и удобный семейный вход, а не аутентификация владельца.

Приложение генерирует 256-битный случайный `device_secret` через SecRandomCopyBytes и хранит pending secret в Keychain до успешного сохранения токена. Bootstrap детерминированно выводит токен из роли и секрета с отдельным префиксом назначения; в PostgreSQL хранится только SHA-256 токена. Повтор запроса, в том числе после потери ответа или перезапуска приложения, возвращает тот же token/enrollment_id. Новый секрет создаёт другое устройство у того же learner. Отозванный токен повтором не оживляется. Секреты/ответы bootstrap нельзя логировать; вывод response body из debug APIClient удалён.

`POST /api/v1/enrollment` удалён. Публичного создания enrollment-кодов нет, старые записи кодов не удаляются. Новый CLI больше не предлагает генерацию кодов. Старые версии приложения не смогут пройти новый вход через enrollment, но их уже выданные device tokens остаются валидными.

## Проверки

Результат: **3 PostgreSQL integration tests passed**, **2 iOS XCTest passed**, Debug и Release с Widgets — **BUILD SUCCEEDED**. Ruff для изменённых Python-модулей и тестов проходит. В обоих app bundles проверены production API URL и встроенная AluaWidgets.appex. Первый экран визуально проверен в iPhone 17 Pro Simulator; для этой проверки использована ad-hoc подпись (без подписи Keychain в Simulator недоступен).

iOS-тесты `frontend/AluaTests/AuthSessionTests.swift` работают с настоящим Keychain симулятора и подставными API-сервисами: восстановление сессии, запрет повторного выбора после успеха, отзыв при смене профиля, повтор после потерянного ответа и перезапуска. Они не вызывают production API. Для запуска выберите UDID своего симулятора из `xcrun simctl list devices available`:

```bash
xcodebuild -project frontend/Alua.xcodeproj -scheme Alua -configuration Debug \
  -destination 'platform=iOS Simulator,id=SIMULATOR_UDID' \
  CODE_SIGNING_ALLOWED=YES CODE_SIGN_IDENTITY=- test
```

Тесты PostgreSQL выводят существующие предупреждения о Pydantic-поле `register` и Alembic `path_separator`; ошибок нет. Временные базы, QA-симулятор, скриншоты и временные build/test artifacts удалены после проверок.

Регрессионные тесты: `backend/tests/test_household_bootstrap.py`. Это постоянные тесты проекта, не временные файлы. Они самостоятельно запускают временный локальный PostgreSQL 17 в UTF-8 на Unix socket, без TCP, и удаляют кластер при завершении. Не используют DATABASE_URL из рабочего .env.

```bash
cd ~/Projects/Alua/backend
.venv/bin/python -m pytest tests/test_household_bootstrap.py -q
```

Проверяются свежая миграция и обновление старой схемы с прогрессом; повторная миграция; явная идемпотентная привязка старых UUID; ограничения ролей; 24 конкурентных повтора bootstrap; потерянный ответ; новые устройства; отзыв и запрет повторного использования отозванного bootstrap; 48 защищённых API без токена; подмена UID; чужие device IDs; Vocabulary V2, SRS, Grammar, Daily Plan, Progress, Student Model, Partner Mode и widget snapshot schema 5.

В ходе PostgreSQL-проверки Partner Mode обнаружен существующий дефект порядка INSERT: permissions могли сохраняться до родительской relationship. В репозиторий добавлен flush родителя перед permissions; данные и интерфейс Partner Mode не меняются.

Сборка:

```bash
cd ~/Projects/Alua
xcodegen generate --spec frontend/project.yml
xcodebuild -project frontend/Alua.xcodeproj -scheme Alua \
  -configuration Debug -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
xcodebuild -project frontend/Alua.xcodeproj -scheme Alua \
  -configuration Release -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

## Изменённые файлы

Backend: `app/db/models.py`, `app/cli.py`, `app/modules/enrollment/bootstrap.py` (новый), `router.py`, `schemas.py`, `app/modules/partner/repository.py`, миграция `alembic/versions/20261029_0002_household_profiles.py` (новая), `tests/test_household_bootstrap.py` (новый).

iOS: `App/AuthSession.swift`, `App/AluaApp.swift`, `App/VocabularyLearningStore.swift`, `Core/Auth/DeviceTokenStore.swift`, `Core/Networking/APIClient.swift`, `Features/Auth/AuthView.swift`, новый `ProfileSelectionView.swift` вместо удалённого `EnrollmentView.swift`, `Features/Root/RootView.swift`, `Features/Settings/SettingsView.swift`, `Services/EnrollmentService.swift`, `Services/WidgetSyncService.swift`, `Services/VocabularyNotificationService.swift`, `project.yml`, сгенерированные `Alua.xcodeproj/project.pbxproj` и shared scheme, новые `AluaTests/AuthSessionTests.swift`.

Этот отчёт — новый файл документации. Предыдущие несвязанные изменения рабочего дерева сохранены; коммитов и push нет.

## Безопасное обновление Oracle: команды для ручного выполнения

Точные известные параметры:

- адрес `141.144.194.152`;
- backend `/opt/alua/backend-pg`;
- service `alua-api.service`;
- environment `/etc/alua/alua.env`;
- database `alua`;
- upstream `127.0.0.1:8010`;
- HTTPS `https://alua-api.flora-flowers.kz`.

Новые Python-зависимости не добавлены. Используется существующий `/opt/alua/backend-pg/.venv/bin/python`; наличие проверяется перед остановкой. Если production использует другой interpreter, подставьте его из ExecStart. Nginx, FLORA, DNS и порты изменять не нужно.

### 1. Локально подготовить и передать только код Alua

Заменить `YOUR_ORACLE_SSH_USER` своим SSH-пользователем. Команды передачи выполняете вы:

```bash
cd ~/Projects/Alua
ALUA_UPLOAD=$(mktemp -d /tmp/alua-household-upload.XXXXXX)
tar --exclude='__pycache__' --exclude='*.pyc' \
  -czf "$ALUA_UPLOAD/backend.tgz" backend/app backend/alembic
shasum -a 256 "$ALUA_UPLOAD/backend.tgz"
scp "$ALUA_UPLOAD/backend.tgz" YOUR_ORACLE_SSH_USER@141.144.194.152:/tmp/alua-household-backend.tgz
```

В архив не входят `.env`, `.venv`, локальные БД и credentials. После успешной передачи удалите только созданный каталог `$ALUA_UPLOAD`.

### 2. На Oracle: preflight, остановка Alua, резервная копия

В своей SSH-сессии запустите `sudo -i`, затем выполняйте блоки в этой root-сессии. Никаких команд для FLORA:

```bash
set -euo pipefail
ALUA_DIR=/opt/alua/backend-pg
ALUA_PY="$ALUA_DIR/.venv/bin/python"
ALUA_USER=$(systemctl show alua-api.service --property=User --value)
ALUA_GROUP=$(systemctl show alua-api.service --property=Group --value)
test -n "$ALUA_USER"
if [ -z "$ALUA_GROUP" ]; then ALUA_GROUP=$(id -gn "$ALUA_USER"); fi
test -x "$ALUA_PY"
test -f /etc/alua/alua.env
systemctl show alua-api.service --property=WorkingDirectory --property=ExecStart --property=EnvironmentFiles
sha256sum /tmp/alua-household-backend.tgz
# Сверьте SHA-256 с локальным значением, WorkingDirectory и interpreter — с параметрами выше.

install -d -m 700 /opt/alua/backups
ALUA_BACKUP=$(mktemp -d /opt/alua/backups/household.XXXXXX)
ALUA_STAGE=$(mktemp -d /opt/alua/household-stage.XXXXXX)
tar -xzf /tmp/alua-household-backend.tgz -C "$ALUA_STAGE"
test -f "$ALUA_STAGE/backend/app/modules/enrollment/bootstrap.py"
test -f "$ALUA_STAGE/backend/alembic/versions/20261029_0002_household_profiles.py"

systemctl stop alua-api.service
sudo -u postgres pg_dump --format=custom --dbname=alua > "$ALUA_BACKUP/alua.dump"
pg_restore --list "$ALUA_BACKUP/alua.dump" > "$ALUA_BACKUP/alua.dump.list"
tar -czf "$ALUA_BACKUP/code-before.tgz" -C "$ALUA_DIR" app alembic
printf 'Backup: %s\n' "$ALUA_BACKUP"
```

Не продолжайте при ошибке backup. `set -e` останавливает выполнение при ошибках; после ошибки проверяйте состояние сервиса. Не восстанавливайте БД автоматически поверх новых данных.

### 3. Установить код и выполнить добавочную миграцию

```bash
rsync -a --chown="$ALUA_USER:$ALUA_GROUP" \
  "$ALUA_STAGE/backend/app" "$ALUA_STAGE/backend/alembic" "$ALUA_DIR/"

alua_run() {
  systemd-run --quiet --wait --pipe --collect \
    --property=Type=oneshot \
    --property="User=$ALUA_USER" --property="Group=$ALUA_GROUP" \
    --property="WorkingDirectory=$ALUA_DIR" \
    --property=EnvironmentFile=/etc/alua/alua.env \
    "$ALUA_PY" "$@"
}

alua_run -m alembic current
alua_run -m alembic upgrade head
alua_run -m alembic current
# Ожидаем: 20261029_0002 (head).
alua_run -m app.cli list-household-candidates
```

EnvironmentFile читает systemd, не shell; пароли не выводятся. Миграция создаёт только household_profiles. Сервис пока остановлен, поэтому публичный bootstrap не успеет создать новые UUID до привязки истории.

### 4. Выбрать существующие learner ID или явно создать новые

Для двух существующих профилей: по выводу CLI и вашим данным определите UUID мужа и жены. Не угадывайте по порядку строк. Введите их:

```bash
read -r -p 'Existing husband learner UUID: ' ALUA_HUSBAND_ID
read -r -p 'Existing wife learner UUID: ' ALUA_WIFE_ID
test -n "$ALUA_HUSBAND_ID"
test -n "$ALUA_WIFE_ID"
test "$ALUA_HUSBAND_ID" != "$ALUA_WIFE_ID"
alua_run -m app.cli prepare-household \
  --husband-id "$ALUA_HUSBAND_ID" --wife-id "$ALUA_WIFE_ID"
```

Если нужен один старый и один новый профиль, укажите один `--husband-id` либо `--wife-id` и добавьте `--create-missing`. Если история отсутствует и оба профиля должны быть новыми, используйте вместо блока выше:

```bash
alua_run -m app.cli prepare-household --create-missing
```

`--create-missing` не удаляет старые данные, но не связывает их автоматически. Повторите `list-household-candidates` и проверьте оба назначения перед запуском.

### 5. Запуск и проверки без выпуска токенов в терминал

```bash
alua_run -m app.cli list-household-candidates
systemctl start alua-api.service
systemctl is-active alua-api.service
curl --fail --silent --show-error http://127.0.0.1:8010/api/v1/health
curl --fail --silent --show-error https://alua-api.flora-flowers.kz/api/v1/health
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  https://alua-api.flora-flowers.kz/api/v1/me
# Ожидаем 401 без Bearer token.
```

После этого установить новую сборку iOS, выбрать роли на двух устройствах, проверить Today, перезапуск приложения, отдельный прогресс и обновление виджетов. Выпускать токены curl-командами для проверки не требуется. После успешной проверки удалить staging и переданный архив, сохранив backup:

```bash
rm -rf -- "$ALUA_STAGE"
rm -- /tmp/alua-household-backend.tgz
```

### Откат кода при неудаче

В той же root-сессии, с сохранённым ALUA_BACKUP:

```bash
systemctl stop alua-api.service
mv "$ALUA_DIR/app" "$ALUA_BACKUP/app-failed"
mv "$ALUA_DIR/alembic" "$ALUA_BACKUP/alembic-failed"
tar -xzf "$ALUA_BACKUP/code-before.tgz" -C "$ALUA_DIR"
systemctl start alua-api.service
```

Добавочная таблица не мешает старому backend. Alembic downgrade и восстановление дампа не нужны для отката кода; их не выполняйте автоматически. Новый iOS bootstrap при старом backend недоступен — откат приложения/возврат нового backend согласуется отдельно.

## Ограничения проверки

Production и реальная база не посещались; неизвестно, какие существующие UUID соответствуют мужу и жене. Это единственное решение по данным, которое необходимо принять перед запуском обновления. Нельзя безопасно сделать его по исходникам.

Simulator build не проверяет provisioning, аппаратный Keychain и живое обновление App Group на iPhone. AI-вызовы к внешнему провайдеру в тестах отключены. Публичный выбор роли намеренно не является защитой от посторонних.
