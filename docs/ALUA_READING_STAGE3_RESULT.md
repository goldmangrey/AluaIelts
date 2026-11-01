# Alua Reading 1.0 — Stage 3

Дата: 2026-11-01, Asia/Almaty. Локальная SwiftUI реализация поверх Stage 2. Production deployment, SSH, Oracle, migrations на production, PDF/OCR, commit/push не выполнялись. Исходный Dataset, backend business logic, enrollment/Keychain implementation, Bundle ID, App Group, project signing values и Widgets не изменялись.

## A. Implementation

Новые файлы в `frontend/Alua/Features/Reading/`:

- `ReadingModels.swift` — Codable/Sendable wire models фактического Stage 2 API и canonical content. Все 15 question types и пять известных content-block kinds описаны явно; неизвестный обязательный enum не подменяется произвольным TextField.
- `ReadingAPI.swift` — существующий APIClient для JSON, авторизованная загрузка PNG, ISO 8601, hash/ETag validation.
- `ReadingPersistence.swift` — learner-scoped file store, durable events, preferences, positions, Unicode range conversion.
- `ReadingStore.swift` — единый @MainActor/@Observable источник состояния, start/resume, ответы/state, последовательная очередь, CAS, timer, submit/result.
- `PassageTextView.swift` — UIKit/TextKit persistent selection/highlights, общий passage renderer для Player/Review, native zoomable image.
- `ReadingQuestionViews.swift` — choice, text completion, typed content blocks, source-image controls, group checks.
- `ReadingViews.swift` — Library/Book/Mode, Player, Navigator, Settings, Results и Review.

Интеграция: DependencyContainer предоставляет ReadingAPI на текущем API client/token store. RootView владеет ReadingStore конкретного authenticated UID и деактивирует его при смене профиля. MainTabView передаёт его существующей PracticeView. Reading заменяет только Reading placeholder; Listening/Writing/Speaking сохраняются. В приложении по-прежнему **ровно три вкладки**. Player открывается через fullScreenCover и собственный NavigationStack, без нижнего TabBar. Существующие deep links не перепривязаны.

Библиотека получает актуальные books/exams через API, фильтрует только enabled_for_private_practice, сортирует книги по убыванию. Количество не зашито в UI. Cambridge 12 показывает исходные 5–8; Cambridge 10 с нулём доступных тестов не становится активной книгой. Есть новая попытка, незавершённая попытка и история с пагинацией. Общая тихая заметка о возможных ошибках переноса показана один раз.

Player показывает passage, серверный countdown и сегменты passages. В portrait используется нативный sheet с compact/medium/large detents, background interaction до medium и запретом случайного dismiss. Средний detent адаптирует сама iOS; в достаточно широком layout (>=650 pt) passage и вопросы расположены рядом. Отдельного gesture engine нет. Есть кнопки перехода, question grid, local bookmarks, подтверждение выхода/submit внутри существующей панели и keyboard Done. Подтверждение показывает число ответов/пропусков и действия завершения/возврата; отдельный вложенный alert не используется. Sheet имеет собственный NavigationStack для keyboard toolbar; идентификаторы отдельных кнопок и полей не перезаписываются идентификатором контейнера. Позиции passages/groups, выбранный вопрос, passage и detent сохраняются отдельно. Восстановление чтения выполняется по стабильному блоку текста, а не по точному пиксельному offset.

Для Boolean/Matching/MCQ используются только присланные options/allowed_values. Choose TWO использует единый selector группы, разные question IDs и атомарный batch; UI не позволяет дважды выбрать одну букву. Правильность на клиенте не вычисляется. Completion показывает оригинальный общий контекст один раз и отдельные numbered inputs. Typed tables имеют Grid и horizontal scroll; lists/rich text/blanks/images/heading поддержаны явно. `source_image_with_inputs` показывает оригинальное изображение и отдельные ответы без повторного вывода OCR-текста поверх изображения.

В текущих 63 экзаменах фактически используются rich_text, list и image blocks; обязательные таблицы/схемы с image fallback отображаются исходными PNG. Наличие `.table` renderer не выдаётся за наличие семантически восстановленных таблиц там, где Stage 1 их не создал.

## B. Backend integration

Клиент использует следующие Stage 2 Reading routes:

```text
GET  /api/v1/reading/books
GET  /api/v1/reading/exams/{exam_id}
POST /api/v1/reading/attempts
GET  /api/v1/reading/attempts?limit=100&offset=...
GET  /api/v1/reading/attempts/{attempt_id}
PUT  /api/v1/reading/attempts/{attempt_id}/answers/{question_id}
POST /api/v1/reading/attempts/{attempt_id}/sync
PATCH /api/v1/reading/attempts/{attempt_id}/state
POST /api/v1/reading/attempts/{attempt_id}/check
POST /api/v1/reading/attempts/{attempt_id}/submit
GET  /api/v1/reading/attempts/{attempt_id}/result
GET  /api/v1/reading/assets/{asset_id}
```

Отдельный GET `/reading/exams` не нужен текущему UI: `/books` уже возвращает те же catalog entries внутри книг. DTO декодируют реальный публичный exam projection и attempt/result fields; служебные SHA используются для привязки и cache validation, пользователю не показываются.

Все JSON requests идут через существующий APIClient с requiresAuthentication=true. Asset requests получают актуальный token из того же DeviceTokenStore, отправляют bearer только в Authorization и повторно сверяют token после await. URL изображения строится из asset ID текущего API origin; произвольный URL/path из контента не открывается. Поддерживаются 200 PNG и 304 при наличии проверенных cached bytes; SHA-256 должен совпасть. Tokens не записываются в Reading files и не добавляются в URL.

Контент и необходимые images скачиваются перед POST создания попытки, поэтому серверные 60 минут не тратятся на первичное скачивание схем. При ошибке обязательного изображения fake attempt не создаётся. После успешного начала данные остаются доступны локально. Создание требует сервера в обоих режимах; pending start имеет постоянный UUID и переживает потерянный HTTP acknowledgement.

Private answer keys не входят в iOS resources. correct/accepted answers появляются только из server result или selective Practice check; незавершённый Full Exam их не получает. Баллы, Band, per-passage/type counts берутся исключительно с backend.

## C. Persistence, synchronization, timer

Application Support `Reading-v1/<SHA256(learner UID)>/attempts.json` хранит снимки попыток, публичный exam, исходные пользовательские ответы, annotations, очередь, terminal unaccepted events, UI positions и preferences. PNG кэшируются по content SHA в том же learner directory. Запись атомарная, с file protection UntilFirstUserAuthentication. Widget/App Group storage не используется.

Каждое изменение сначала записывается на диск вместе с постоянным event UUID и **исходной expected_version**. Версии следующих событий образуют последовательную цепочку. GET после reconnect не меняет expected_version старых событий. Это существенно: иначе старый offline ответ мог бы незаметно перезаписать новое изменение другого устройства.

Только один отправитель работает с очередью попытки. Retry повторяет тот же UUID и payload. После ack событие удаляется атомарно с обновлением server state. Устаревшее acknowledgement не понижает server version и не заменяет более свежий локальный ввод. Pending события накладываются поверх подтверждённого snapshot. Async ответы после смены learner игнорируются по generation/token, ответы другой попытки адресуются её record.

CAS/event conflict останавливает очередь, загружает свежий server attempt и сохраняет локальный ввод. UI предлагает явно выбрать серверные или локальные ответы. Выбор локальных создаёт новые UUID для осознанной новой batch/state; старые события сохраняются в unaccepted, их UUID не переиспользуются с другим payload. Автоматического бесконечного rebasing нет.

При logout текущий ReadingStore деактивируется, UI/active UID очищаются, подтверждённые caches можно удалить. **Неотправленные и отклонённые изменения остаются в приватной UID-scoped папке**, чтобы выход из профиля не уничтожил ответы. Они не читаются другим learner; повторная авторизация того же UUID позволяет восстановить попытку. Непрочитанный повреждённый attempts.json переносится в unreadable-UUID.json, а не молча затирается. Ошибка записи не объявляется успешным локальным сохранением и блокирует отправку до retry.

Full Exam display использует последнее server remaining_seconds и elapsed ContinuousClock, а не изменяемые часы устройства. Foreground/reconnect запрашивает актуальный attempt. После холодного offline restart, когда серверное время пока нельзя подтвердить, существующий текст/ответы доступны для чтения, Full Exam input заморожен до refresh; новый 60-минутный таймер не запускается.

При нуле UI прекращает редактирование и запрашивает сервер. Deadline rejection (`mutation_applied:false`) не считается принятым ответом. Поздние изменения сохраняются локально в unaccepted; Results отдельно показывает значения, отличающиеся от ответов, вошедших в server result. Client timestamps не используются для обхода дедлайна.

Submit добавляется после pending edits, защищён от двойного нажатия и переживает retry. Results не открывается до подтверждённого backend result. При недоступном сервере локальная очередь остаётся видимой, оценка не выдумывается. Practice check замораживает server checked_question_ids, linked groups раскрываются/блокируются вместе; остальные ответы не раскрываются. Последовательные проверки накапливаются по question_id: новый check не стирает ранее подтверждённую обратную связь.

## D. Visual / UX

SF/system fonts для UI; UIFont serif с UIFontMetrics и line spacing для passages. Light/Sepia/Dark и размер 16–30 сохраняются для learner, не меняя глобальную тему приложения. Dynamic Type и системная selection/VoiceOver остаются доступны.

Текстовый компонент использует UITextView/TextKit, isEditable=false, selection=true. Системное edit menu даёт жёлтый/зелёный/синий маркер и удаление. Exact quote и Unicode scalar offsets [start,end) преобразуются в UTF-16 только после проверки границ. Составные emoji, surrogate pairs и combining characters не приравниваются к Swift Character offsets. Для несовпадающего content_hash highlight не рисуется. Font/theme changes не меняют смысловую привязку.

Crossed options сохраняются через PATCH state, отдельно от answers. Bookmarks и scroll anchors локальные и не выдаются за синхронизацию между устройствами. Схемы открываются в UIScrollView с pinch zoom 1–6 и VoiceOver actions увеличения/уменьшения; пропорции исходного PNG сохраняются.

Results показывает raw score, backend estimated_band с названием **Estimated IELTS Academic Reading Band**, время, пропуски и реальные breakdown. Для Practice Band отсутствует. Для Full score ниже опубликованной шкалы null не заменяется на 0.0. Самый слабый фактический type ведёт к фильтрованному Review. Недостоверное per-passage time не показывается как точный факт.

Review имеет фильтры ошибок/всех, passages и types, исходный user answer, correct answer, пропуски, исходное задание/options/images и переход к общему passage renderer с annotations. Evidence отсутствует в текущих keys и остаётся null; цитаты/объяснения не генерируются. Если backend присылает quote, отображается именно она и passage можно открыть на содержащем её блоке.

## E. Verification

Постоянные проверки:

- `frontend/AluaTests/ReadingTests.swift`: real Dataset decode/renderer compatibility, durable offline/replay/CAS, Unicode/highlights, corrupted-file preservation, Full/Practice HTTP integration и representative small-width layout.
- `frontend/AluaUITests/ReadingUITests.swift`: настоящий пользовательский путь Library → Practice → answer → submit → Results → Review → Passage.
- `frontend/scripts/check_reading.py`: собственный временный PostgreSQL 17 cluster, Alembic head, локальный Uvicorn, одноразовые test enrollments и **новый отдельный** simulator. Production URL/DB и существующие simulator enrollments не используются. Tokens находятся только во временном файле с permissions 0600, удаляемом finally; в iOS bundle не копируются.

Команды из корня:

```sh
xcodegen generate --spec frontend/project.yml
backend/.venv/bin/python frontend/scripts/check_reading.py
# Быстрая целевая повторная проверка:
backend/.venv/bin/python frontend/scripts/check_reading.py --reading-only
```

XcodeGen не хранит локальные DEVELOPMENT_TEAM значения в project.yml: при выполненной генерации прежние значения восстановлены без изменения identities/entitlements. Повторная генерация пользователем также должна сохранять его локальные signing settings.

Реальный build:

```sh
xcodebuild -project frontend/Alua.xcodeproj -scheme Alua \
  -configuration Debug -sdk iphonesimulator \
  -destination 'id=A072A37D-13A0-400C-9D1D-AE6F6C6A5E6B' \
  -derivedDataPath /tmp/alua-reading-stage3-build CODE_SIGNING_ALLOWED=NO build
```

Build прошёл. Для тестов с реальным Keychain runner использует **только simulator CLI overrides** `CODE_SIGNING_ALLOWED=YES CODE_SIGN_IDENTITY=-`, не меняя signing configuration проекта. Первый unsigned запуск auth-тестов получил Keychain -34018; при simulator ad-hoc подписи оба существующих auth-теста прошли.

Проверены **63 реальных exam JSON, 189 passages, 2 520 positions, все 15 question types и 49 PNG references этих экзаменов**. Весь Dataset по-прежнему содержит 72 экзамена/60 PNG; недоступные девять не подменяются рабочими.

Read-only Dataset validator дополнительно подтвердил: **144 Schema documents, 72 exams, 216 passages, 2 880 questions/keys, 60 PNG, errors=[]; хеши всех 36 исходных TXT/PDF совпадают**. Использовалась команда `/tmp/alua-reading-env/bin/python backend/scripts/reading_dataset/validator.py`; повторная генерация/OCR не запускались. `backend/.venv/bin/ruff check frontend/scripts/check_reading.py` и `git diff --check` прошли.

Полный unit/integration запуск: **21 tests, 0 failures**, включая 10 Reading и 11 существующих Auth/Study/Presentation/Widget tests. После финальных UI-правок выполнен `backend/.venv/bin/python frontend/scripts/check_reading.py --reading-only`: **10 Reading tests + 1 UI test, 0 failures**. Сборка приложения и тестовых targets прошла, Swift concurrency/compiler errors не обнаружены.

UI прошёл настоящий путь: enrollment → Practice → Reading → Cambridge 18 → Test 1 → Passage Practice → раскрытие нативной панели → ввод `lettuces` → keyboard Done → подтверждение submit в панели → серверный результат **1/13** → прокрутка к Review → фильтр «Все» → сохранённый ответ → исходный passage **Urban farming**. Навигационные нажатия и фокусировка имеют одну ограниченную повторную попытку при потере события в симуляторе; start/check/answer/submit так не повторяются.

Дополнительно тот же Swift core выполнен нативным локальным harness: real HTTP Full/Practice, сохранение первого/40-го ответа, submit, resume, asset 304, selective check и grading; PASS. Временный harness source/binary удалён. Постоянные тесты остаются для воспроизводимости.

Логи финальной проверки: `/tmp/alua-reading-stage3-tests.log`, `/tmp/alua-reading-stage3-ui-tests.log`. XCTest results: `/tmp/alua-reading-stage3-build/Logs/Test/Test-Alua-2026.11.01_04-42-36-+0500.xcresult` и `/tmp/alua-reading-stage3-build/Logs/Test/Test-AluaQA-2026.11.01_04-43-49-+0500.xcresult`.

Известная диагностическая особенность: iOS 26.1 simulator при открытии клавиатуры выводит `Invalid frame dimension (negative or non-finite)`. Функциональный UI-прогон завершается без ошибок, но считать визуальную проверку на устройстве выполненной нельзя. TextKit measurement отклоняет нечисловые/бесконечные размеры. Переходы sheet/keyboard и layout нужно проверить на физических iPhone. AppIntents metadata warning связан с отсутствием AppIntents.framework и не является ошибкой сборки.

## F. Physical iPhone QA checklist

Физический device QA **не выполнялся**. После отдельного согласованного backend release проверить на обоих iPhone:

- Текущий enrollment сохраняется; Library принадлежит правильному learner, Cambridge 12 имеет Test 5–8, недоступные экзамены не запускаются.
- Full Exam: ввод 1/40, смена passages, Question Navigator/flags, compact/medium/large panel, чтение под compact/medium, клавиатура/Done и безопасный выход.
- Авиарежим: локальные ответы/notes сохраняются, app force quit/restart не стирает очередь; после сети данные отправляются; конфликт двух устройств требует явного выбора.
- Lock screen/background и изменение системных часов не дают новые 60 минут. Ответы после deadline видны как локальные, не вошедшие в результат.
- Practice: check question/group, заморозка уже проверенных positions, остальные keys не раскрываются, результат без Band.
- Cambridge 08 Test 1 Q9–13: исходная clock diagram доступна offline, pinch/VoiceOver zoom и numbered inputs читаемы.
- Выделить emoji/combining text, поменять serif size/theme, закрыть/открыть, удалить highlight; проверить VoiceOver и максимальный Dynamic Type.
- Выход/повторный вход и смена learner не раскрывают чужие local records; неотправленные данные того же UUID можно восстановить после повторной авторизации.
- Results/Review: реальный backend Band/null, ошибки/пропуски, type filters, исходный passage и annotations; история не заменяется новой попыткой.
- Регрессия: Сегодня, Моя книга/SRS, три вкладки Practice, существующие deep links и Widgets.

## G. Deployment readiness

Локально реализованы Reading UI и клиент Stage 2; это **не утверждение**, что production Reading API уже развёрнут или физические iPhone проверены. До rollout отдельно нужны:

1. Backup PostgreSQL и проверка текущей revision `20261031_0004`.
2. Аддитивный upgrade `20261101_0005` для Reading attempts/mutations на целевой базе после отдельного разрешения. Не применять к другим сервисам/базам.
3. Backend release с `app/modules/reading`, `app/content/reading_v1` (manifest, schema, 72 public exams, **приватные** answer_keys, assets, audit), runtime jsonschema/lockfile и единственным `scripts/reading_dataset/grading.py` (Stage 2 Dockerfile уже копирует его).
4. Asset API должен требовать bearer, answer_keys directory нельзя публиковать static. Сохранить старые versions/assets при последующих обновлениях; текущие попытки привязаны к content hash/version.
5. Проверить health, bootstrap 404, действующий enrollment двух learners, catalog 63/9 по текущей policy, начало/сохранение/submit/result, learner isolation и authenticated PNG через реальные release endpoints.
6. Собрать iOS с обычным существующим API_BASE_URL, а не ephemeral loopback URL тестового runner. Bundle ID/App Group/signing не менять.
7. Выполнить physical QA checklist и подтвердить серверный deadline/offline behavior перед повседневным использованием.

Production deployment этим этапом не выполняется.
