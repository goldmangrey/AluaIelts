# Alua 2.1 — Stage 4: SwiftUI redesign

Дата: 2026-10-29, Asia/Almaty. Реализация выполнена локально поверх Stage 3. Commit, push, Oracle и production deploy не выполнялись.

## Структура приложения

Ровно три постоянные вкладки: **Сегодня → Моя книга → Прогресс**. Настройки доступны через gear вверху каждой вкладки. Урок и основное повторение открываются полноэкранно без TabBar. Книга, карточка, отдельный день/тема, диагностика и грамматика используют NavigationStack.

Грамматика, диагностика и практика существующего daily plan доступны со страницы «Сегодня». Совместный прогресс сохранён как вторичный переход из Settings; отдельной вкладки Partner больше нет. Существующие deep links vocabulary / grammar / practice / review / partner продолжают обрабатываться; App Group и widget contract не менялись.

## Изменённые файлы

Новые:
- `frontend/Alua/Core/DesignSystem/Components/StudyComponents.swift`: небольшой набор общих компонентов — primary button style, страница с прокруткой, строка перехода, кнопка закрытия, варианты ответа, состояния загрузки и синхронизации.
- `frontend/Alua/Features/Study/StudyPresentation.swift`: read-only представление существующих данных, фильтрация книги и подписи статусов. Никакого нового SRS или persistence.
- `frontend/Alua/Features/Study/StudyLessonView.swift`: Today-блок, ежедневный урок, паузы и завершение, основное повторение, учебный контент карточки.
- `frontend/Alua/Features/Study/StudyBookView.swift`: три режима книги, списки дней/тем, карточка, восстановление скрытого и report.
- `frontend/Alua/Features/Study/StudyProgressView.swift`: реальные показатели программы, темы, диагностика и слабые грамматические темы.
- `frontend/AluaTests/Stage4PresentationTests.swift`: проверки UI-проекции, поиска/фильтров, durability 18/30 и отрисовки настоящих SwiftUI-экранов.
- Этот отчёт.

Обновлены:
- `Core/DesignSystem/AluaColors.swift`, `Components/PrimaryButton.swift`, `Components/AluaProgressBar.swift`.
- `Navigation/AppTab.swift`, `Navigation/MainTabView.swift`.
- `Features/Today/TodayView.swift`, `Features/Study/StudyView.swift` (модели и StudyStore оставлены; старые views заменены отдельными файлами).
- `Features/LearningQuality/DiagnosticView.swift`, `Features/Settings/SettingsView.swift`, `Features/Auth/ProfileSelectionView.swift`, `Features/Profile/EditProfileView.swift`, `Features/Root/RootView.swift` (только интерфейс).
- `Features/Grammar/GrammarLibraryView.swift`, `GrammarStageView.swift`, `GrammarLessonView.swift`.
- `Features/Exercises/ExerciseSessionView.swift`, `DailyPlanActivityView.swift`.
- `Features/Vocabulary/VocabularyReviewSessionView.swift`: стиль прежних review-сессий и явное ручное продолжение после проверки.
- `frontend/Alua.xcodeproj/project.pbxproj`: добавлены новые source/test members через существующий XcodeGen specification.

## Визуальный подход

Светлый фон, нейтральная поверхность #F5F5F7, чёрный основной CTA, системный SF Pro и SF Symbols. Тонкий progress bar, крупный term, свободные отступы, обычные списки вместо сеток. Secondary text немного темнее исходного #767676 для контраста на вторичной поверхности. Убраны градиент и 3D-переворот в старом review. Новых декоративных анимаций, картинок, наград или игровых показателей нет.

Переиспользованы существующие AluaTypography, AluaSpacing, AluaCard, GrammarStore, CurriculumStore, ExerciseSessionStore, LearningQualityService, StudyStore и API-контракты. Старые Learn/dashboard и общий analytics ProgressView исключены из основного маршрута; сервисы и данные не удалены.

## Today и урок

Today показывает `alua.`, дату Asia/Almaty, текущий учебный день, реальные X/30, один главный CTA, повторения и переход к книге. Без диагностики курс доступен; проверка предлагается вторичным переходом.

Состояния: начатый/не начатый день; 10/20; 30/30; все 50 дней; нулевая очередь повторений; backlog; offline и ошибка первоначальной загрузки. Если backend уже вернул следующий, ещё недоступный день с 0/30, Today показывает предыдущий завершённый день и объясняет доступность следующего завтра. Данные сервера не переписываются ради отображения.

Урок показывает одну карточку, оба перевода, definition, пример и usage note. «Дальше» — основной CTA; «Уже знаю»/«Не знаю» отдельные действия; hide/report в меню. После 10/20 — спокойная пауза с продолжением, выходом и короткой проверкой. После 30 — завершение, число обработанных единиц, ожидающие повторения при наличии данных и открытие этого дня в книге. Завершение не названо mastery. При смене карточки прокрутка возвращается к началу; повторный быстрый tap по уже обработанной карточке не продвигает локальный экран второй раз.

Исходные durable queue, UUID, atomic save и сетевые методы StudyStore не изменены. Один общий store обслуживает все три вкладки. Sync выполняется при активации приложения и периодически в активной сцене, включая время полноэкранного урока. Недоставленные ответы видны в предупреждении, которое поясняет, что они сохранены на iPhone и приложение не следует удалять до отправки.

## Повторение

Stage 3: один term, варианты значения, выбор, отдельная кнопка «Проверить»/«Не знаю», правильный ответ и ручное «Дальше». Нет автоперелистывания. Порция до 10 или одна карточка из книги. Ответ уходит через прежнюю очередь; никакой mastery за открытие.

Старые review-ссылки продолжают отображать `frontTerm`/`prompt` всех прежних типов и использовать существующие again/hard/good ratings. Для них сохранена самопроверка; открытие правильного ответа не записывает рейтинг. Дальше нужно явно оценить вспоминание и продолжить. Существующее системное произношение сохранено только там, где оно уже было. В новые карточки IPA/аудио не добавлялись.

## Моя книга

Все 50 дней с тематическими названиями, X/30 и состояниями; все 50 тем с числом изученных карточек; общий список с English/Russian search и четырьмя фильтрами. Поиск действует по изученной библиотеке и из режима дней/тем. При accessibility-размерах segmented control заменяется нативным menu picker, чтобы подписи помещались.

Списки читаемые и плотные; будущие дни не считаются пройденными. Одна карточка может появляться в нескольких темах, но вся история остаётся общей. Карточка показывает актуальный статус из store, учебные данные, повторение, hide/unhide и report. Raw source IDs и редакторские поля на учебных экранах не выводятся. Данные книги не сбрасываются при смене дня или завершении программы.

## Прогресс и вторичные экраны

Показаны завершённые учебные дни / 50, впервые изученные ID текущего курса / 1500, server-reported retained текущего курса, все ожидающие повторения. Legacy-контент вне 1500 не раздувает счётчик курса. Есть темы и результат диагностики; слабые темы берутся из существующего learning-quality API, а не выводятся из backlog. При отсутствии данных — пустые состояния; фиктивных streak/IELTS Band нет.

Диагностика: выбираемый вариант и явная отправка, сохранение текущего контракта, единый стиль вопросов и результата. Settings/profile/enrollment локализованы и используют те же поверхности/типографику. Техническая информация устройства находится в DisclosureGroup. Grammar/exercises сохранили рабочие маршруты, получили общую палитру и понятные русские служебные подписи.

## Проверки

- iOS Simulator Debug build: **BUILD SUCCEEDED**.
- `StudyStoreTests` + `Stage4PresentationTests`: финальный прогон **6 tests passed**, без ошибок; **TEST SUCCEEDED**, 72.630 s вместе со сборкой/запуском simulator.
- Проверены: ровно три tab cases; проекции Today 0/10/18/20/30 и 50 дней; завершённый день при заблокированной следующей подборке; отсутствие подмены retained числом introduced; поиск по English/Russian; все фильтры; multi-topic identity; восстановление 18/30; сохранение всех 30 UUID при offline; второй learner без чужой очереди; повтор прежнего UUID после потерянного acknowledgement.
- Реальные views отрисованы в UIHostingController: Today, Lesson, Book, карточка, Progress, Review. Есть проверка отсутствия горизонтального overflow в UIScrollView. Снимки просмотрены визуально. Это тестовые payloads внутри XCTest, а не демонстрационные экраны или фиктивные данные приложения.
- Ширины 320/375/390 pt; accessibility Dynamic Type, включая карточку и Today. Используются semantic fonts, ScaledMetric, VoiceOver labels для icon controls/progress, состояния выбора, текстовые статусы вместо цветовых обозначений, min 44 pt actions, safe areas и вертикальная прокрутка.
- Перед изменениями сохранены контрольные суммы защищённых файлов. Backend Python/content, AuthSession, DeviceTokenStore, AluaShared, AluaWidgets и project.yml остались побайтово прежними. В diff Xcode project относительно начала Stage 4 нет изменений signing, team, provisioning, entitlements или API URL.

Команда тестов:

```sh
cd frontend
xcodebuild -project Alua.xcodeproj -scheme Alua \
  -destination 'platform=iOS Simulator,id=D2FF27EB-472E-4BC8-8551-571EDFBB07EF' \
  -derivedDataPath /tmp/alua-stage4-build CODE_SIGNING_ALLOWED=NO \
  -only-testing:AluaTests/StudyStoreTests \
  -only-testing:AluaTests/Stage4PresentationTests test
```

## Ограничения и следующий этап

- Полный физический walkthrough на двух подписанных iPhone и проверка VoiceOver жестами остаются перед выпуском. Автоматические render/layout тесты не заменяют эту проверку.
- Существующие AuthSessionTests в неподписанном simulator имеют известное ограничение Keychain -34018 из Stage 3. Безопасность не отключалась; signing/Keychain не менялись. Эти auth-тесты не выдаются за прошедшие в Stage 4.
- Старые review-сессии сохраняют прежний online/rating контракт; новый основной курс и повторение из книги используют durable queue Stage 3. SRS не модифицировался.
- Системный внешний вид navigation/search/TabBar зависит от версии iOS; собственного glassmorphism нет.
- Точная дата будущего повторения и отдельные lifetime retention totals недоступны в Stage 3 snapshot; UI их не выдумывает. Показан текущий `retained` по серверным статусам.
- Stage 5: виджеты и их согласованная презентация текущего учебного дня, очереди повторений и deep links. WidgetKit, App Group и contract v5 в этом этапе не изменены.
