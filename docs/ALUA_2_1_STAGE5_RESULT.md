# Alua 2.1 — Stage 5: local release candidate

Дата завершения проверок: 2026-10-30, Asia/Almaty. **Production release не выполнен.** Production остаётся на Stage 1 / `20261029_0002` по исходным данным владельца; Oracle по SSH не использовался.

## 1. WidgetKit

Добавлен **Alua Glance**, один новый `accessoryRectangular` widget. Монохромное содержимое: «ВСПОМНИ» → настоящий English term → «Помнишь значение?». Перевод не выводится. Если due-карточек нет — реальный номер/прогресс дня; до первого знакомства — приглашение открыть учебник. Уже установленные Today/Vocabulary/Grammar/Practice/Partner widgets и их kinds сохранены; прежний Vocabulary в rectangular Lock Screen family использует тот же безопасный Glance-контент.

Виджет не делает HTTP-запросов и не получает bearer-токены. Карточка выбирается только из `book` со статусом `review_due`. Будущая подборка не является источником Quick Recall. При неотправленных действиях вместо карточки выводится явно локальный статус дня. Срок актуальности — не дольше суток после подтверждения сервера и не позже границы дня Asia/Almaty.

## 2. Точная карточка и deep link

Минимально расширен существующий `alua://review`:

- `alua://review` — обычные Stage 3 повторения.
- `alua://review/item/<itemID>?learner=<learnerID>&generation=<UUID>&expires=<epoch>` — точная карточка Glance.
- Прежние ссылки `/review/session/<id>`, grammar, vocabulary, practice и partner сохранены.

В Info.plist зарегистрирована схема `alua` — её отсутствие обнаружено при QA. Секретов в URL нет. `MainTabView` обрабатывает ссылку только после существующей авторизации и создания learner-scoped store. `WidgetQuickRecallView` обновляет Today через authenticated API и проверяет learner, срок, подтверждённый Glance, совпадение ID/term, наличие изученной карточки, due-статус и отсутствие неотправленного действия по ней. Обновление generation при том же подтверждённом term не ломает ещё действующую ссылку.

Для чужой, скрытой, устаревшей или недоступной карточки открывается обычная очередь повторений. Открытие/закрытие не вызывает `record`; ответ записывается только после «Проверить»/«Не знаю» через прежнюю durable queue, тот же event UUID и Stage 3 `/study/actions`. Алгоритм SRS не менялся.

## 3. App Group v5

`group.com.alua.app`, существующие storage keys и schema version **5** сохранены. В envelope добавлено необязательное поле `glance`; старые v5 JSON декодируются без него. Прежние learner/partner payloads не переименованы. Glance содержит только learner/card IDs, term, прогресс, признак локальных данных и временные границы; без перевода/токена.

`StudyDisk.confirmedAt` — совместимое optional поле кеша, фиксирующее последнее успешное получение серверного Today. Исходный ответ сохраняется на диск до отправки, прежний UUID при retry сохраняется. `WidgetSyncService` получает обновления после сохранения состояния, знакомства, hide/unhide, ответа и подтверждения синхронизации. Запоздалая публикация другого learner игнорируется. При смене learner App Group очищается; cold launch того же learner сохраняет точную ещё действующую generation.

App Group обновляется сразу. WidgetCenter reload coalesced с интервалом не менее 30 секунд; legacy snapshot fetch ограничен 60 секундами. Реальное расписание перерисовки контролирует WidgetKit. Для смены профиля выполняется немедленная инвалидизация. Устаревший системный кадр не позволяет записать ответ от другого learner.

## 4. Изменённые файлы

- Shared: `AluaShared/{DeepLink,WidgetSnapshotModels,WidgetSnapshotStorage}.swift`; новые `GlanceWidgetSnapshot.swift`, `AluaGlanceContent.swift`.
- Widget target: новый `AluaGlanceWidget.swift`, `AluaWidgetsBundle.swift`, rectangular branch `VocabularyWidget.swift`.
- App: `Services/WidgetSyncService.swift`, `Navigation/MainTabView.swift`, `Features/Study/StudyView.swift` (optional confirmation timestamp и публикация snapshot), `StudyLessonView.swift` (повторения из deep link и исключение pending из due), новый `WidgetQuickRecallView.swift`.
- QA accessibility identifiers в `TodayView.swift`, `StudyBookView.swift`.
- `project.yml`, project.pbxproj и Info.plist: URL scheme, совместимые version macros, отдельная loopback QA configuration/scheme и UI test target. Production Debug/Release API URL сохранён.
- `Assets.xcassets/AppIcon.appiconset`: устранена отсутствовавшая иконка; использована существующая надпись `alua.` чёрным на белом. Это не новая дизайн-система.
- `AluaTests/WidgetRecallTests.swift`, `AluaUITests/AluaProductQATests.swift`, одна необходимая backend regression в `tests/test_study.py`.
- `backend/scripts/qa/stage5_server.py`: воспроизводимая изолированная QA-конфигурация с настоящими FastAPI, SQLAlchemy, PostgreSQL и обычным enrollment. Нет production admin routes.
- `.gitignore`: локальные signed binaries в `/artifacts/stage5/` исключены из будущего commit.

AuthSession, DeviceTokenStore, существующие entitlements, SRS, каталог, порядок 50×30 и backend learning services не переписаны. Новых Alembic revisions в Stage 5 нет.

## 5. Сценарии и тесты

Backend: **14 passed** на временных PostgreSQL clusters; Ruff — **All checks passed**. Логи: `docs/stage5/test-results/backend.txt`, `ruff.txt`. Проверены 1500/50/30; независимость learner; A1/B2/default; resume; пропуск календарной даты; Book, English/Russian search; known/unknown/hide/unhide; полный День 50 и дальнейшее повторение; legacy history; duplicate/concurrent UUID; auth/exercises/grammar. Добавлена проверка: чтение Today/Book не создаёт review response, повтор одного ответа создаёт ровно один response и не меняет квоту новых единиц.

Swift regressions проверяют v5 compatibility, подтверждённые snapshots, отсутствие вопроса при pending, смену learner/позднюю публикацию, точный itemID, скрытую/expired/wrong-learner карточку, отсутствие события на opening и сохранение UUID после перезапуска. Существующие StudyStoreTests/Stage4PresentationTests сохранены.

Реальный UI использовал отдельный loopback backend и настоящие записи каталога. Первый learner прошёл обычный ввод 32-hex кода, диагностику 12/12, 10 → пауза → 11, перезапуск на 18/30 → 19, паузу 20 и завершение 30. Первый длинный UI-прогон остановился затем на неверном селекторе `learn` в отсортированном списке, не на потере прогресса. Селектор исправлен на ID строки; отдельный последующий проход Book → Card → Review → Feedback → Progress успешно выполнен. Неуспешные попытки настройки системного widget gallery не считаются проверкой бизнес-логики.

**iOS: 10 tests passed, 0 failures** — AuthSession 2, StudyStore 2, Stage4Presentation 4, WidgetRecall 2. `xcodebuild test` выполнен на iOS 27 simulator с обычными entitlements и локальной подписью; Keychain security не отключалась. Лог: `docs/stage5/test-results/ios-unit.txt`.

Настоящий системный Lock Screen Widget установлен в simulator. Нажатие `learn` открыло `learn` в полном review UI, без ответа (`widget-tap.txt`). До ответа сервер имел 0 review events / review_count=0. После «Не знаю» — 1 event / count=1; двукратный replay того же UUID не изменил count и квоту новых карточек (`widget-answer.txt`, `widget-server-verification.txt`). Оба UI теста этого пути прошли. В процессе настройки тестового wallpaper были добавлены две копии одного и того же kind; это видно на реальном снимке и не является двумя вариантами продукта.

Дополнительно успешно выполнены UI-прогоны на iPhone SE (375×667 pt): длинное `contribute to development`, 15→18 и перезапуск, Book/русский поиск с клавиатурой/Card/Review. Отдельный прогон при `accessibility-extra-extra-extra-large` прошёл через Today/Lesson/прокрутку/Grammar/Diagnostic. Логи: `small-iphone-ui.txt`, `accessibility-ui.txt`.

Реальная потеря связи проверена приостановкой только локального QA HTTP server: приложение записало 19-й ответ и было завершено. На диске осталась очередь из 1 UUID, сервер имел 18. После восстановления сервера и обычного запуска приложения очередь стала 0, сервер — 19, исходный UUID записан единожды. Replay не изменил 19. Логи `offline-ui.txt`, `offline-server-verification.txt`, снимки 30/31. Временные функции управления сетью и системным widget gallery удалены; оставшиеся четыре UI regression tests после очистки успешно скомпилированы (`qa-final-compile.txt`). Матрица всех 20 сценариев: `docs/stage5/SCENARIO_MATRIX.md`.

## 6. Реальные скриншоты

Папка: **`docs/stage5/screenshots/`**, **29 реальных PNG**, индекс `README.md`, размеры и SHA-256 в `manifest.json`. PNG сняты с реально установленного QA-приложения через XCUIApplication/XCUIScreen и системный WidgetKit/SpringBoard. В приложении не добавлены mockup screens, fixture views или обход авторизации. Использованы два изолированных QA learner; числа на этих снимках не являются прогрессом владельца.

Today 0/30, 18/30, паузы 10/20, завершение 30, результат диагностики, Book days/words, Card, Review и Progress доступны отдельными файлами. Некоторые ранние снимки извлечены побайтово из PNG objects незавершённого xcresult (источник сохранён в `first-run-object-sources.json`); изображения не редактировались и не генерировались. Ранний кадр незавершённого перехода Review удалён; устойчивый полноэкранный Review доступен в `20-widget-exact-card-no-answer.png`.

## 7. Подписанная сборка

**ARCHIVE SUCCEEDED / EXPORT SUCCEEDED**. Версия **2.1 (5)**, Apple Development, team `A8DD9HJC4H`; профили приложения и widget extension включают существующий App Group. Проверены archive и экспортированный IPA через `codesign --verify --deep --strict`, версия и App Group обоих provisioning profiles (`signing.txt`). SHA-256, API URL и обязательная backend revision зафиксированы в `docs/stage5/release/manifest.json`; контрольные суммы iOS sources — `ios-files.sha256`.

Локальные артефакты, исключённые из Git:

- `artifacts/stage5/Alua-2.1-build5.xcarchive`
- `artifacts/stage5/Alua-2.1-build5-BACKEND-0004-REQUIRED.ipa`
- `artifacts/stage5/backend-stage2-stage3-source.tar.gz`

Это development RC для зарегистрированных устройств, не App Store/TestFlight upload. На физические телефоны сборка не устанавливалась. В Release сохранён существующий production URL; поэтому устанавливать этот RC до согласованного backend upgrade нельзя.

## 8. Физические проверки

Подробная инструкция: `docs/stage5/RELEASE_CHECKLIST.md`; воспроизведение изолированной QA: `docs/stage5/QA_REPRODUCTION.md`. На обоих iPhone нужны восстановление существующего enrollment, изолированный прогресс, resume, Airplane Mode/reconnect, hidden/unhide, Book search, настоящий Lock Screen tap и VoiceOver чтение/фокус. Крупный Dynamic Type и небольшие размеры проверены автоматически и реальными снимками; реальный VoiceOver walkthrough не выдается за выполненный.

## 9. Oracle и совместимое обновление

Production baseline: `20261029_0002`. До установки iOS потребуются существующие аддитивные `20261030_0003` и `20261031_0004`, полный backend/content bundle и проверка Stage 3 endpoints. Перечень файлов/контрольные суммы: `docs/stage5/release/backend-files.sha256`.

Порядок: подтверждённый внешний backup и restore test → согласованное backend обновление 0003/0004 → auth/legacy/Stage 3 smoke tests → первый физический iPhone → второй. Никаких миграций/deploy на Oracle в этой задаче не выполнялось.

Откат приложения сохраняет backend на 0004, историю, совместимые endpoints, App Group и Keychain. Перед откатом требуется опустошить offline queue. Предпочтителен подписанный forward-fix. Не удалять приложение и не выполнять destructive Alembic downgrade ради rollback.

## 10. Реальные ограничения и блокеры окончательного production release

Технические ограничения:

- WidgetKit определяет фактическое время перерисовки; старый видимый кадр может задержаться. Авторизованный resolver заново проверяет due/learner/срок и не засчитывает устаревший вопрос.
- Сохранён существующий auth contract: cold launch без сети требует восстановления связи для проверки профиля. Durable queue при этом остаётся на диске; полного offline-first и обхода авторизации не добавлено.
- Проверки на simulator не подтверждают реальное поведение Face ID/Lock Screen authentication, радиосети, физического VoiceOver и установки development profile. Эти пункты остаются ручными gates.
- Первый полный UI test имеет зафиксированное падение на селекторе Book после успешного 30/30. Исправленный Book flow проверен отдельным успешным прогоном; весь fresh-course тест с нуля повторно не запускался.

Каталог остаётся текущим editorial AI review / human_review_pending для закрытого использования Alua; независимая преподавательская проверка не заявляется. Development RC не является App Store/TestFlight публикацией.

Релизные блокеры:

1. **Внешний автоматический backup и успешное восстановление не подтверждены.**
2. Production backend пока Stage 1; Stage 2/3 migrations и совместимый deployment ещё не выполнены.
3. Проверка обоих физических iPhone и ручной VoiceOver walkthrough ещё необходимы.

Локальный QA server остановлен, временная PostgreSQL cluster и metadata удалены. 167 защищённых backend/auth/entitlement/AppGroup файлов совпали с исходной локальной baseline (`preservation.txt`).

Локальный RC не означает завершённый production release. Commit/push и любые изменения FLORA не выполнялись.
