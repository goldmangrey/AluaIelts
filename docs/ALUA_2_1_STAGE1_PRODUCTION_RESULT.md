# Alua 2.1 / S1 — выполненный production переход, 29 октября 2026

Серверная авторизация развернута. **Этап 1 НЕ закрыт:** требуются проверка двух физических iPhone и автоматическая внешняя копия.

## Запущенная версия

- SSH: `ubuntu@141.144.194.152`, служба `alua-api.service`, upstream только `127.0.0.1:8010`.
- Release: `/opt/alua/releases/s1-auth-20261029-eb2621fdaa11`.
- `RELEASE_ID`: `s1-auth-20261029-eb2621fdaa11`; суффикс — первые 12 символов SHA-256 отсортированного JSON manifest Python-файлов `backend/app`.
- API metadata по-прежнему `0.1.0`: это прежний APP_VERSION, а не идентификатор этого deploy.
- Переключение через `/etc/systemd/system/alua-api.service.d/20-stage1-release.conf`.
- Старый `/opt/alua/backend-next` сохранён, но напрямую возвращать его в public service нельзя.
- Production отличался от локальной реализации ровно пятью файлами: `app/cli.py`, `app/modules/enrollment/{bootstrap,router,schemas,service}.py`. Остальной Python-код совпадал. Dependencies скопированы из работающего runtime без обновлений.
- Alembic остаётся `20261029_0002`; production migration не выполнялась.

## Сохранённые данные

- Муж: learner `98b222fb-1e28-494f-bf3f-c125b7f629e0`.
- Жена: learner `588a8cda-928f-4201-813a-de13e1adbd2c`.
- Единственный enrollment: `3c08b3a2-0eb4-4f6a-a6c5-a91d771b887a`, принадлежит мужу, активен.
- Enrollment ID, learner ID, token hash и revoked status не изменялись. Токен не извлекался и не выводился.
- До/после deploy и повторного рестарта совпали fingerprints всех 23 таблиц, включая enrollment и учебные данные.
- В профиле мужа по одной записи: curriculum_states, daily_plans, progress_analytics, review_sessions, vocabulary_packs. Learning events/answers/mastery states на момент снимка пусты. У жены учебных записей не найдено. Это только состояние текущей PostgreSQL, не доказательство отсутствия старой истории в иных системах.
- Остались три старые записи enrollment_codes; действующих кодов на preflight не было. Новые профили/enrollments в production не создавались, коды супруге заранее не выпускались, чтобы не истекли до готовности телефона.
- `confirm-household-devices --apply` НЕ запускалась; ни одно устройство не отозвано.

## Проверки

- Public и loopback health: 200; bootstrap: 404.
- Public anonymous `/me`: 401.
- Public invalid enrollment: 401; конкурентные попытки: 429.
- Соединение приложения с PostgreSQL: database/user `alua/alua`, SELECT 1 успешно.
- Реальный CLI → valid code → HTTP enrollment → /me → повторное погашение → отзыв проверены на Oracle runtime в восстановленной изолированной БД. Production enrollment не затрагивался. Валидный production bearer мужа неизвестен серверу в открытом виде; настоящий вход с ним ещё должен подтвердить владелец телефона.
- Проверен второй restart Alua; `NRestarts=0`, ошибки уровня error в журнале Alua не найдены. Есть прежнее предупреждение Pydantic о поле `register`, не ошибка нового auth.
- `flora-api`, `flora-web`, `nginx`, `postgresql` active. Их времена старта остались прежними, конфигурации/БД/службы FLORA не изменялись; Nginx не перезагружался.

## Backup и restore

Установлен пакет Ubuntu `age` (без обновления других пакетов и без перезапуска FLORA).

- До deploy создан согласованный custom dump только БД Alua. Alua-конфигурации, включая EnvironmentFile, сохранены в закрытом зашифрованном архиве. Секреты не печатались.
- `/var/backups/alua/pre-s1-20261029/`: зашифрованные predeploy dump/config и свидетельство restore. Открытые временные dump/config удалены после проверки.
- Dump расшифрован и восстановлен в НОВОМ временном PostgreSQL 17 cluster, с отдельным Unix socket, без TCP и без доступа к рабочим БД. Все 23 fingerprints совпали с исходной БД. Временный cluster остановлен и удалён; `dropdb`/downgrade рабочей БД не выполнялись.
- Автоматическая копия также расшифрована и восстановлена с тем же результатом.
- `/usr/local/libexec/alua-backup`: ежедневный dump, проверка архива, age encryption, 14 последних успешных архивов, очистка abandoned staging, резерв свободного диска 2 GiB, предварительный storage guard 2 GiB, максимум отдельного файла 256 MiB. При превышении guard backup завершается ошибкой, не удаляя последнюю хорошую копию ради места.
- `/usr/local/libexec/alua-backup-restore-check`: каждые 7 дней до шифрования новый dump автоматически восстанавливается в отдельный временный cluster и проверяется. Первый автоматический restore прошёл.
- `/usr/local/libexec/alua-backup-check`: почасовая проверка свежести (<30 часов), размера архива, failure marker, свежести restore (<9 дней). Ошибка даёт failed systemd unit и запись в отдельный журнал. Удалённые email/push-уведомления не настроены.
- `alua-backup.timer`: ежедневно 04:30 Asia/Almaty + до 10 минут jitter, Persistent=true.
- `alua-backup-check.timer`: каждый час. Оба enabled/active; последние запуски success.
- `/var/lib/alua-backup/status.json`, `failure` при ошибке и `last-restore-success` — локальные статусы.
- Public encryption recipient: `/etc/alua-backup/recipient`. Приватного ключа на VPS больше нет.
- Recovery key находится на Mac: `~/Desktop/my-server/alua-backup-recovery/age-identity-20261029.key` (0600). Его копия проверена перед удалением с VPS. Не терять; поместить дополнительную копию в личный менеджер паролей/защищённое хранилище.
- В той же закрытой директории на Mac сохранены зашифрованные predeploy dump/config. Это разовая аварийная копия вне VPS, **не автоматический внешний backup**.

**Автоматический внешний backup: BLOCKED.** Destination/credentials отсутствуют, пользователь подтвердил отсутствие хранилища. Платные ресурсы не создавались.

Простой кандидат: отдельный private OCI Object Storage bucket Standard в home region, только для зашифрованных Alua dumps, с узкими IAM правами и lifecycle retention. Документация Oracle указывает 20 GB combined для Always Free-only; для paid/trial — отдельные allowances по tiers, в частности 10 GB Standard, и 50 000 requests/month. Реальную свободную квоту и billing state аккаунта нельзя вывести из SSH-доступа к VM. OCI CLI/config на VPS не обнаружены. До создания bucket нужны проверка tenancy home region, текущего usage и бесплатного остатка; ничего не создано автоматически.

Источник: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

## Изоляция Alua

До изменений: 11 GiB RAM, ~10 GiB available, 138 GiB свободного диска; Alua ~160 MiB cgroup / 181 MiB RSS, 7 tasks, ~0.1% CPU; 2 CPU на VM.

`30-resources.conf`:
- MemoryHigh=512M, MemoryMax=1G; CPUQuota=100% (одна CPU из двух), TasksMax=64.
- Один uvicorn worker; pool 2 + overflow 1. `/etc/alua/runtime-limits.env` добавлен ПОСЛЕ исходного EnvironmentFile.
- Только Alua sessions: statement timeout 30s, lock timeout 5s, idle transaction timeout 60s, work_mem 4MB. Настройки общего PostgreSQL/ролей FLORA не изменялись.
- Файловая система API readonly; приватные `/tmp` и `/var/tmp` по 64 MiB tmpfs; проверены в mount namespace живого процесса.
- Restart burst ограничен; API access logging выключен; namespace журнала `alua` ограничен 64 MiB на диске / 16 MiB runtime, retention 7 дней и rate limit.
- Backup job имеет собственные CPU=50%, MemoryMax=512M, timeout, file size limit и низкий IO priority.
- После рестарта Alua ~80–86 MiB; OOM/restart loops нет.

Это ограничения API/backup, не жёсткая изоляция общей службы PostgreSQL и не лимит размера БД. Общие Nginx/PostgreSQL остаются общей инфраструктурой; их глобальные конфигурации не менялись.

## iPhone: требуется участие владельца

Подписанный Release archive подготовлен и подпись проверена:
`~/Desktop/my-server/alua-release/Alua-S1-20261029.xcarchive`.
Приложение: `com.alua.app`, version 1.0.0 (1), production HTTPS API. Provisioning profile содержит два устройства, но их соответствие конкретным iPhone пока не подтверждено. Keychain/App Group/signing identity в проекте не менялись.

1. На iPhone мужа открыть уже установленную Alua без удаления приложения и проверить свой профиль/прогресс после server deploy. Подтвердить фактический результат.
2. Подключить iPhone к Mac, разблокировать и подтвердить доверие. Установить новую сборку ПОВЕРХ текущей через Xcode (проект `frontend/Alua.xcodeproj`, схема Alua, выбрать подключённый iPhone, Run). Не удалять приложение и не менять team/bundle ID. Можно использовать подготовленный signed .app из archive через Xcode Devices.
3. На iPhone мужа Settings → «Проверить ID устройства»: ожидаемый enrollment указан выше. Сверить, что профиль остался прежним.
4. На iPhone жены установить ту же новую сборку; должен быть экран одноразового кода. Сообщить готовность — тогда выпустить свежий код для существующего wife learner, сохранить его приватно и ввести лично. В отчёты/чат код не публиковать. Код заранее не выпущен: TTL 15 минут.
5. На обоих телефонах закрыть/открыть приложение, проверить самостоятельный вход и раздельный прогресс; проверить виджеты. Только после этого считать физическую проверку пройденной. Любой последующий отзыв неизвестного enrollment требует отдельного подтверждения владельца.

CLI выдачи кода выполняется из текущего release под `alua`, через systemd-run с `/etc/alua/alua.env`, с обязательным `--learner-id 588a8cda-928f-4201-813a-de13e1adbd2c` и `--output /run/alua-provisioning/wife-code`; directory уже подготовлен с mode 0700. Полный общий wrapper есть в инструкции перехода.

## Безопасный rollback

- Подготовлен `/opt/alua/releases/pre-s1-safe-20261029`: прежний backend с принудительно отключённым bootstrap. Проверка HTTP 404 прошла в изолированном окружении.
- `/usr/local/sbin/alua-rollback-safe` переключает ТОЛЬКО Alua на этот каталог, сохраняет resource limits и БД, перезапускает Alua, проверяет health/bootstrap. При неуспешной проверке безопасности останавливает только Alua.
- Скрипт установлен и syntax проверен; реальный production rollback не выполнялся, поскольку deploy прошёл успешно.
- Не возвращать исходный backend-next публично, не делать downgrade/restore БД ради отката кода, не оживлять отозванные токены. В безопасной старой версии первичная привязка недоступна; существующие токены работают.

## Локальные изменения этого выполнения

Добавлены операционные scripts/units в `deploy/stage1/` и этот отчёт. Подготовлены локальные signed archive и recovery artifacts вне git. Backend/iOS бизнес-код не менялся. Временные проверочные файлы удалены. Commit/push не выполнялись.
