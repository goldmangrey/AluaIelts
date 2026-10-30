> Серверный переход выполнен 29 октября 2026. Актуальный результат, особый порядок для одного enrollment и оставшиеся блокеры: [production report](ALUA_2_1_STAGE1_PRODUCTION_RESULT.md). Ниже сохранён первоначальный общий план; физические iPhone и внешний автоматический backup ещё не приняты.

# Alua 2.1 / S1: безопасная привязка устройств

Это инструкция для новой реализации, не отчёт о выполнении на Oracle. Deploy, production SQL, миграции, commit/push не выполнялись. FLORA не изменять. Старые инструкции `prepare-household --create-missing` и публичный bootstrap больше не применяются.

## Контракт

- `POST /api/v1/bootstrap` удалён (404), реализации выдачи по роли нет. Compatibility flag отсутствует.
- Старые device tokens продолжают работать через неизменный `get_current_user` и SHA-256 в `device_enrollments`. Никакой автоматической ротации/отзыва при обновлении.
- `POST /api/v1/enrollment`: `{code, device_name?}`; код — 32 hex-символа (128 случайных бит), привязан к существующему learner. Ответ прежнего типа `{token, enrollment_id, profile}`, `Cache-Control: no-store`.
- CLI TTL по умолчанию 15 минут, допустимо 1–30. Код только в новом файле 0600, не stdout/journal/аргументах процесса. В БД только hash. Не помещать этот файл в git, backup приложения или общую директорию.
- Общая PostgreSQL advisory try-lock и задержка 1 секунда ограничивают проверку кодов во всех workers: одновременно проходит один запрос, конкурирующие получают 429. Случайность кода защищает от перебора; throttle не заменяет сетевую защиту от DDoS. При атаке первичная привязка может временно быть недоступна, обычный bearer-вход этим throttle не затрагивается.
- Погашение кода, создание enrollment и отметка redeemed выполняются в одной транзакции с блокировкой строки. Код без learner ID отвергается; новые learner не создаются.
- Схема БД, learner IDs, существующие enrollment IDs, Keychain service/account, bundle IDs, entitlements/App Group и widget schema v5 не изменяются.
- Настройки показывают только learner ID и current enrollment ID (`GET /devices`, `is_current`). Это не секреты. UI свободного выбора роли удалён.

## Порядок перехода: не переставлять шаги

1. Проверить реальную версию backend и metadata службы. Локальные исходники не доказывают состояние Oracle. По предыдущим сведениям служба `alua-api.service`, upstream 8010, путь `/opt/alua/backend-next`, но это требуется подтвердить. Не устанавливать старый пример systemd с 8101.
2. Проверить наличие таблиц `enrollment_codes`, `device_enrollments`, `household_profiles`, текущую Alembic revision, отдельную БД/роль Alua. Если схема отличается — остановить переход, не запускать автоматически migrations/create_all. Для этой реализации migration не нужна.
3. Сделать проверенную резервную копию Alua и сохранить текущий release/unit/drop-ins. Не копировать FLORA и не восстанавливать общий кластер. Зафиксировать household UUID и counts учебных записей каждого learner.
4. Установить новую iOS-сборку поверх существующей на ОБА телефона, сохранив signing identity. НЕ удалять приложение/Keychain, НЕ отзывать токены. Новый iOS читает существующий `/devices` старого backend; при его отсутствии переход остановить до согласования совместимости.
5. На каждом физическом телефоне: обычный вход, правильный профиль, Settings → «Проверить ID устройства». Владелец лично сопоставляет learner UUID с household role и записывает два точных enrollment UUID. Имя устройства/IP/last_used недостаточны. Если старый токен уже недействителен, сначала отдельно восстановить доступ; не переходить к массовому отзыву.
6. Запустить из candidate CLI проверку двух ID БЕЗ `--apply`. На старом backend выдача по роли ещё открыта — провести переход в коротком контролируемом окне.
7. После подтверждения двух телефонов переключить только Alua на проверенный candidate. Конкретные команды переключения зависят от реального unit/release layout; не перезаписывать его шаблоном. Новый backend закрывает bootstrap сразу, без флага.
8. Проверить 404 bootstrap; оба iPhone повторно открывают приложение и получают свой профиль/прогресс без кода. Health недостаточно: он не проверяет БД. До успеха на обоих устройствах НЕ запускать `--apply`.
9. Повторить CLI validation, затем `--apply` с теми же двумя ID. Команда в одной транзакции проверяет разные правильные household profiles, существование и активность обоих enrollment, отзывает ВСЕ прочие активные enrollments в БД Alua (включая прежние профили), истекает ВСЕ непогашенные коды. Профили и учебные записи не удаляет. Если обнаружены другие законные пользователи — остановиться, этот продукт рассчитан на два устройства.
10. Проверить вход обоих телефонов, их неизменные IDs/историю, отказ отозванным токенам, очистку/обновление собственных виджетов. Проверить состояние FLORA только чтением. Новые recovery-коды выпускать уже после pruning.

## Команды Oracle — шаблоны, здесь не выполнялись

Сначала только чтение metadata (не выводить Environment/пароли):

```bash
sudo systemctl show alua-api.service \
  --property=User --property=Group --property=WorkingDirectory \
  --property=ExecStart --property=EnvironmentFiles --property=DropInPaths
sudo systemctl is-active alua-api.service
```

В приватной bash-сессии задайте значения ПОСЛЕ проверки. Путь candidate содержит эту новую реализацию CLI; EnvironmentFile должен указывать только на Alua. Значения ниже — placeholders, не факты о VPS.

```bash
ALUA_S1_DIR='/confirmed/alua/candidate'
ALUA_S1_PYTHON="$ALUA_S1_DIR/.venv/bin/python"
ALUA_S1_ENV='/confirmed/alua/environment-file'
ALUA_S1_USER='confirmed-alua-user'
ALUA_S1_GROUP='confirmed-alua-group'

alua_s1_admin() {
  sudo systemd-run --quiet --wait --pipe --collect \
    --property=Type=oneshot \
    --property="User=$ALUA_S1_USER" --property="Group=$ALUA_S1_GROUP" \
    --property="WorkingDirectory=$ALUA_S1_DIR" \
    --property="EnvironmentFile=$ALUA_S1_ENV" \
    "$ALUA_S1_PYTHON" -m app.cli "$@"
}

alua_s1_admin list-household-candidates
read -r -p 'Enrollment ID с iPhone мужа: ' ALUA_S1_HUSBAND
read -r -p 'Enrollment ID с iPhone жены: ' ALUA_S1_WIFE
alua_s1_admin confirm-household-devices \
  --husband-enrollment-id "$ALUA_S1_HUSBAND" \
  --wife-enrollment-id "$ALUA_S1_WIFE"
```

После отдельного переключения backend и проверки ОБОИХ iPhone:

```bash
# Безопасная отрицательная проверка: нет настоящего секрета, тело ответа не выводится.
# До переключения НЕ запускать: старый backend выдал бы enrollment.
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
  -H 'Content-Type: application/json' \
  --data '{"role":"wife","device_secret":"0000000000000000000000000000000000000000000000000000000000000000"}' \
  https://alua-api.flora-flowers.kz/api/v1/bootstrap
# Ожидаем 404. Если получили 200 — остановиться, не выполнять pruning.

alua_s1_admin confirm-household-devices \
  --husband-enrollment-id "$ALUA_S1_HUSBAND" \
  --wife-enrollment-id "$ALUA_S1_WIFE" --apply
```

Только для нового/восстанавливаемого устройства, не для ежедневного входа:

```bash
sudo install -d -m 700 -o "$ALUA_S1_USER" -g "$ALUA_S1_GROUP" /run/alua-provisioning
read -r -p 'Существующий household learner UUID: ' ALUA_S1_LEARNER
alua_s1_admin create-enrollment-code \
  --learner-id "$ALUA_S1_LEARNER" --ttl-minutes 15 \
  --output /run/alua-provisioning/one-time-code
```

Открыть файл только в приватной административной сессии, передать код лично владельцу нужного телефона, ввести на экране привязки. Не присылать в чат/логи. После использования удалить `/run/alua-provisioning/one-time-code`; команда специально отказывается перезаписывать существующий файл. После успешной замены телефона снова подтвердить пару текущих enrollment ID и отозвать остальные.

## Сбой ответа и восстановление

Если сервер погасил код, но ответ потерялся или Keychain не сохранил токен, повторное погашение запрещено. CLI выдаёт новый код для того же learner; после успешного входа подтвердить пару устройств и отозвать лишние enrollment. Это редкое административное действие, не ежедневный UX. Автоматического role fallback нет.

Токен `AfterFirstUnlockThisDeviceOnly` не предназначен для переноса на новый iPhone. Временная ошибка чтения Keychain или сети ведёт на повтор загрузки, а не на перезапись токена. Серверный 401 по-прежнему требует повторной доверенной привязки.

## Rollback

- Не откатывать БД и не запускать Alembic downgrade ради отката кода. Не оживлять все отозванные токены.
- До pruning можно остановить переход, сохранив оба токена, и исправить candidate.
- Небезопасный старый backend нельзя просто вернуть публично: он вновь откроет bootstrap. Предпочтителен предыдущий проверенный security-compatible release. Если имеется только старый release, сначала блокировать bootstrap в отдельном Alua server block (не FLORA), проверить Nginx config и отсутствие прямого внешнего доступа к upstream; иначе остановить только Alua до исправления.
- После pruning исправление/переключение кода сохраняет два разрешённых enrollment. При потере конкретного токена использовать новый одноразовый код для прежнего learner.
- Новая iOS-сборка совместима с прежними токенами, но первичная привязка требует нового backend. Старый iOS после потери токена уже не сможет выбрать роль; обновить приложение, не открывать bootstrap.

## Локальная проверка

Изолированный временный PostgreSQL, не DATABASE_URL production: существующий suite адаптирован к удалению bootstrap, сохранены проверки разделения пользователей, учебного flow, widget v5 и сохранения legacy progress. Дополнительные временные проверки CLI, TTL, unbound codes и конкурентного погашения удаляются после запуска. iOS AuthSession tests адаптированы к enrollment; тесты используют отдельные Keychain accounts и mock services. Для запуска host приложения в симуляторе использовать build override `API_BASE_URL=http://127.0.0.1:9`.

Результат локальной проверки реализации: 5 PostgreSQL tests passed (3 существующих адаптированных + 2 временных расширенных), 2 iOS AuthSession tests passed с реальным Keychain симулятора. Временные файлы удалены. `ruff check` для изменённых Python-файлов прошёл. Первоначальный запуск iOS без подписи дал Keychain -34018; повтор с ad-hoc simulator signing прошёл, настройки подписи в проекте не менялись.

Воспроизводимый iOS запуск (override URL только для тестовой сборки, не для выпуска):

```bash
xcodebuild -project frontend/Alua.xcodeproj -scheme Alua \
  -destination 'platform=iOS Simulator,id=YOUR_SIMULATOR_UDID' \
  -derivedDataPath /tmp/alua-s1-tests \
  CODE_SIGN_IDENTITY=- API_BASE_URL=http://127.0.0.1:9 test
```

Проверка двух физических iPhone, production schema/release и переход на Oracle ещё не выполнены. Автоматические backups и ресурсная изоляция не входили в этот инкремент авторизации.
