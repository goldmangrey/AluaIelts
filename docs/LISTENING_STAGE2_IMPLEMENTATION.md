# Listening Stage 2 — локальная реализация

Дата: 4 ноября 2026. Реализованы универсальный engine и UI на существующем Stage 1. Production не изменялся: SSH, deployment, commit/push не выполнялись.

## Фактический результат

| Метрика | Результат |
|---|---:|
| Exams in catalog | 72/72 |
| Full-content exams | 69/72 |
| Verified content exams | 4/72 |
| Preliminary scored exams | 62/72 |
| Ungraded exams | 3/72 |
| Blocked incomplete exams | 3/72 |
| Interactive positions, учтённые engine | 2864/2880 |
| Source-verified questions, без изменения Stage 1 | 206/2880 |
| Keys present / source-verified positions | 2720 / 640 |
| Audio mappings, inventory-verified | 288/288 |
| Real audio technically verified — decode | 0/288 |
| Real audio content verified | 0/288 |
| Backend tests | PASS — 23 Listening/Reading/Firebase tests |
| Browser E2E | PASS — 9 Listening scenarios across Chromium/WebKit/mobile WebKit |
| TypeScript / ESLint | PASS |
| Next.js build | PASS |
| Workers build | PASS |
| Reading regression | PASS — existing backend tests + 12 frontend release contract checks |
| Stage 1 validator consistency | PASS; original content limitations remain |

Режимы вычисляются из реальных вопросов и ключей, а не задаются списком IDs. `needs_review` допускает preliminary practice. `can_start` отдельно требует четыре существующих файла на backend с размерами из inventory. В обычном локальном окружении Oracle filesystem недоступен, поэтому реальные записи и запуск с ними здесь не проверены. Локальный E2E использует настоящие вопросы, ключи, API, PostgreSQL и потоковый proxy, но синтетические MP3/M4A из временного pytest fixture. Эти записи не входят в production manifest.

Четыре content-verified экзамена: **09 Test 4, 12 Test 5, 14 Test 1, 20 Test 4**. Для каждого backend regression проверяет 40/40 на официальных допустимых формах и unordered наборах. Это подтверждение интеграции ключей, не сверка реального аудио.

## Реализованные сценарии и контракты

- `/listening`: все 18 книг / 72 экзамена, режим, progress, Start/Resume; штатные SiteHeader, Firebase session и навигация Alua.
- `/listening/[book]/[examId]`: preparation; `/listening/attempts/[attemptId]`: workspace; дочерние `/results`, `/review`.
- `/api/v1/listening/exams`, `/exams/{id}`, `/attempts`, `/attempts/{id}`, `/sync`, `/submit`, `/result`, `/review`, `/playback`, `/audio/{part}` GET/HEAD, `/assets/{asset_id}`.
- Три независимые таблицы: `listening_attempts`, `listening_mutations`, `listening_playback_grants`. Аддитивная migration `20261104_0007`; Reading-owned tables не меняются. Downgrade сохраняет Listening history.
- Snapshot содержит точные exam/key/audio документы, schema version, content/key hashes и режим. Последующие изменения dataset не изменяют начатую попытку; результат сохраняется при submit.
- Ownership проверяется через существующий `get_current_user`. UUID событий, payload hashes, PostgreSQL advisory locks и optimistic version защищают retries/concurrent saves. Завершённая попытка неизменяема; повторный finish возвращает прежний итог.
- Ответы, marks, question/displayed part и audio checkpoint сохраняются на backend. Owner-scoped local draft/outbox хранит точный UUID незавершённого sync/submit. Старый ответ сервера не заменяет более свежий ввод; 409 запускает merge, несовместимые ответы требуют выбора пользователя. Offline retry, reload/resume и conflict recovery проверены браузерами.
- Renderer использует настоящие options и shared banks. Text/select/multi-select, отдельные slots Choose TWO, completion, matching, maps/plans/diagrams и сложные layouts через `image_backed` с интерактивными полями; увеличение оригинальных изображений. Ответы и private key evidence не публикуются до завершения; приватные source artifacts не раздаются вообще.

## Grading

Только backend: Unicode NFC, casefold, trim/collapse whitespace, точная орфография. Разбираются явные slash alternatives, optional parentheses, числовые значения и официальные written-number alternatives. Unordered slots расходуют каждый expected unit один раз; typed within-position rules требуют все компоненты. Fuzzy matching отсутствует.

Три позиции остаются **ungradable**, сохраняют official notation и отображаются с причиной; они не засчитываются как ошибочные и не входят в denominator:

| Экзамен | Вопрос | Нотация / причина |
|---|---:|---|
| Cambridge 06 Test 1 | 7 | `10(am), 4.30(pm)` — отсутствует однозначное typed правило композиции |
| Cambridge 06 Test 1 | 19 | `Monday, Thursday` — отсутствует однозначное typed правило композиции |
| Cambridge 11 Test 1 | 2 | `(£)115 / a/one hundred (and) fifteen` — неоднозначная slash abbreviation |

Эти экзамены остаются preliminary; показаны соответственно результаты по 38 и 39 оцениваемым позициям, включая число оцениваемых вопросов по каждому Part. Исходные ключи не переписывались.

Estimated IELTS Band доступен только при verified content/key режиме и отсутствии grading issues. Версия таблицы: `listening-estimate-v1`; нижние пороги raw→band: 39→9, 37→8.5, 35→8, 32→7.5, 30→7, 26→6.5, 23→6, 18→5.5, 16→5, 13→4.5, 10→4, 8→3.5, 6→3, 4→2.5. Ниже 4 оценка не выводится. Это приблизительная practice conversion; точные пороги зависят от варианта экзамена — [IELTS: scoring in detail](https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail). Preliminary/ungraded не получают band.

## Audio и безопасность

`backend/app/content/listening_audio_v1/audio_manifest.json` создан из фактического Desktop inventory: **288 уникальных paths/identities; 272 MP3 + 16 M4A Cambridge 05; 1 891 278 047 bytes**. Min/max: 895 047 / 19 477 068 bytes; пустых файлов, дубликатов и пропущенных identities нет. Проверены соответствие directory/filename book, test/part и `audio_mapping_key`. Cambridge 12 сохраняет printed Tests 5–8 и ordinals 1–4.

`file_inventory_verified=true`; `decode_verified=false`, `content_mapping_verified=false`; duration/SHA-256 неизвестны и оставлены null. MIME определяется форматом имени (`audio/mpeg`, `audio/mp4`), содержимое контейнера ещё требует ffprobe. Аудио не копировалось в frontend.

Firebase Bearer используется только в POST выдачи grant. Next same-origin route `/api/listening/authorize` проверяет origin/Host и сохраняет opaque 15-minute grant в scoped HttpOnly/SameSite=Strict cookie (Secure на HTTPS); grant не возвращается JavaScript. Backend хранит SHA-256 grant и проверяет expiry/attempt/owner. Постоянных секретов и Firebase tokens в URL нет. Плеер обновляет доступ периодически, после foreground и при повторном подключении.

`/api/listening/audio/{attempt}/{part}` передаёт Range/If-Range/HEAD в фиксированный upstream и возвращает поток `response.body`, без полной буферизации в Worker. Backend FileResponse поддерживает 206/416/HEAD и MP3/M4A. `private, no-store`, закрытые grants, confinement resolved path внутри `LISTENING_AUDIO_ROOT`, запрет traversal/symlink escape и сверка размера. Нет листинга или произвольного filesystem endpoint. Изображения доступны только владельцу attempt, по public asset ID из snapshot, с проверкой SHA-256; keys/private assets не имеют endpoint.

Native HTMLAudioElement: три основные кнопки (−5, Play/Pause, +5), seek bar, время, loading/buffering/error; metadata preload следующей части; checkpoint/resume без autoplay на reload; последовательный переход Parts с fallback при запрете autoplay. Вопросы переключаются независимо от audio. Горячие клавиши исключают поля/редактируемые элементы; touch targets около 44px и больше. Нет speed/volume/download/settings.

## Файлы Stage 2

Добавлены:

- `backend/app/modules/listening/{catalog,grading,models,schemas,service,router,__init__}.py`.
- `backend/alembic/versions/20261104_0007_listening.py`.
- `backend/app/content/listening_audio_v1/audio_manifest.json`.
- `backend/scripts/listening_media/{import_inventory,probe_audio}.py`.
- `backend/tests/test_listening.py`, `backend/tests/test_listening_browser.py`.
- `web/src/features/listening/{api,audio-proxy,draft,models,pages,player,questions}.ts[x]`, `listening.module.css`.
- `web/src/app/listening/[book]/[examId]/page.tsx`, `attempts/[attemptId]/page.tsx`, дочерние `results/page.tsx`, `review/page.tsx`.
- `web/src/app/api/listening/authorize/route.ts`, `audio/[attemptId]/[part]/route.ts`.
- `web/scripts/test-listening.mjs`, `web/playwright.listening.config.ts`, `web/tests/listening.spec.ts`, этот отчёт.

Изменены: `backend/app/api.py` (router), `backend/app/core/config.py` (audio root), `backend/alembic/env.py` (models), `backend/tests/test_reading.py` и `test_firebase_auth.py` (только ожидаемая migration head); `web/src/app/listening/page.tsx` и `web/src/app/page.tsx` (настоящий Listening вместо Coming soon); `web/tests/public-pages.spec.ts` (Listening исключён из старого списка незавершённых sections). Stage 1 JSON, source reviews и pipeline не изменялись; frontend Reading и Firebase implementation не менялись. Новых npm dependencies нет.

## Воспроизведение проверок

Из корня репозитория:

```sh
PYTHONPATH=backend backend/.venv/bin/pytest -q backend/tests/test_listening.py backend/tests/test_reading.py backend/tests/test_firebase_auth.py
ALUA_RUN_LISTENING_BROWSER=1 PYTHONPATH=backend backend/.venv/bin/pytest -q -s backend/tests/test_listening_browser.py
backend/.venv/bin/ruff check backend/app/modules/listening backend/scripts/listening_media backend/tests/test_listening.py backend/tests/test_listening_browser.py backend/alembic/versions/20261104_0007_listening.py
```

В `web/`: `pnpm typecheck`, `pnpm lint`, `pnpm build`, `pnpm build:workers`, `pnpm test:reading-release --project=release-contracts`.

Backend fixtures создают отдельный временный PostgreSQL cluster, выполняют migrations и генерируют синтетические MP3/M4A через ffmpeg. Browser harness собирает временную копию Next с test-only session/token adapter и настоящим локальным FastAPI. Production Firebase/attempts не используются. Проверены: auth/ownership/Firebase binding, 72 modes/IDs, 288 mappings, snapshots, concurrent writes/idempotency/terminal state, все четыре verified keysets, альтернативы/word limits/unordered/composite rules, grant expiry/wrong-attempt, GET/HEAD/Range/416, confinement, private asset isolation.

9 browser checks: три сценария × Chromium 1440×900, WebKit 1440×900, iPhone viewport WebKit 390×844. Сценарии покрывают library→preparation→start→play→input→seek/±5→navigation→autosave→reload/checkpoint→four-part transition→finish confirmation→result→readonly review; preliminary/ungraded; matching/map/image zoom; M4A; keyboard exclusion; failed save/exact UUID retry/newer typing; remote conflict/reconciliation; потерянный ответ submit и безопасный retry с прежним UUID. Оригинальные изображения проверяются по `naturalWidth > 0`, а не только `img.complete`; test network guard разрешает локальные blob URLs. Проверено отсутствие horizontal document overflow. Скриншоты сохраняются в ignored `.next/`.

Не выполнены: реальный Oracle playback/decode smoke; физический iPhone/Safari background/foreground; live Firebase credentials; production PostgreSQL; streaming через реально развёрнутый Cloudflare Worker. WebKit automation подтверждает локальный браузерный сценарий, а не все особенности физического iOS.

## Остаточные Stage 1 блокировки

- Cambridge 04 Test 1: отсутствует Q34; официальный key также отсутствует.
- Cambridge 06 Test 2: Q6–10 не renderable из-за исходной таблицы.
- Cambridge 14 Test 3: Q1–10 заблокированы из-за исходной страницы.
- Cambridge 04 Tests 2–4: полный контент, без официальных ключей — разрешён ungraded.
- Остальные `needs_review` сохраняют preliminary статус; повторная массовая PDF-сверка не выполнялась.

## Последующая доставка — здесь не выполнялась

1. Backend: доставить код, Stage 1 exams/keys/public assets и отдельный audio manifest в существующее backend release. Не монтировать content directory как static/public. Сохранить существующие Firebase/DB settings, резервную копию БД и процедуру rollback; выполнить `alembic upgrade head` в штатном окружении. Migration добавляет только Listening tables. `LISTENING_AUDIO_ROOT` по умолчанию `/opt/alua/shared/listening/audio/`; аудиофайлы не переносить и не переименовывать. Процессу нужны права чтения.
2. Проверить реальные media read-only. Из корня доставленного checkout, где доступны ffprobe/ffmpeg, одна команда:

   ```sh
   python3 backend/scripts/listening_media/probe_audio.py --root /opt/alua/shared/listening/audio --manifest backend/app/content/listening_audio_v1/audio_manifest.json > /tmp/alua-listening-audio-probe.jsonl
   ```

   Скрипт читает все 288 файлов, проверяет размеры, ffprobe metadata и полный ffmpeg decode; выводит только JSONL, не меняет записи/production config. Cambridge 08 включён в ту же проверку. Успешный decode не подтверждает Book/Test/Part по содержанию. Сверку содержания выполнять отдельно; сейчас все content flags false.
3. Frontend: после backend migration/API smoke собрать и доставить Cloudflare отдельно штатным способом проекта, с существующим HTTPS `NEXT_PUBLIC_API_BASE_URL` и Firebase configuration. Backend audio/keys не входят в frontend build. Этот этап не выполнялся; deploy command автоматически не запускался.
4. Smoke под разрешённым пользователем: catalog counts/modes; новый Listening attempt 14 Test 1; авторизация аудио; MP3 и Cambridge 05 M4A, Range/HEAD/416, seek, обновление grant, reload/save/submit/review; negative ownership checks. Проверить Safari и Worker streaming без полного buffering. Для Reading достаточно read-only открыть catalog/собственную существующую попытку; не завершать и не перезаписывать её ради smoke. Все мутации smoke относятся только к новым Listening attempts.


## Private practice simplification — 2026-11-05

New snapshots carry `grading_policy=practice-v2`. Their existing keys are graded regardless of editorial mode; a complete 40-position score permits the existing estimated band conversion. Missing/ambiguous keys remain ungraded, with a partial score and no band. The table is unchanged: below raw 4 it provides no numeric band. Legacy snapshots without the policy retain their previous grading behavior; stored results are read unchanged, including repeated Submit.

All 72 production exams have 40 positions/keys and available audio/source material. 70 have complete grading/band eligibility; Cambridge 06 T1 has 38 gradable positions (Q7/Q19 ambiguous), Cambridge 11 T1 has 39 (Q2 ambiguous). No dataset keys, metadata, tables or migrations changed.

Listening hides editorial badges/labels in catalog, preparation, workspace, Results and Review. Results show `Estimated practice band` when available and a short partial-score explanation when needed. Review V2 uses backend per-question verdicts rather than editorial mode; original materials, read-only navigation/audio, zoom and split panes remain shared with V3.

Validation: 33 backend Listening/Reading/auth tests PASS; TypeScript/ESLint PASS; 24 real-backend browser scenarios PASS across Chromium/WebKit/desktop/mobile; Review suite 44 PASS (4 desktop skips of mobile-only cases). Production OpenNext build and local workerd smoke PASS. A test helper now waits only on the current attempt draft, avoiding unrelated historical localStorage entries.

Release assembly uses HEAD plus Listening runtime files only. Premium Home/Login source and CSS match the current workspace byte-for-byte; unrelated pending Reading edits are excluded. Backend release is copied from the active release, changing only `catalog.py` and `grading.py`; all dataset/audio/other application bytes are preserved. Normal encrypted backup succeeded: `alua-20261105T180856Z.dump.age`. No commit or push.

Published: https://alua.study — Worker version `c400775e-e0e4-49cd-9392-db345250b786`, backend `/opt/alua/releases/listening-practice-20261105` active/running. Health/Home/Login/Reading/Listening shells return 200; protected API gates return 401 without authentication. Listening/Reading attempt and mutation counts plus full-row aggregate fingerprints match before/after; no production attempt was created or recalculated. Rollback: remove only `zzzzzzzz-listening-practice-20261105.conf`, daemon-reload/restart `alua-api`; previous Worker `5a93eac7-3f9f-43cb-8d3a-218d211251ee`. Previous backend release remains intact.

Post-deploy native browser smoke: Chromium and WebKit both passed premium Home (four section cards), Login email/password form, and signed-out Listening shell. No authentication or production data mutation was performed.
