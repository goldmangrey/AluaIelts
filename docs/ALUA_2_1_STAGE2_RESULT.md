# Alua 2.1 — этап 2 (S3), локальная реализация

Oracle/SSH, production, авторизация, Keychain, устройства, backup, FLORA не изменялись. Commit/push/deploy не выполнялись.

## Функциональность

- `GET /api/v1/learning-quality/diagnostic`, `POST .../diagnostic/answers`: 12 оригинальных вопросов от базовых до продвинутых, лексика в контексте, грамматика и два коротких фрагмента Reading. Каждый ответ (включая «не знаю») сохраняется с блокировкой записи. Повтор отправки идемпотентен; изменение уже сохранённого ответа — 409. Ключи правильных ответов не выдаются клиенту. Результаты независимы для каждого learner.
- Результат — приблизительная сложность курса A1–C1 и пробелы по темам, не официальный CEFR/Band. Профиль и declared current_level не переписываются. Learn содержит добровольную стартовую проверку; выход сохраняет ответы. Новые словарные подборки учитывают результат; уже созданный урок текущего дня сохранён. Грамматический curriculum автоматически через старые узлы не перескакивает.
- `POST .../items/{item_id}/actions`: known/unknown ставят на проверку без mastered/evidence; hide/unhide изменяют только предпочтение learner; report сохраняет canonical item ID, тип, комментарий и UUID. Known попадает в кандидаты следующих создаваемых review sessions, без нового SRS.
- На карточках новой подборки Learn видны «Уже знаю», «Скрыть», «Ошибка в карточке». Ошибка отправляется с типом и необязательным комментарием. Скрытые карточки исключены из будущих подборок, ответов API существующих review sessions, quick recall и счётчиков; история остаётся.
- «Не знаю» в vocabulary review отправляет существующий again. В grammar exercises явный unknown сохраняет answer_status=unknown, outcome=0, is_correct=false, topic_id (существующий grammar lesson ID), exercise_type. Успешное воспоминание не засчитывается.
- `GET .../grammar-topics`: агрегация существующих exercise answers + sessions, включая старые записи. Слабая тема: >=3 попытках, >=2 ошибках и доле ошибок >=50%; именованные константы. Названия и статистика тем доступны на экране проверки.
- Text answers поддерживают явные accepted_answers и однозначные сокращения (don't/do not и т. п.). Неоднозначные 's/'d не раскрываются автоматически. Context recall скрывает выражение без учёта регистра; для другой грамматической формы используется обратная проверка перевода, без показа ответа.

## Данные и совместимость

Аддитивная Alembic revision `20261030_0003` после `20261029_0002`: только таблица learning_quality с PK (learner_id, key) и JSON payload. Ключи: diagnostic:v1, item:<canonical_id>, report:<UUID>. Learner ID, профили и учебная история не изменяются. Новые поля exercise attempt имеют defaults для старых записей.

Миграция применялась только в изолированных локальных тестовых PostgreSQL. При будущей интеграции нужен additive upgrade до запуска нового backend. Downgrade этой revision намеренно сохраняет таблицу/историю; откат приложения не требует удаления данных. Безопасную авторизацию этапа 1 откатывать нельзя.

Widget schema v5, алгоритм SRS, app identity, Keychain service/account, App Group сохранены.

## Контент: результаты и ограничения

Автоматически просмотрено **11 196** единиц. 10 878 без примера, 9 962 без определения, 6 196 без уровня. 475 групп совпадающих термов — не все дубли ошибочны: возможны разные значения/части речи.

318 записей имеют определение, пример и уровень. Для них выполнен редакторский просмотр ассистентом: смысл, перевод, часть речи, контекст, повторы и пригодность первого курса. **300 допущены в локальную первоначальную выдачу**, 18 исключены как повторы/излишне специальные темы. Остальные 10 896 записей не попадают в новые подборки. Повторения ранее изученного контента сохраняются.

Исправления хранятся отдельно в initial_pool_v1.json, без изменения стабильных ID и исходного lexicon. Например: course → «учебный курс», sentence в данном контексте → «приговор», rest как глагол → «отдыхать». Устранены смешанные noun/verb переводы, British practise согласовано с примером. Непроверенная импортная IPA не показывается для первоначального пула. C2 в этой подборке заменено внутренней сложностью C1 — редакционная оценка, не официальная калибровка.

Пул: A1 40, A2 48, B1 55, B2 74, C1 83. Типы: 208 слов, 10 upgrades, 71 phrase, 9 phrasal verbs, 2 collocations. Совпадающих термов нет. Начинающему не подмешиваются B2/C1 upgrades ради заполнения квоты.

**Независимых человеческих языковых проверок: 0; все 300 ожидают независимого review.** Происхождение/права существующего alua_legacy_v1 не подтверждены внешним аудитом. Нельзя называть результат «300 слов, проверенных преподавателем». Автоматические проверки подтверждают структуру, не языковую правильность. CSV содержит 318 кандидатов, итоговые поля и статусы.

300 — общий пул разных сложностей, не 300 на каждый уровень. Для A1 доступны 88 A1/A2 единиц; бюджет до 30 новых/день может исчерпать их раньше двух недель. Выдача сокращается вплоть до нуля новых слов, повторения продолжаются, непроверенного fallback нет. Расширение начального пула и уменьшение ежедневной нагрузки остаются контентной работой / задачей планировщика этапа 3.

Воспроизведение аудита из backend: `.venv/bin/python -m scripts.lexicon.audit_initial_pool`.

## Изменённые файлы этапа 2

Backend (пути относительно backend):
- app/api.py, app/db/models.py;
- alembic/versions/20261030_0003_learning_quality.py;
- app/modules/learning_quality/{__init__,questions,repository,router}.py;
- app/modules/vocabulary_review/{lexicon_repository,selector,service}.py;
- app/modules/exercises/{models,schemas,service,grader}.py;
- app/content/vocabulary_v2/initial_pool_v1.json;
- scripts/lexicon/audit_initial_pool.py;
- tests/test_learning_quality.py;
- tests/test_household_bootstrap.py: только ожидаемое количество защищённых маршрутов 48 → 52.

SwiftUI (пути относительно frontend/Alua):
- Services/LearningQualityService.swift, Services/ExerciseService.swift;
- Features/LearningQuality/{DiagnosticView,CardActionsView}.swift;
- Features/Learn/LearnView.swift, Navigation/MainTabView.swift;
- Features/Exercises/{ExerciseSessionStore,ExerciseSessionView}.swift;
- Features/Vocabulary/VocabularyReviewSessionView.swift;
- frontend/Alua.xcodeproj/project.pbxproj: новые файлы зарегистрированы XcodeGen.

Документы: этот отчёт, docs/stage2/content_summary.json, docs/stage2/content_review.csv.
Ранее существовавшие многочисленные локальные изменения не сбрасывались.

## Проверки

- 3 существующих backend integration tests: авторизация маршрутов, сохранение профилей/прогресса, цепочка curriculum → plan → vocabulary → review → widget v5.
- 3 новых PostgreSQL integration tests: независимые A1/C1 и реально разные подборки, сохранение/повтор диагностики, known без mastery, hide без потери history, изоляция learner/report idempotency, unknown=0 и порог слабой темы.
- 1 content regression test: 300 уникальных термов; 14 последовательных подборок без повторного введения/непроверенного fallback; допустимые сокращения; context recall без утечки ответа.
- iOS simulator build и 2 существующих XCTest. API_BASE_URL для тестов localhost:9, не production.
- Ruff для изменённых backend-модулей; воспроизводимый content audit.

Новые регрессионные тесты сохранены намеренно для дальнейшей интеграции. Временных тестовых файлов нет. Физические iPhone и production migration/deploy не проверялись и не выполнялись.

## Что осталось

Независимый language/rights review, расширение начальных уровней до полной двухнедельной нагрузки, ручной UX-прогон на iPhone. Диагностика — короткая эвристика без listening/writing/speaking. Слабые темы агрегируются по всей сохранённой истории без модели забывания. Новый Today/Lesson Player, новый SRS и IELTS engine не разрабатывались.
