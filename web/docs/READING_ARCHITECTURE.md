> Current release: D/E/F implementation supersedes the historical phase limits below. See [READING_RELEASE_VERIFICATION.md](READING_RELEASE_VERIFICATION.md) for current architecture, exact evidence and deployment gate.

# Reading architecture for subsequent phases

Phase C реализован поверх Phase A/B: routing/catalog/preparation, безопасный явный Start/Continue, exam renderer и базовый serial save. См. PHASE_C_VERIFICATION.md.

## Границы

`lib/api/client.ts` отвечает за HTTP, bearer token, cancellation и timeout; Firebase token provider не находится в компонентах. `features/reading/contracts.ts` хранит точные wire names, `api.ts` проверяет untrusted response. `catalog-view.tsx` получает только каталог, фильтрует доступность и строит ссылки. Он не импортирует dataset и не загружает passages при выборе книги. Main page не импортирует Reading/Firebase client. Private данные находятся только в памяти текущего компонента, не в Next server cache или статических файлах.

Phase B реализован: auth route shells заменены реальными формами; единый session store проверяет `/me` и восстанавливает provisioning при точном identity_not_allowed. Его размещение должно сохранять статическую главную и ленивую Firebase загрузку. Смена UID/выход должны немедленно убирать приватные данные, отменять запросы и очищать per-user in-memory cache. В Phase B header переключает Log in / Account; профиль и logout реализованы.

## Renderer — Phase C

После выбора backend-authorized exam: отдельный exam layout практически на весь viewport. Верхняя строка logo/title/timer, три passage tabs, две одновременно видимые колонки 50/50, нижняя question navigation. Native independent overflow для каждой колонки, desktop без переключателя текст/вопросы. Клавиатурно доступный separator меняет долю 40–60%. Только на узком mobile допустим passage/questions toggle.

Renderer принимает `ReadingExam → ReadingPassage → ReadingGroup → ReadingQuestion`; typed registry для 15 фактических group types. Общий контекст выводится один раз; `representation: source_image_with_inputs` использует authenticated assets и numbered inputs. Multiple-answer grading groups и constraints следуют server schema, не домыслу UI. Устойчивая identity по question ID, без remount полей при вводе. Никаких raw HTML strings.

## Attempts — Phase C и оставшаяся Phase D

Start — явное действие после повторной проверки availability и in-progress IDs, не page load. Resume — GET существующего UUID. Persist create `event_id` до отправки; неопределённый исход сети повторяет тот же UUID. При нескольких активных attempts не выбирать молча случайный.

Состояние на backend: answers, version, current_passage, annotations/crossed_options, timestamps. Browser-only view state отдельно и scoped по Firebase UID + attempt ID + content hash: left/right scroll каждого passage, focused question, review marks. Store adapter и outbox появятся в D; Phase C хранит только pending create event UUID в sessionStorage; ответы, review и scroll остаются в памяти. Существующие backend answers восстанавливаются из GET attempt.

Будущая Phase D: answer outbox сохраняется до отправки, очищается только после ack; UUID/expected_version сохраняются при retry. При 409 сначала server refresh и явное разрешение конфликтов, не blind last-write-wins. BroadcastChannel координация вкладок; local unsynced answers остаются при offline/401. Дедлайн считается от server_now/deadline_at, не сбрасывается refresh. Auth expired не удаляет pending answers.

## Результаты — Phase E

Submit после подтверждения и синхронизации outbox; идемпотентный event UUID. Результат только от backend. Поддержать submitted/expired/already finished и пагинацию истории. Не выдавать correct answers из клиентского bundle и не рассчитывать IELTS band самостоятельно.

## Контрактные пробелы и точные предложения

Для Phase A новых endpoints не требуется. Для согласованных следующих фаз существующих API достаточно для базового renderer/persistence. Ниже необязательное расширение, если будет нужна **межустройственная** синхронизация review marks (сейчас это только browser view state):

- В `PATCH /reading/attempts/{id}/state` добавить optional `review_question_ids: list[str]` (max 40), полная замена, только IDs из snapshot выбранной попытки.
- Сохранить `event_id`, `expected_version`, существующую идемпотентность/CAS и неизменные defaults для iOS. В GET attempt добавить поле в state, по умолчанию `[]`.
- Не хранить browser scroll offsets на backend: они зависят от viewport. Без расширения review marks допустимо хранить локально по UID/attempt/hash. Backend менять сейчас не требуется.

Дальнейшая спецификация должна также выбрать UX для нескольких active IDs: backend допускает несколько разных create events. Никакого самовольного изменения серверной модели в Phase A.

## Реализация Phase C

`features/reading/exam/parse.ts` проверяет public snapshot, уникальность question IDs, asset references и отсутствие private answer keys. `start.ts` повторно проверяет catalog; `start-button.tsx` защищает явное действие от повторного клика (Web Locks при доступности + общий promise lock). Только `POST /attempts` создаёт попытку; route mount/refresh/passage switch выполняют только загрузку/локальную навигацию. GET attempt передаёт все три passages сразу.

`AnswerSession` хранит draft отдельно от acknowledged answers. 600 ms debounce, одна запись `/sync` за раз, expected_version после ack, Retry того же event/payload при неопределённом исходе. 409 блокирует дальнейшее редактирование, не перезаписывает сервер. Расширенный конфликт-резолвер отсутствует. UID/generation change размонтирует private exam. ID token хранит только Firebase.

Deadline отображается от server_now/deadline_at и монотонного времени. При нуле ввод блокируется, но submit/check/result не вызываются. Это не окончательная Phase D реализация таймера. Local current passage/review/scroll не отправляются PATCH state. Серверный current_passage используется при первоначальном открытии.

Межустройственный simultaneous Start с разными UUID backend атомарно не запрещает. Web locks недоступны на обычном HTTP LAN; минимальная защита UI не заявляется как глобальная гарантия одной active attempt. Backend policy не менялась.

## Reading v1 D/E/F update

Web now uses native IndexedDB durable drafts/outbox, three-way CAS reconciliation, explicit durable conflicts, per-tab writer fencing, local highlights/preferences, server deadline reconciliation and confirmed submit/results/readonly review/history. All scoring stays on the existing backend. `CreateAttempt` adds optional `reuse_active=false`; web sends true. Under the existing learner advisory lock it returns a matching active attempt after enforcing expiry. Legacy fingerprints/behavior remain compatible. No migration or production deployment was performed. Updated backend must be deployed before this web version's new-test Start; old strict schema returns 422. See final verification for limitations and separated fixture/local integration/production acceptance evidence.
