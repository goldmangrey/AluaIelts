# Что это за Markdown-файл

`AUDIT_REPORT.md` — единый самодостаточный отчёт глубокого технического аудита монорепозитория Alua. В нём собраны итог всех 15 фаз, доказательства, полный список находок, результаты SRS-симуляции, проверка гипотез владельца, дорожная карта и план тестирования. Для разбора аудита достаточно только этого файла; остальные материалы в `docs/audit/` являются воспроизводимыми приложениями.

# Alua — главный отчёт аудита

Дата: 2026-10-28. Объект: текущее рабочее дерево, включая незакоммиченные файлы. Продакшен, Firebase, Cloud Run и OpenAI не вызывались.

## 1. Резюме

Alua уже имеет хорошо разделённые FastAPI-модули, обязательную Firebase-аутентификацию и рабочую iOS/Widget сборку.
Canonical Vocabulary V2 действительно содержит 11 196 записей, уникальные ID и полные source/provenance; заявленные категории и IPA 77,5% совпали.
Selector детерминирован в 20 отдельных процессах; pack/session IDs и review event/state транзакция спроектированы аккуратно.
Главный риск — не формула интервалов, а граница «pack → показ»: слово считается introduced при генерации, даже если не вошло в session.
Из-за 30 новых при capacity 24 часть слов навсегда исчезает из обучения; симуляция оценила 1 917–2 014 таких элементов за 180 идеальных дней.
Review debt появляется уже на четвёртый день, а после двухнедельного пропуска достигает 173–196 карточек.
Again 30 минут записывается в state, но текущая immutable session не может показать его повторно.
Exercise answer изменяет пять сущностей без общей transaction/outbox; сбой посередине создаёт рассогласованное состояние.
iOS не имеет offline event queue, retry после 401 и безопасного декодирования новых enum cases.
AI защищён от части prompt injection, но не имеет user/day quota и денежного потолка.
В репозитории нет backend/iOS тестов, Firestore rules/indexes, CI/CD, backup/runbook и подтверждённого dev/prod разделения.
При этом `ruff`, `mypy`, Python compile и полная iOS Simulator build проходят — кодовая база компилируется чисто.
До расширения AI/analytics следует стабилизировать ежедневный цикл, offline/idempotency и эксплуатационные гарантии.

## 2. Топ-10 узких мест

Шкала влияния/вероятности: 1–5. Трудоёмкость: S/M/L.

| # | Категория | Узкое место | Влияние | Вероятность | Работа |
|---:|---|---|---:|---:|---|
| 1 | обучение/корректность | Непоказанный pack item уже считается introduced и теряется | 5 | 5 | M |
| 2 | данные | Exercise attempt/event/mastery/session/plan не атомарны | 5 | 4 | L |
| 3 | обучение/SRS | Capacity 12+12 не выдерживает политику 30/20/10 | 5 | 5 | M |
| 4 | обучение/SRS | Again 30 минут невозможно обслужить текущей session | 4 | 5 | M |
| 5 | качество | Нет ни одного backend/iOS автотеста | 5 | 5 | M |
| 6 | iOS/данные | Нет offline queue и гарантированной повторной отправки | 5 | 4 | L |
| 7 | совместимость | Неизвестный backend enum ломает Codable response | 4 | 4 | M |
| 8 | безопасность/стоимость | AI без per-user quota и money ceiling | 4 | 4 | M |
| 9 | эксплуатация | Один API URL для Debug/Release; нет backup/CI/runbook | 4 | 4 | L |
| 10 | масштабируемость | Full scans packs/states/mastery markers на горячих экранах | 3 | 5 | M |

## 3. Полная таблица находок

| ID | Sev | Статус | Область | Описание и доказательство | Как воспроизвести | Рекомендация | Работа |
|---|---|---|---|---|---|---|---|
| AUD-00-01 | S2 | VERIFIED | git | Новые модули untracked; история всего 2 коммита | `git status --short`; `git log` | Сохранить baseline atomic commits | S |
| AUD-00-02 | S2 | VERIFIED | ops | CI/rules/indexes не найдены | `rg --files` по `.github`, rules/indexes | Версионировать CI и Firebase config | M |
| AUD-01-01 | S2 | VERIFIED | content | 234 examples вместо 254 | `scripts/content_audit.py` | Исправить описание или добавить 20 примеров | S |
| AUD-01-02 | S2 | VERIFIED | selector | 70/20/10 меняется на малых budget/краях | `selector.py:103-118` | Явно определить boundary policy и тесты | S |
| AUD-02-01 | S2 | VERIFIED | data | 71 duplicate lemma+POS groups | `scripts/content_audit.py` | Merge/alias после curator review | M |
| AUD-02-02 | S2 | VERIFIED | data | 17 переводов с латиницей, ≥3 явных смешения | `scripts/content_summary.txt` | Ручная правка и validation allowlist | S |
| AUD-02-03 | S2 | VERIFIED | data | CEFR отсутствует у 6 196 записей | `content_audit.py`; `selector.py:126` | Не считать missing текущим уровнем | M |
| AUD-03-01 | S1 | VERIFIED | SRS | Pack presence = introduced; unseen больше не выбирается | `service.py:203-204,281-295` | Mark introduced только при первом показе/event | M |
| AUD-03-02 | S1 | LIKELY | SRS | Debt с 4-го дня; gap peak 173–196 | `scripts/srs_summary.csv` | 5–10 new, zero-new threshold, adaptive cap | M |
| AUD-03-03 | S1 | VERIFIED | SRS | Again=30m не входит в уже созданную session | `scheduler.py:14-16`; `service.py:276-295` | Intra-day relearning queue | M |
| AUD-04-01 | S1 | VERIFIED | pack | Непросмотренный вчерашний pack исключает IDs навсегда | `service.py:203-204` | Persist exposure state отдельно | M |
| AUD-04-02 | S2 | VERIFIED | selector | 10 upgrades исчерпываются за 2 дня | `selector.py:44-68` | Treat upgrades as reusable/periodic, не NEW once | S |
| AUD-05-01 | S0 | VERIFIED | consistency | Exercise pipeline — 5 независимых writes | `exercises/service.py:145-215` | Transaction/outbox + reconciler | L |
| AUD-05-02 | S2 | VERIFIED | events | Repository returns existing event without payload check | `learning_events/repository.py:36-54` | Compare immutable payload in repository/transaction | S |
| AUD-05-03 | S2 | VERIFIED | repair | Rebuild/reconciliation projections не найден | repository search | Add replay/reconcile dry-run tools | M |
| AUD-06-01 | S2 | VERIFIED | Firestore | `/today` stream all packs and states | `vocabulary_review/repository.py:66-123` | Indexed date/due queries + introduced ledger | M |
| AUD-06-02 | S2 | VERIFIED | Firestore | Mastery count scans every marker | `mastery/repository.py:45-53` | Aggregation count/counter | S |
| AUD-06-03 | S1 | VERIFIED | Firestore | Rules/indexes absent from repo | file inventory | Add deny-by-default rules + emulator tests | M |
| AUD-07-01 | S1 | VERIFIED | AI | Нет user/day/spend limits; до 2 calls/action | `ai_progress/service.py:54-67,114-148` | Quota doc + atomic charge + global kill switch | M |
| AUD-07-02 | S1 | VERIFIED | privacy | Account deletion и App Check не найдены | repo-wide search | Delete workflow; App Check enforcement | L |
| AUD-07-03 | S2 | VERIFIED | Docker | Unpinned base, process root | `Dockerfile:1-18` | Pin digest; non-root user | S |
| AUD-08-01 | S2 | VERIFIED | latency | Widget/partner paths compose many reads/scans | `widgets/service.py:87-185` | Cache/materialized snapshot; query budgets | M |
| AUD-08-02 | S2 | VERIFIED | async | Sync Firestore/OpenAI routes вынесены в threadpool; прямого blocking I/O в loop не найдено | router inspection | Сохранить pattern; добавить latency tests | S |
| AUD-08-03 | S2 | HYPOTHESIS | Cloud Run | Runtime sizing/min instances unknown | deploy config absent | Version Cloud Run config and load test | M |
| AUD-09-01 | S1 | VERIFIED | iOS | Нет disk-backed offline event queue | `APIClient.swift:28-42` | Durable outbox with idempotency ID | L |
| AUD-09-02 | S1 | VERIFIED | iOS | Нет forced-refresh 401 retry/timeouts/backoff | `APIClient.swift:28-43,64-100` | One refresh retry; bounded retry/backoff | M |
| AUD-09-03 | S1 | VERIFIED | compatibility | Strict Codable enums | `VocabularyLearningModels.swift:3-6` | Custom unknown case or version gate | M |
| AUD-09-04 | S2 | VERIFIED | environment | Debug=Release URL | `project.yml:31-36` | Separate dev/staging/prod configs/projects | M |
| AUD-09-05 | S2 | VERIFIED | UX | Hardcoded strings; speech en-US/no fallback | `VocabularyReviewSessionView.swift:78-79` | String Catalog; voice fallback/audio session | M |
| AUD-10-01 | S2 | VERIFIED | widgets | Staged UserDefaults write проверяется, но multi-key atomicity не гарантирована | `WidgetSnapshotStorage.swift:15-24` | Один atomic file/replace или generation pointer | M |
| AUD-10-02 | S1 | VERIFIED | widgets | Старый snapshot исчезает сразу после смены даты | `WidgetSnapshotStorage.swift:7-12,40-46` | Show stale state + last sync; background refresh | S |
| AUD-10-03 | S2 | VERIFIED | widgets | До 49 entries × 5, шаг 30m | `WidgetTimelineProvider.swift:41-49` | Per-widget cadence; ≤hourly vocab | S |
| AUD-11-01 | S2 | VERIFIED | maintainability | Router DI graphs дублируются | `exercises/router.py:44-100` | Cached providers/application container | M |
| AUD-11-02 | S2 | LIKELY | architecture | Legacy vocabulary и canonical V2 расходятся | два content repository | Сделать V2 единым source of truth | L |
| AUD-12-01 | S1 | VERIFIED | tests | `pytest`: no tests; iOS test target absent | commands в фазе 12 | Critical-path suite first | M |
| AUD-12-02 | S2 | VERIFIED | Pydantic | `register` shadows BaseModel | `models.py:49-68` warning | Alias field / rename internal attribute | S |
| AUD-13-01 | S1 | VERIFIED | operations | Нет подтверждённого dev/prod separation | `project.yml:31-36` | Separate projects and credentials | L |
| AUD-13-02 | S2 | VERIFIED | operations | Backup/rollback/runbook/diagnostics отсутствуют | inventory | Operational baseline and restore drill | M |
| AUD-13-03 | S2 | VERIFIED | migrations | Старые review schemas молча скрываются | `repository.py:66-77,111-123` | Explicit migration/quarantine metrics | M |

S0 = риск потери/порчи данных или критичной уязвимости; S1 = ломает ежедневный цикл; S2 = заметное ухудшение/будущий риск; S3 = мелочь/долг.

## 4. SRS simulation

Симулятор: `scripts/srs_simulation.py`; результаты: `scripts/srs_summary.csv`. Он повторяет интервалы scheduler и capacity 24 в будний/субботний день, 52 в воскресенье; sub-day due консервативно переносит на следующий учебный день. Firestore service напрямую не импортирован, поэтому статус LIKELY.

| Good/Hard/Again | Поведение | Первый debt | Peak due | Peak debt | Unseen/stranded new |
|---|---|---|---:|---:|---:|
| 85/10/5 | идеально | 2026-01-08 | 64 | 40 | 2 014 |
| 85/10/5 | 2 пропуска/нед | 2026-01-06 | 64 | 48 | 2 296 |
| 85/10/5 | gap 2 недели | 2026-01-14 | 197 | 196 | 2 074 |
| 70/20/10 | идеально | 2026-01-08 | 53 | 29 | 1 917 |
| 70/20/10 | 2 пропуска/нед | 2026-01-06 | 71 | 57 | 1 868 |
| 70/20/10 | gap 2 недели | 2026-01-08 | 179 | 173 | 1 917 |

Рекомендуемый старт: 8 новых/день; 4 при due 15–29; 0 при due ≥30; intra-day Again не считать в дневной cap; обычный cap 30, recovery cap 40, weekly не заменяет evening; каждую неделю автоматически калибровать по P90 debt и completion. При 5–8 сек чистое время для 24/40/52 ответов — 2–3,2 / 3,3–5,3 / 4,3–6,9 минуты; реальное чтение/озвучка увеличит его.

## 5. Расхождения описания и кода

Полная сверка: [01_drift.md](01_drift.md). Главное: examples 234, не 254; Hard определён; 70/20/10 приблизительно, а не строго на малых budget/краях; timezone явный; pack race защищена; review event/state транзакционны. Отсутствуют обещания эксплуатации: backup, App Check, account deletion, offline queue. Все численные характеристики корпуса, 5 stages/197 nodes/117 lessons/117 errors/10 contrasts и версии контрактов совпали.

## 6. Дорожная карта

### За 1 день

1. Снизить новые до 8/4/0 по debt; временно запретить 30. Зачем: остановить потерю/рост долга. Проверка: 30-дневный deterministic simulation без stranded IDs.
2. Изменить семантику introduced: только first exposure/review event. Зачем: вернуть непоказанные слова. Проверка: pack 30, session 12, оставшиеся 18 доступны завтра.
3. Добавить 15 unit tests scheduler/selector/pack IDs/schema/timezone. Зачем: зафиксировать контракт. Проверка: CI green.
4. Поставить AI kill switch default-off в prod до quota. Зачем: ограничить расход. Проверка: endpoint 503 без OpenAI call.
5. Показывать stale widget snapshot с timestamp вместо nil. Зачем: не делать виджеты пустыми после полуночи.

### За 1 неделю

1. Реализовать intra-day Again queue и adaptive sessions; симуляция + clock tests.
2. Durable iOS outbox для review/events с stable event ID, exponential backoff и one-time 401 refresh.
3. Fault-injection/outbox для exercise pipeline или единая Firestore transaction там, где документы укладываются в пределы.
4. Версионировать Firestore rules/indexes и emulator tests на IDOR/Partner revoke.
5. Separate Debug Firebase/API project; добавить request IDs, latency/read counters и OpenAI quota.
6. Curator pass по 71 duplicates, 17 latin translations и missing CEFR policy.

### За 1 месяц

1. Reconciliation/replay для events→review/mastery/progress; ежедневный invariant audit.
2. Убрать full scans: due query, introduced ledger, aggregate marker count, cached widget snapshot.
3. CI/CD с backend+iOS builds, emulator integration, schema compatibility fixtures и rollback.
4. Backup/export schedule и проверенный restore drill; account deletion; App Check.
5. Consolidate legacy vocabulary и V2, затем удалить дублированный слой после migration.

## 7. Чего пока делать не нужно

Не расширять AI Progress, AI exercise variation, Student Model и сложные Partner/Progress analytics, пока ежедневный cycle не имеет тестов, offline delivery и reconciliation. AI Exercise можно оставить за feature flag с deterministic fallback. Не удалять модули немедленно: сначала добавить endpoint telemetry на 2–4 недели. Не усложнять SRS «умной» моделью — текущая проблема в capacity/exposure semantics, не в формуле Good.

## 8. План тестов

Автоматизация по порядку:

1. Scheduler: все ratings, ceiling, exact timestamps, repeated Again/Hard.
2. Selector: 20 processes; A1/C2 boundaries; exhausted kinds; zero words; stable content version.
3. Pack: concurrent create, malformed revision, first exposure, missed day, timezone travel/midnight.
4. Events: same/different idempotency payload; two devices; transaction failure and replay.
5. Exercise pipeline: fault after каждого из пяти writes; reconciler converges.
6. Auth: missing/invalid token, UID spoof, Partner consent toggles/revoke, conversation ownership.
7. Compatibility: старый Swift decoder + новые optional fields/unknown enums/schema 1/3/6.
8. Widgets: partial staging, stale date, unsupported schema, long Russian strings, all families.

Ручной двухтелефонный прогон на неделю:

1. Телефон A учится, B отправляет тот же review event; проверить один state/event.
2. Отключить сеть перед 10 ответами, закрыть app, вернуть сеть; все ответы доставлены один раз.
3. В 23:55 создать pack в Almaty, в 00:05 открыть widgets; проверить stale/current UX.
4. Сменить timezone Almaty→London→Almaty; не должно появиться два pack одного learning day.
5. Revoke Partner на A при offline B; B не получает новые данные, локальный snapshot очищается/помечается stale.
6. Оставить app закрытым 3 дня; widgets/notifications честно показывают stale и recovery.
7. Установить старую сборку против нового backend fixture с дополнительным enum case.

## 9. Что не удалось и вопросы владельцу

Не запускались реальные Firebase/Firestore/Cloud Run/OpenAI и deployment inspection — по правилу read-only/no production. Firestore emulator config отсутствует, поэтому transaction/index/rules integration не выполнялась. `pip-audit`, radon, vulture, SwiftLint отсутствуют. Не измерялись device memory, widget refresh budget, VoiceOver/contrast, cold start и реальные Firestore reads. Git churn неинформативен из-за двух коммитов и untracked модулей. Ручная лингвистическая валидация 100 слов требует куратора; скрипт лишь фиксирует выборку.

Вопросы: какой Firebase project сейчас production и есть ли отдельный dev вне repo? Настроены ли managed Firestore backups/TTL вне кода? Должен ли pack означать «предложено» или «реально показано»? Weekly 40 заменяет evening 12 или добавляется к нему? Какой приемлемый максимум минут/долга? Нужна ли юридически account deletion до TestFlight? Есть ли Cloud Run deploy command/IaC вне репозитория?

## 10. Проверка гипотез владельца

1. **Долг растёт без предела — LIKELY, частично подтверждено.** Debt появляется на 4-й день и резко растёт после пропусков. Неограниченный рост за 180 дней не доказан: длинные интервалы частично стабилизируют очередь.
2. **Again недостижим, Hard не определён — подтверждено наполовину.** Again=30 минут вычисляется, но immutable session не показывает карточку повторно. Hard определён: минимум 12 часов, далее ×1,5.
3. **Нет локальной очереди — VERIFIED.** Дискового outbox и offline retry в iOS нет.
4. **Дата пака без timezone — опровергнуто.** Backend принимает IANA timezone, а iOS передаёт `TimeZone.current.identifier`.
5. **Возможна двойная генерация пака — опровергнуто для текущего контракта.** Document ID детерминирован, Firestore `create` возвращает победивший документ конкурентному запросу.
6. **Review event и state пишутся раздельно — опровергнуто.** Они записываются одной Firestore transaction. Аналогичный риск найден в exercise pipeline.
7. **Старая сборка ломается на новых полях — опровергнуто для optional keys, вероятно для enum.** Swift Codable игнорирует неизвестные ключи, но неизвестное raw-value enum ломает весь response.
8. **Нет dev/prod и backup — VERIFIED/LIKELY.** Debug и Release используют один URL; backup configuration в репозитории не найдена, фактическое состояние cloud проверить нельзя.
9. **Нет лимитов AI — VERIFIED.** Есть timeout, retry и output-token cap, но нет per-user/day quota и денежного ceiling.
10. **В корпусе есть плохие переводы и пустые поля — подтверждено частично.** Найдены 71 duplicate group и минимум три смешанных перевода; пустых переводов нет.

## 11. Воспроизводимые проверки

- Корпус: 11 196 записей; 6 389 words, 2 247 phrases, 2 395 collocations, 155 phrasal verbs, 10 upgrades.
- IPA: 8 678 записей, 77,5098%.
- Пустые переводы: 0; переводы с латиницей: 17; duplicate lemma+POS groups: 71.
- Curriculum: 5 stages, 197 уникальных nodes, 0 циклов, 0 dangling prerequisites.
- Grammar: 117 lessons, 234 examples, 117 common errors, 10 contrasts.
- Selector: одинаковый SHA-256 во всех 20 отдельных процессах.
- Backend: `ruff` passed; `mypy` passed для 118 файлов; `compileall` passed; `pytest` — тестов не найдено.
- iOS: Xcode 27.0, Debug Simulator build вместе с widgets — `BUILD SUCCEEDED` за 14,449 с.
- Dependency vulnerability audit не выполнялся: `pip-audit` не установлен.

Диагностические скрипты не нужны для чтения отчёта, но сохранены в `docs/audit/scripts/` для повторного запуска без доступа к production.
