# Alua Reading 1.0 — Stage 2 result

Дата: 2026-11-01. Реализован локальный FastAPI/PostgreSQL backend для двух существующих learners. Production, SSH, Oracle, SwiftUI, enrollment, публичный bootstrap и существующие учебные таблицы не изменялись. Commit/push не выполнялись.

## Изменения

- `backend/app/modules/reading/catalog.py`: загрузка manifest, проверка JSON Schema, SHA-256, связей вопросов/ключей, обязательных options/images, отдельных content gates; кэш процесса и приватный допуск.
- `models.py`, `repository.py`: две Reading-owned таблицы, транзакции и learner scope, PostgreSQL locks.
- `schemas.py`, `service.py`, `router.py`: запросы, библиотека, экзамены, попытки, синхронизация, annotations, проверки и результаты.
- `grading.py`: runtime adapter к **единственному** scorer из `scripts/reading_dataset/grading.py`, ограничения ввода, статистика и версионированная Band table. Dataset Engine и его scorer не переписывались.
- `backend/app/api.py`: подключён Reading router к существующему `/api/v1`.
- `backend/alembic/env.py`: зарегистрирована metadata новых моделей.
- `backend/alembic/versions/20261101_0005_reading.py`: аддитивная revision после `20261031_0004`, только `reading_attempts` и `reading_mutations`. Downgrade сохраняет историю, как revision 0004.
- `backend/pyproject.toml`, `uv.lock`: runtime dependency `jsonschema`.
- `backend/Dockerfile`: добавлено копирование существующего единственного scorer в image. Image не собирался и не публиковался.
- `backend/tests/test_reading.py`: реальные PostgreSQL integration tests и проверки grading/catalog. В существующем auth-тесте обновлено ожидаемое число защищённых операций с 55 до 68.
- Этот отчёт и `docs/ALUA_READING_STAGE2_CATALOG.json`.

Канонические 72 экзамена, ключи, assets и исходные TXT/PDF Stage 1 сохранены без изменений. Повторного OCR, извлечения PDF или генерации dataset не было.

## Допуск к личной практике

Dataset version `1.0.0`, content revision `10e606c1f3bf1b871bceab9a722d7e1244c9e0f9898763c12541289129d06d39`.

**Доступны 63 полных экзамена, исключены 9.** Все доступные сохраняют `content_status: needs_review`, `not_fully_proofread: true`, `enabled_for_private_practice: true`. Статусов `ready` по-прежнему 0. Private policy `private-practice-v1` заменяет строгий release gate Stage 1 исключительно для закрытой практики по новому заданию пользователя; клиент не может включить запрещённый экзамен или передать QA bypass.

Точный список IDs, исключений и исходных предупреждений: [ALUA_READING_STAGE2_CATALOG.json](ALUA_READING_STAGE2_CATALOG.json). Эта документация — снимок текущего допуска; runtime вычисляет его заново по каноническим файлам.

| Cambridge book | Доступные исходные Test numbers |
|---|---|
| 04, 05 | 1, 2, 3, 4 |
| 06 | 1, 3, 4 |
| 07 | 3, 4 |
| 08, 09 | 1, 2, 3, 4 |
| 10 | нет |
| 11 | 1, 2, 3, 4 |
| 12 | **5, 6, 7, 8**; test_ordinal остаётся 1–4 |
| 13 | 1, 2, 3, 4 |
| 14 | 1, 3, 4 |
| 15, 16, 17, 18, 19 | 1, 2, 3, 4 |
| 20 | 1, 2, 4 |
| 21 | 1, 2, 3, 4 |

| Исключённый exam_id | Причина |
|---|---|
| cambridge-06-test-02 | Stage 1 blocked: не восстановлена метка абзаца A, Passage 1. |
| cambridge-07-test-01 | Questions 10–13 содержат предупреждение о восстановленном тексте под overlay/watermark; изображения для достоверного задания нет. |
| cambridge-07-test-02 | Stage 1 blocked: текст под watermark, неоднозначные Questions 11–13. |
| cambridge-10-test-01 | Stage 1 blocked: Passage 2, метки H/I; дополнительное предупреждение о binding Stepwells. |
| cambridge-10-test-02 | Stage 1 blocked: Passage 1 C/G, Passage 2 A–F. |
| cambridge-10-test-03 | Stage 1 blocked: Passage 1 A–C, Passage 2 E–I. |
| cambridge-10-test-04 | Stage 1 blocked: Passage 2 E–H. |
| cambridge-14-test-02 | Дополнительный runtime gate: Matching Information Q14–18 без options/allowed values/assets; инструкция требует девять секций, в структурированном тексте есть только A–D. |
| cambridge-20-test-03 | Stage 1 blocked: исходная неоднозначность labels A–F в Q22–23 при инструкции A–E. |

Общая нехватка полной PDF-вычитки, некритические OCR-подозрения, редакционные заголовки и unverified keys не превращаются в `ready`. Они передаются как warnings. Существующие `source_image_with_inputs` допускаются, если исходное изображение присутствует и прошло техническую проверку; фронтенд обязан показать изображение вместе с отдельными numbered inputs. Новая неисправность одного JSON исключает этот экзамен, сохраняя остальную библиотеку.

## HTTP contract

Все 13 операций требуют существующий device bearer token. `learner_id` берётся только из `AuthenticatedUser.uid`; входные модели запрещают лишние поля. Reading JSON имеет `Cache-Control: no-store`. Ошибки используют существующий `{error: {code, message}}`, ошибки Pydantic — стандартный FastAPI 422.

| Method /api/v1/reading/... | Запрос | Ответ |
|---|---|---|
| GET books | — | `{items: [{book_number, exams: [catalog_entry]}], dataset_version}` |
| GET exams | optional `book=4..21` | `{items: [catalog_entry], dataset_version, practice_policy_version}` |
| GET exams/{exam_id} | — | Публичный экзамен с metadata, всеми тремя passages и 40 вопросами. Исключённый экзамен: 404. |
| POST attempts | `{event_id, exam_id, mode, selected_passage?}` | 201, attempt snapshot; Full Exam запрещает selected_passage, Practice требует 1–3. |
| GET attempts | `limit=1..100`, `offset>=0` | `{items: [attempt_summary], limit, offset}`; только свои попытки. |
| GET attempts/{attempt_id} | — | attempt с публичным **историческим** exam snapshot; в Practice только выбранный passage; также проверенные practice results, если есть. |
| PUT attempts/{attempt_id}/answers/{question_id} | `{event_id, expected_version, answer}` | attempt acknowledgement, новая version. |
| POST attempts/{attempt_id}/sync | `{event_id, expected_version, answers: {question_id: string}}` | Атомарная пачка до 40 позиций, один шаг version. |
| PATCH attempts/{attempt_id}/state | `{event_id, expected_version, current_passage, annotations?, crossed_options?}` | Обновлённая state; списки заменяются целиком. |
| POST attempts/{attempt_id}/check | `{event_id, expected_version, question_ids}` | Только Practice: attempt + `checked_result` исключительно проверенных позиций; связанные пары раскрываются/замораживаются вместе. |
| POST attempts/{attempt_id}/submit | `{event_id, expected_version}` | attempt + полный сохранённый result выбранного режима. Повторный submit завершённой попытки возвращает тот же result. |
| GET attempts/{attempt_id}/result | — | Сохранённый result; до submit/expiry 409. |
| GET assets/{asset_id} | optional If-None-Match | PNG или 304, private cache, SHA-256 ETag, размеры в X-Image-Width/Height, MIME image/png. |

`catalog_entry`: exam_id, source_book, source_test_number, test_ordinal, dataset_version, content_revision, content_hash, content_status, enabled_for_private_practice, not_fully_proofread, question_count, passage_count, exclusion_reasons, warnings, practice_policy_version; персонально — completed_attempts, in_progress_attempt_ids и best_estimated_band (только Full Exam; null при отсутствии результата).

`attempt`: id, exam_id, dataset_version, content_hash, content_revision, mode (`full_exam`/`passage_practice`), selected_passage, status (`in_progress`/`submitted`/`expired`), version, started_at, deadline_at, submitted_at, server_now, remaining_seconds, elapsed_seconds, answers, state, content_status, not_fully_proofread, timing_status. Даты ISO 8601 UTC. Mutation acknowledgement добавляет mutation_applied. GET attempt дополнительно содержит exam и, для Practice, checked_result по уже замороженным позициям.

Ни публичный экзамен, ни незавершённая Full Exam попытка не содержат accepted/canonical answers, приватных ключей или filesystem paths. До окончания Practice раскрывает только явно проверенные позиции. Запрос чужого UUID всегда 404. Все Reading endpoints наследуют bearer authentication; POST `/api/v1/bootstrap` остался 404. Произвольный filesystem path для assets не принимается, директория content не монтируется как static.

### Компактные JSON-примеры

Сокращённый фрагмент настоящего публичного экзамена Cambridge 18 Test 1. Полный GET содержит все три passages и 40 вопросов; поля, опущенные здесь для краткости, определяются Stage 1 schema и описанной проекцией API.

```json
{"id":"cambridge-18-test-01","dataset_version":"1.0.0","content_status":"needs_review","question_count":40,"metadata":{"enabled_for_private_practice":true,"not_fully_proofread":true},"passages":[{"id":"cambridge-18-test-01-p-1","number":1,"title":"Urban farming","content":[{"type":"heading","text":"Urban farming","label":null}],"question_groups":[{"type":"sentence_completion","instructions":"Questions 1–3. Complete the sentences. Choose NO MORE THAN TWO WORDS AND/OR A NUMBER from the passage for each answer.","questions":[{"id":"cambridge-18-test-01-q-01","number":1,"prompt":"Vertical tubes are used to grow strawberries, __________ and herbs.","answer_input_type":"text","options":[]}]}]}]}
```

Сохранение ответа: `PUT /api/v1/reading/attempts/{attempt_id}/answers/cambridge-18-test-01-q-01`.

```json
{"event_id":"25f50c19-b072-4cff-8ced-d947f76c250d","expected_version":0,"answer":"lettuces"}
```

Сокращённый **иллюстративный**, а не реальный learner result после Full Exam; endpoint также возвращает остальные positions, breakdown и version fields.

```json
{"exam_id":"cambridge-18-test-01","raw_score":23,"total_questions":40,"estimated_band":6.0,"band_is_estimate":true,"band_label":"Estimated IELTS Academic Reading Band","band_table_version":"academic-indicative-2026-11-01-v1","elapsed_seconds":3420,"correct_count":23,"incorrect_count":10,"unanswered_count":7,"timing_status":"server_deadline_enforced","positions":[{"question_id":"cambridge-18-test-01-q-01","number":1,"question_type":"sentence_completion","passage_number":1,"user_answer":"lettuces","correct_answer":"lettuces","accepted_answers":["lettuces"],"is_correct":true,"unanswered":false,"evidence":null}]}
```

## Persistence, concurrency и offline queue

`reading_attempts` хранит learner FK, UUID попытки, точную dataset/version/revision/hash, режим и passage, timestamps, status/version, JSONB answers/state/result и закрытый immutable снимок exam/key/metadata. После завершения result сохраняется и не пересчитывается из нового каталога. Исторический GET использует снимок, поэтому изменение текста/ключей каталога не перепривязывает старую попытку. Ключи не копируются в публичные DTO. PostgreSQL backups должны считаться приватными данными.

`reading_mutations` имеет PK `(learner_id, event_id)`, attempt FK, SHA-256 всего mutation payload/operation/attempt и сохранённый acknowledgement. PostgreSQL transaction/advisory lock по learner и scoped row lock сериализуют чтение/изменения. Для двух пользователей это намеренно простой вариант. Он защищает также одинаковый UUID в двух одновременных созданиях попыток. Изменение answer/state/result и запись события коммитятся одной транзакцией.

Правила для SwiftUI outbox:

1. Сохранять локально attempt_id, dataset_version, content_hash, server version и событие UUID **до** отправки. Клиент не задаёт learner_id или deadline.
2. Отправлять события одной очередью на attempt. `expected_version` — последнее подтверждённое состояние, на котором основано действие. UUID и payload при сетевом retry сохранять точно.
3. Retry того же UUID/payload возвращает исходный acknowledgement без повторной записи. Один UUID с другим содержимым, attempt или operation возвращает 409 `reading_event_conflict`.
4. Устаревшая expected_version возвращает 409 `reading_version_conflict`, ничего не меняя. Получить свежую попытку. Не переписывать автоматически старому событию version на текущую: это может затереть новое действие с другого устройства. Разрешать конфликт осознанно, отправляя новое событие UUID только для действительно актуального локального состояния.
5. Для новой offline пачки можно объединить последние локальные ответы по question_id в `/sync`, указать согласованную expected_version и новый UUID. Пачка применяется атомарно либо не применяется вовсе. State и annotations используют тот же счётчик version.
6. Сохранённый acknowledgement при retry может отражать более раннее состояние. После восстановления соединения GET attempt является актуальным источником status/version/time; не откатывать локальную version из старого acknowledgement.
7. После submit/expiry удалять неприменимые события из очереди, сохранять результат. Submit завершённой попытки идемпотентен; остальные изменения submitted attempt получают 409. Изменения expired attempt получают 200 с `mutation_applied:false`, `rejection_reason:deadline_passed`, терминальным статусом и прежними ответами.

Full Exam deadline = started_at + ровно 3600 секунд, рассчитывается сервером. На каждом обращении попытка проверяется после получения PostgreSQL lock. При `server_now >= deadline_at` сохранённые ответы финализируются, status становится expired, submitted_at — deadline, elapsed_seconds — 3600. Нет фонового worker: физическая финализация происходит при первом обращении к attempt/list/library/result после deadline, логический момент завершения остаётся тем же.

Поздние offline ответы **не принимаются**, даже если устройство заявляет более раннее время. Это позволяет честно вернуть `server_deadline_enforced` для сохранённых до deadline ответов. Клиентских timestamps и продления таймера нет. GET возвращает server_now/remaining_seconds; закрытие приложения не останавливает таймер. Practice не имеет deadline и не получает IELTS Band.

Annotations привязаны к content_hash, passage_id, block_index и полуоткрытому `[start,end)` диапазону **Unicode codepoints** в `passage.content[block_index].text`. Quote должен совпадать точно; Swift должен преобразовать String/UTF-16 offsets в codepoints перед отправкой. Поля: id(UUID), passage_id, content_hash, block_index, start, end, quote, color(yellow/green/blue/pink), optional note. Crossed options: `{question_id, option_label}`; сервер проверяет scope и наличие label в доступных options/allowed_values. Изменение версии не переносит highlight на другой текст.

## Grading и результаты

Единственная Cambridge matching/normalization logic импортируется из `scripts.reading_dataset.grading`. Никакого LLM grading, нечёткого сравнения или придуманных synonyms. Поддержаны все 15 типов Dataset: их различия сохраняются в questions и статистике. Строковые ответы приходят отдельно по каждому question_id; multi-select клиент раскладывает по номерным позициям группы.

Нормализация использует исключительно перечисленные в key rules: Unicode NFKC, casefold, trim, whitespace, апострофы и разделители тысяч. UK/US, optional words и альтернативы берутся из official accepted_answers. Пустой ответ — 0. Unordered группы проверяются максимальным сопоставлением: одна выбранная буква/один смысловой вариант не может дать два балла. `unordered_parts` требует все части одного ответа. Runtime контролирует max_words/number allowance; hyphenated token считается одним словом. Явная официальная accepted alternative имеет приоритет при конфликте печатной инструкции и ключа (Cambridge 14 T4 Q1: ONE WORD ONLY, но official key допускает `four / 4`). Разрешения произвольных числовых/пунктуационных замен нет.

Результат содержит raw_score, total_questions, accuracy, correct/incorrect/unanswered counts, elapsed_seconds, completion_reason, timing_status, grading_version, dataset identity, per_passage и per_question_type. `incorrect_count` не включает unanswered; три счётчика суммируются в total. Weakest types сортируются по фактической accuracy, объяснения не генерируются. Каждая position содержит question_id/number/type/passage, исходный user_answer, canonical/accepted answers, grading_group, is_correct, unanswered и evidence (сейчас null).

Practice `/check` замораживает проверенные answers; linked either-order группа проверяется целиком, чтобы её ключ не помогал изменить другие позиции той же пары. Остальные незавершённые задания не раскрываются. GET attempt восстанавливает checked_result после перезапуска.

State heartbeat даёт только приблизительное время активности по passages: сервер учитывает не более 30 секунд между обращениями при PATCH state и приписывает интервал предыдущему current_passage. В result это `reported_active_seconds` и `time_is_verified:false`. Закрытое приложение, чтение без heartbeat и активность между другими mutations достоверно распределить по passages нельзя; эти интервалы не выдаются за фактическое подтверждённое время. Полное elapsed_seconds измеряется сервером.

### Estimated IELTS Academic Reading Band

Версия `academic-indicative-2026-11-01-v1`. Источник диапазонов — опубликованный [ESLBAR IELTS Score Conversion Chart, ©2016](https://eslbar.co.uk/wp-content/uploads/2019/10/Ielts-score-conversions-chart.pdf); проверен 2026-11-01. Основные Academic Reading границы сверены с [British Council](https://takeielts.britishcouncil.org/results/how-is-ielts-assessed). Это ориентировочная таблица практики: реальная IELTS conversion зависит от test version.

| Raw score | Estimated Band |
|---|---|
| 0–3 | null: below_published_range; источник не публикует диапазон |
| 4–5 | 2.5 |
| 6–7 | 3.0 |
| 8–9 | 3.5 |
| 10–12 | 4.0 |
| 13–14 | 4.5 |
| 15–18 | 5.0 |
| 19–22 | 5.5 |
| 23–26 | 6.0 |
| 27–29 | 6.5 |
| 30–32 | 7.0 |
| 33–34 | 7.5 |
| 35–36 | 8.0 |
| 37–38 | 8.5 |
| 39–40 | 9.0 |

Нет произвольной интерполяции нижних диапазонов. Для Practice estimated_band всегда null. Для Full Exam `band_is_estimate:true`, название **Estimated IELTS Academic Reading Band**, версия таблицы сохраняется в result. Это не официальный сертифицированный IELTS score.

## Проверки

Команды из корня репозитория:

```sh
backend/.venv/bin/ruff check backend/app backend/alembic backend/tests
cd backend
PYTHONPATH=. .venv/bin/pytest -q --tb=short
```

Fixture `postgres_url` запускает отдельный PostgreSQL 17 cluster через initdb/pg_ctl во временном `/tmp/alua-pg-*`, без TCP listener, по private Unix socket. Fixture подставляет DATABASE_URL, применяет Alembic head и затем останавливает cluster. Настроенная пользовательская/production база не используется. Отдельный тест моделирует базу revision 0004 без Reading tables и применяет upgrade до `20261101_0005`.

Проверены manifest/schema/hash, изоляция повреждённого JSON, 63 допустимых экзамена, все 15 типов, official alternatives, unordered pairs/duplicates/compound answers, Full/Practice lifecycle, два настоящих device enrollments, learner isolation, отсутствие ключей до submit, annotations, selective check/group freeze, batch sync, retry/mismatched UUID, CAS и concurrent requests, перезапуск app/DB pool, snapshots при изменении каталога, expiry/late rejection, повторный submit, 23→6 / 30→7 / 35→8 через настоящий API, breakdown и пустые ответы, assets/ETag/path traversal, bootstrap 404 и все legacy API/auth tests.

Дополнительно без регенерации запущен Stage 1 validator: все 144 JSON, 60 assets, 36 source hashes; dataset сохранён. `uv lock --check --offline --directory backend` проверяет согласованность зависимостей.

**Итог последнего полного запуска: 23 passed за 49.90 s**, включая 9 Reading tests и 14 существующих backend tests. Ruff: All checks passed. Lockfile: согласован, 58 packages. Stage 1 validator: artifact_validation_passed=true, errors=[], 144 schema documents, 60 PNG, 36 source hashes. Остались прежние предупреждения Alembic о path_separator и Pydantic о поле register; ошибок тестов нет.

## Ограничения и Stage 3

- 63 экзамена разрешены для закрытой практики, а не объявлены source-verified. Девять исключённых недоступны для создания и выдачи полного теста.
- Существующие изображения местами заменяют typed layout/options; SwiftUI обязан учитывать representation и не дублировать поверх изображения rich text того же задания.
- Нижний Band 0–3 не выдумывается; UI показывает score и отсутствие опубликованной оценки. Для Practice UI показывает score/accuracy без Band.
- Проверка content кэшируется при первом Reading request в процессе; после намеренного обновления immutable dataset требуется перезапуск процесса. Старые версии и asset files следует сохранять при будущих обновлениях, чтобы исторические image URLs оставались доступны; тексты/ключи и уже рассчитанные результаты хранятся в PostgreSQL snapshots.
- Примерное время по passages зависит от heartbeat и явно непроверенное. Нет LLM explanations/evidence generation.
- Перед будущим deployment отдельно подготовить backup и применить additive migration; на этом этапе production migration/deployment не выполнялись.

Stage 3: реализовать SwiftUI библиотеку, оба режима Exam Player, rendering Stage 1 blocks и authenticated assets, серверный таймер, общую outbox с UUID/CAS, Unicode-correct annotations и crossed options, Practice check/group freeze и result screens. Использовать текущий bearer enrollment без изменений. Не включать answer_keys в iOS bundle. OpenAPI `/openapi.json` содержит request schemas; этот документ и Stage 1 schema описывают structured content и runtime response fields.
