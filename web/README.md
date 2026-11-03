# Alua Web — Reading v1 (D / E / F)

Веб-клиент существующего Alua. Next.js App Router, React, TypeScript strict, Tailwind CSS, Firebase Web SDK. Backend и SwiftUI не изменяются. Reading v1 включает сохранение, Finish, результаты, review и историю. Production-приёмка остаётся ручной; перед новым Start требуется совместимое обновление backend.

## Запуск

Node.js 22.13+ и pnpm. `.env.local` уже заполнен пользователем; не перезаписывайте его примером.

```bash
cd /Users/yeskendir/Projects/Alua/web
pnpm install --frozen-lockfile
pnpm dev --hostname 0.0.0.0
```

Открыть http://localhost:3000 или http://192.168.10.18:3000. Если порт занят, используйте существующий сервер или остановите именно его процесс перед новым запуском. Проверочные серверы агента по окончании остановлены.

На новом checkout создать `.env.local` из `.env.example` и заполнить публичную Web-конфигурацию **существующего Firebase project**:

```dotenv
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
NEXT_PUBLIC_API_BASE_URL=https://alua-api.flora-flowers.kz/api/v1
```

Данные берутся из Firebase Console → Project settings → General → Your apps → Web app → SDK setup and configuration → Config. Web App уже зарегистрирован пользователем. Email/Password должен быть разрешён в Authentication → Sign-in method. Не подставлять iOS app ID или Admin credentials. Web App ID имеет вид `1:…:web:…`, sender ID — публичный идентификатор. Sender ID передаётся SDK; сам email/password flow использует ключ/project/app/domain. Все `NEXT_PUBLIC_*` публичны и встраиваются при build; после изменений требуется restart/rebuild. `.env.local` игнорируется Git.

## Что работает

- Главная Alua Minimal и три Coming soon секции сохранены.
- `/login`: email/password Firebase sign-in, show/hide password, ошибки, защита повторной отправки, возврат на безопасный same-origin `next` путь.
- `/register`: Firebase account → metadata → Alua learner; partial signup продолжает setup без нового createUser.
- `/forgot-password`: настоящий Firebase reset, одинаковое подтверждение для отсутствующего/существующего аккаунта.
- `/profile`: Firebase email, реальное имя learner, logout.
- `/reading`: после разрешения сессии — реальный authenticated каталог. До входа — Log in; при конфигурационных/сетевых/permission/server ошибках — явное состояние. Нет бесконечного ожидания SDK или сети.
- `/reading/cambridge-12` и `/reading/cambridge-12/cambridge-12-test-05`: реальные каталог/подготовка; source numbering сохранён, disabled/blocked тесты исключены. Start/Continue проверяют свежую доступность и открывают настоящую attempt.

## Архитектура авторизации

Firebase управляет persistence и refresh токенов. Приложение не сохраняет ID token самостоятельно. `features/auth/session.ts` — единое состояние через useSyncExternalStore; listener отслеживает sign-in/sign-out и смену UID. Generation guard не допускает показа позднего ответа старой сессии; каталог прячется и запрос отменяется при logout/смене пользователя. Private profile/catalog не лежат в общем Next.js cache.

После Firebase login/restore выполняется `GET /me`. Только точный `403 identity_not_allowed` запускает `POST /auth/register`, как в существующем SwiftUI flow. Все остальные 403 остаются запретом доступа. Retry provisioning безопасен: backend сам идемпотентно создаёт mapping и learner. Ошибка не удаляет Firebase account; UI предлагает Retry account setup или Use another account. При возобновлении после refresh снова проверяется `/me`, а не создаётся второй Firebase user.

`lib/api/client.ts` ограничивает весь запрос 15 секундами, включая получение token и чтение response body; GET получает максимум один token refresh после 401. POST автоматически не повторяется. Firebase initialization/SDK operations также ограничены временем. При неизвестном исходе createUser поздний auth callback может восстановить сессию; при email-already-in-use UI направляет на login/reset вместо автоматического создания другого аккаунта.

## LAN, proxy и CORS

Найденная причина infinite loading: Next.js блокировал dev HMR с LAN-host, поэтому SSR показывал Loading, а React hydration/useEffect не запускались. `allowedDevOrigins` теперь явно разрешает `127.0.0.1` и `192.168.10.18`. Это **только Next development**, не FastAPI CORS. При смене LAN IP добавьте точный новый hostname в next.config.ts и перезапустите dev; wildcard отсутствует.

Backend требует Bearer и возвращает 401 без него. Проверенный preflight с LAN-origin возвращал 405. Поэтому browser request идёт на same-origin `/api/alua/*`, а server-side Next.js Route Handler пересылает его на фиксированный `NEXT_PUBLIC_API_BASE_URL` существующего FastAPI с Authorization. Это транспортный proxy, без собственного auth/backend/БД. Upstream не берётся из query/body; redirects запрещены клиентом; fetch использует `cache:no-store` и не передаёт browser cookies. Права по-прежнему проверяет FastAPI. Production CORS/authentication policy не изменялись.

В локальной конфигурации API ранее оставался `localhost:8000`, где не было сервера. Для реального теста локальный параметр переключён на существующий HTTPS Alua API. Для локального FastAPI можно вернуть loopback URL; Next proxy будет обращаться к нему с Mac, а не с телефона пользователя.

Firebase email/password + обычный reset используют SDK и штатный Firebase hosted email handler. Никакой OAuth popup/redirect или LAN continue URL не передаётся. Для выполненного real LAN login дополнительных изменений authorised domains не понадобилось. Для будущих OAuth/email-link flows отдельно нужны разрешённые домены и подходящий HTTPS origin. Если API key имеет HTTP referrer restrictions, они должны разрешать используемые web origins. Не отключать ограничения и не обходить browser security warnings. Local HTTP LAN пригоден для ограниченной разработки; опубликованный сайт должен работать по HTTPS. Сессии localhost и LAN-IP раздельны по origin.

## Проверки

```bash
pnpm typecheck
pnpm lint
pnpm build
pnpm exec playwright install chromium webkit firefox
pnpm test:phase-b
pnpm test:phase-c
pnpm test:reading-release
```

`pnpm test` также запускает Phase B. Runner создаёт временную копию приложения с пустой Firebase/API конфигурацией, собирает её, проверяет на 127.0.0.1:3100 и удаляет копию. Он не меняет `.env.local`, не мешает dev server и не выполняет account operations в production. Существующие test source files сохранены. Старый Phase A placeholder-only browser scenario исторический: его ожидаемые auth-заглушки намеренно заменены формами, поэтому общий legacy config не является актуальным полным suite. Четыре первоначальных contract tests по-прежнему входят в Phase B suite.

[Phase B verification](docs/PHASE_B_VERIFICATION.md) разделяет реальные production/LAN проверки, SDK emulator проверки и тестовые fault fixtures. [Backend contracts](docs/BACKEND_INTEGRATION.md), [Reading plan](docs/READING_ARCHITECTURE.md).

## Изолированный Auth Emulator

Опциональный `NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_URL=http://127.0.0.1:9099` разрешён только development, только с `demo-` project ID и loopback HTTP API/emulator. В production или с реальным project/API такая конфигурация отклоняется. Нельзя включать эту переменную вместе с настоящим Alua project.

Emulator проверяет SDK flows, но **не** полноценный Alua backend: существующий verifier специально запрещает unsigned emulator tokens. Серверную безопасность ради тестов не ослаблять. В Phase B emulator-тесты выполнены из временной копии app с demo configuration; реальные `.env.local` credentials туда не копировались. SMTP-доставка настоящих reset-писем не заявляется.

## Reading v1 — D / E / F

`/reading/attempts/{uuid}` открывает существующий snapshot. Явный Start повторно проверяет каталог и отправляет `reuse_active:true`; backend под learner lock возвращает существующую активную попытку, не сбрасывая ответы. **Эта опция требует нового backend из этого checkout.** Старый production backend отклонит новый Start с 422; fallback без защиты не выполняется. Continue и прежние API сохранены. Миграций БД и новых environment variables нет.

Экзамен: две колонки, независимая прокрутка, регулируемый разделитель, Passage 1–3, All 40 и все 15 типов. IndexedDB хранит scoped по Firebase UID/attempt/hash ответы, точный outbox, конфликт, review marks, scroll, font/split и highlights. Offline-ввод работает в уже загруженном экзамене. Saved означает server acknowledgement; локальный commit — Saved on this device. Retry повторяет тот же event UUID, CAS конфликты требуют явного выбора. После refresh/reopen черновик сверяется с backend. Второй локальный tab readonly; после закрытия прежнего writer восстановление может занять около трёх секунд.

Таймер использует server deadline; focus/visibility/reconnect сверяют сервер. При deadline ввод блокируется, существующий backend подтверждает expiry и grading. Finish с подтверждением сначала синхронизирует ответы и сохраняет submit event. Неизвестный исход не выдаётся за успех. Результат и read-only review доступны после server terminal state:

- `/reading/attempts/{uuid}/result`
- `/reading/attempts/{uuid}/review`
- `/reading/history`

Scoring и estimate приходят с backend. Локальные ответы, не принятые до expiry, показаны отдельно и не включаются в score. Highlights/UX preferences только на устройстве; logout удаляет local-only drafts/highlights этого аккаунта. Холодный запуск offline и защита от очистки/эвикции browser storage не обещаются.

## Изолированные проверки Reading

`pnpm test:phase-c` использует public projections всех 63 доступных локальных экзаменов, реальные source PNG, синтетические attempts/save. `pnpm test:reading-release` дополнительно проверяет настоящий IndexedDB, восстановление, конфликты, Finish/expiry/result/review/history с контролируемой auth/API fixture. Тестовые результаты заранее получены из настоящего Python scorer во временном экспорте; production UI сам не оценивает ответы. Временные app/routes/JSON удаляются; test source files остаются как регрессии.

Реальная локальная backend/browser интеграция (требуются установленные локальные PostgreSQL binaries и Playwright browsers):

```bash
cd /Users/yeskendir/Projects/Alua/backend
ALUA_RUN_READING_BROWSER=1 .venv/bin/python -m pytest tests/test_reading_browser_integration.py -q -s
```

Runner создаёт отдельный временный PostgreSQL, поднимает настоящий FastAPI на loopback 3400 и временный Next на 3300, использует существующий local enrollment auth только для disposable identity и выполняет реальные Start/sync/submit/grading/result/history. Firebase production login не подменяется утверждением об E2E проверке. Конфигурация основного приложения/production БД не используется и не изменяется.

[Final implementation, evidence and manual acceptance](docs/READING_RELEASE_VERIFICATION.md), [question coverage](docs/PHASE_C_COVERAGE.md), [Backend contracts](docs/BACKEND_INTEGRATION.md).

## Cloudflare Workers

Подготовлен существующий Next.js runtime через OpenNext; обычный `pnpm build` сохранён. Локальная проверка в workerd: `pnpm build:workers && pnpm preview:workers`. [Конфигурация, environment variables, проверки и точные настройки GitHub integration](docs/CLOUDFLARE_WORKERS.md). Опубликовано: https://alua-ielts.yeskendiriskakov.workers.dev. Результаты production-проверок и ограничения браузерных тестов записаны в указанном документе.
