> Current release: D/E/F implementation supersedes the historical phase limits below. See [READING_RELEASE_VERIFICATION.md](READING_RELEASE_VERIFICATION.md) for current architecture, exact evidence and deployment gate.

# Existing backend audit — 2026-11-01

Исследованы локальные исходники; это не аудит текущего Oracle deployment. SSH, production API calls, deployment, чтение секретных env и изменение backend не выполнялись.

## Источники

- `backend/app/api.py`, `app/main.py`, `core/config.py`, `core/middleware.py`.
- `core/auth.py`, `core/firebase_auth.py`, `modules/registration/router.py`, `modules/users/router.py`.
- `modules/reading/{router,schemas,catalog,service,repository,models,grading}.py`.
- `content/reading_v1/{manifest.json,README.md}` и загрузка `ReadingCatalog()` со всеми проверками.
- `backend/tests/test_reading.py`, `test_self_registration.py`, `test_firebase_auth.py`.
- iOS `ReadingModels.swift`, `ReadingAPI.swift`, Reading/Auth тесты и документы `docs/ALUA_READING_STAGE2_RESULT.md`, `ALUA_2_1_STAGE1_AUTH_TRANSITION.md`, `ALUA_2_1_STAGE4_RESULT.md`.
- OpenAPI получен локально через `app.openapi()`, без запуска сервера и обращения к БД.

## Реальный dataset

Dataset 1.0.0: 18 книг (04–21), 72 теста, 216 passages, 2880 вопросов; **63 enabled, 9 excluded**, 60 зарегистрированных PNG assets. Manifest statuses сами по себе другие: 65 `needs_review`, 7 `blocked`; дополнительные проверки backend исключают ещё 2 теста. Все 63 разрешённых помечены `not_fully_proofread`. Источник доступности — `enabled_for_private_practice`, не количество файлов и не только `content_status`. Фронтенд дополнительно исключает `blocked`.

Cambridge 12 использует исходные Test 5–8, а `test_ordinal` 1–4. Нельзя заменять source number порядковым номером. Названия, книги и список экзаменов не зашиты в UI.

15 фактических типов: `multiple_choice_single`, `multiple_choice_multiple`, `true_false_not_given`, `yes_no_not_given`, `matching_headings`, `matching_information`, `matching_features`, `matching_sentence_endings`, `sentence_completion`, `summary_completion`, `note_completion`, `table_completion`, `flow_chart_completion`, `diagram_labelling`, `short_answer`. Имена wire types сохраняются буквально.

## Авторизация и регистрация

Все Reading routes наследуют `get_current_user`. Нет публичного каталога. JWT с двумя точками проверяется Firebase Admin SDK с `check_revoked=True`, только если `FIREBASE_AUTH_ENABLED=true`; emulator доверие запрещено. Firebase UID разрешается через `firebase_identities` в PostgreSQL learner ID. Неизвестная связь → 403 `identity_not_allowed`. Пароли backend не принимает. Legacy device tokens независимы, web их не использует и не изменяет.

Phase B: Firebase email/password sign-in → ID token → `GET /api/v1/me`. Регистрация: создание Firebase account → ID token → `POST /api/v1/auth/register` с `{display_name?: string | null}`. Backend сам проверяет token, создаёт learner и mapping атомарно. Existing mapping возвращает прежний профиль; повторный запрос не переименовывает его. При временной ошибке provisioning сохранять Firebase user и повторять register, не createUser. Уточнение Phase B по фактическому AuthSession.swift: login/restore вызывает register автоматически только после точного 403 identity_not_allowed от /me, чтобы завершить partial signup. Прочие 403 не запускают provisioning. Self-registration может быть отключена; ограничения по умолчанию 120 verification requests/minute на процесс и 20 новых mappings/hour через общий DB lock. Обрабатывать 429/503, не обходить лимиты.

## Контракты API

Prefix по умолчанию `/api/v1`. В Phase B web вызывает `GET /reading/books`, `GET /me`, `POST /auth/register`. Reading attempts/results endpoints остаются планом следующих фаз.

| Method | Path | Назначение |
|---|---|---|
| GET | `/reading/books` | `{items:[{book_number,exams:[entry]}],dataset_version}` |
| GET | `/reading/exams?book=18` | Плоский learner-specific каталог |
| GET | `/reading/exams/{exam_id}` | Только public projection экзамена + metadata |
| POST | `/reading/attempts` | `{event_id:UUID,exam_id,mode,selected_passage?}` |
| GET | `/reading/attempts?limit=50&offset=0` | История с pagination |
| GET | `/reading/attempts/{uuid}` | Попытка + snapshot exam |
| PUT | `/reading/attempts/{uuid}/answers/{question_id}` | `{event_id,expected_version,answer}` |
| POST | `/reading/attempts/{uuid}/sync` | `{event_id,expected_version,answers:{question_id:string}}` |
| PATCH | `/reading/attempts/{uuid}/state` | `{event_id,expected_version,current_passage,annotations?,crossed_options?}` |
| POST | `/reading/attempts/{uuid}/check` | Practice only, выбранные question_ids |
| POST | `/reading/attempts/{uuid}/submit` | `{event_id,expected_version}` |
| GET | `/reading/attempts/{uuid}/result` | Реальный server grading |
| GET | `/reading/assets/{asset_id}` | Authenticated PNG, private cache, ETag |
| GET | `/me` | Существующий learner profile |
| POST | `/auth/register` | Идемпотентный learner provisioning |

Entry включает `exam_id`, `source_book`, `source_test_number`, `test_ordinal`, `question_count`, `passage_count`, `enabled_for_private_practice`, `content_status`, `not_fully_proofread`, `in_progress_attempt_ids`, `completed_attempts`, `best_estimated_band` и version/hash metadata. UI валидирует и использует только необходимое подмножество. Reading GET responses не имеют `response_model`: OpenAPI даёт `{}`. Поэтому авто-generated response types не дают защиты; TypeScript subset синхронизирован с source и валидируется на границе.

API errors: `{error:{code,message}}`; validation может возвращать FastAPI `detail`. UI не показывает произвольный backend text/stack trace. Клиент различает configuration, auth, permission, timeout, network и malformed-response; GET retry ограничен одним token refresh после 401. Ответы и токены не логируются. `cache:no-store`, credentials omitted, redirects rejected. Нет server proxy с учётными данными.

## Attempts, grading и безопасность

Версии `expected_version` + UUID `event_id`: повтор того же события возвращает acknowledgement, другой payload с тем же UUID конфликтует. Learner-level advisory lock сериализует операции. Backend не гарантирует единственную активную попытку на exam при разных create UUID: web обязан сначала проверить active IDs и сохранять pending create event UUID, затем resume. Нельзя создавать попытку при mount.

Statuses `in_progress`, `submitted`, `expired`. Full exam: server `started_at`, `deadline_at` (+3600 секунд), `server_now`, `remaining_seconds`; истечение проверяется при запросах. Browser timer только отображает дедлайн. Deadline expiry и submit выполняют grading backend. Band помечен как estimate; web не пересчитывает его.

Repository фильтрует attempt одновременно по UUID и learner ID; чужой UUID → 404. Private answer keys остаются в snapshot БД/серверном dataset. Public projection удаляет private source references; assets адресуются только registered ID и защищены auth. Не использовать обычный публичный img URL без bearer — будущий renderer загружает blob с авторизацией и освобождает object URL. Все content strings рендерить текстом/typed blocks, без unsafe HTML. Контент Cambridge не скопирован в public/bundle; перед публикацией требуются соответствующие права.

## CORS и ограничения Phase A

`ALLOWED_ORIGINS` по умолчанию пуст; middleware тогда не устанавливается. Для прямых browser requests необходим exact origin локального web. В рамках этой фазы настройки backend/production не менялись. Web Firebase configuration не передана, действительная web-сессия не создавалась. Значит каталог подключён на уровне кода, но end-to-end авторизованный путь здесь не принят.

Публичный endpoint не нужен для согласованной модели с входом. Если позже потребуется гостевой каталог, это отдельное изменение контракта, а не обход защиты.

## SDK references

При настройке сверены [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), bundled Next 16.4.3 docs и [Firebase Auth.authStateReady](https://firebase.google.com/docs/reference/js/auth.auth). Scoped dependency override устраняет установленную уязвимую версию gRPC согласно [upstream advisory](https://github.com/advisories/GHSA-m9gg-hp2v-232j); сам Firebase Firestore web-клиент не импортируется.

## Phase B transport update

Browser использует same-origin `/api/alua/*` → фиксированный Next.js external rewrite → существующий FastAPI `/api/v1/*`. Проверка реального API без token дала 401; preflight с LAN-origin дал 405. Внешняя политика CORS/authentication не менялась. Прежнее описание прямых browser-to-backend запросов относится к Phase A и заменено proxy в Phase B. `NEXT_PUBLIC_API_BASE_URL` остаётся upstream configuration. Реальный вход выполнен пользователем; authenticated каталог, профиль, restore и logout проверены через пользовательский браузер. См. PHASE_B_VERIFICATION.md.

## Phase C integration update

Исторические ограничения Phase A выше не описывают текущую реализацию. Phase C подключает authenticated `GET /reading/books`, `POST /reading/attempts`, `GET /reading/attempts/{uuid}`, `POST /reading/attempts/{uuid}/sync`, `GET /reading/assets/{asset_id}` через тот же fixed Next proxy. GET exam helper реализован, но текущий UI берёт контент из snapshot GET attempt. PUT answers, PATCH state, check, submit, result/history в Phase C не вызываются.

Каталог и preparation проверены в настоящем браузере через LAN с существующей сессией. Production Start/sync/submit не выполнялись: нельзя менять пользовательскую попытку или создавать проверочную без отдельного разрешения. 63 public projections/538 groups и исходные PNG проверены локально; synthetic attempt/save fixtures явно отделены от real API проверки в PHASE_C_VERIFICATION.md. Backend, iOS, dataset и production configuration не изменены.

## Reading v1 D/E/F update

Web now uses native IndexedDB durable drafts/outbox, three-way CAS reconciliation, explicit durable conflicts, per-tab writer fencing, local highlights/preferences, server deadline reconciliation and confirmed submit/results/readonly review/history. All scoring stays on the existing backend. `CreateAttempt` adds optional `reuse_active=false`; web sends true. Under the existing learner advisory lock it returns a matching active attempt after enforcing expiry. Legacy fingerprints/behavior remain compatible. No migration or production deployment was performed. Updated backend must be deployed before this web version's new-test Start; old strict schema returns 422. See final verification for limitations and separated fixture/local integration/production acceptance evidence.
