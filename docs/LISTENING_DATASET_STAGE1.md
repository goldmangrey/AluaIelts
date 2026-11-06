# Listening Dataset — проверка 2026-11-05

Текущая ревизия существующего `listening_v1`; отдельный датасет не создавался. Все 72 теста имеют номера 1–40, ключи и доступные поля. Полнота не равна независимой верификации.

| Метрика | Результат |
|---|---:|
| Verified | 6/72 |
| Preliminary | 66/72 |
| Ungraded / Unavailable | 0 / 0 |
| Вопросы / доступные поля / ключи | 2880 / 2880 / 2880 |
| Независимо проверенные вопросы | 292/2880 |
| Независимо проверенные ключи | 960/2880 |
| Тесты с 40 проверенными ключами | 24/72 |

## Исправления и происхождение

- Восстановлены 16 позиций: Cambridge 04 T1 Q34; 06 T2 Q6–10; 14 T3 Q1–10. Существующие ID, Part и номера сохранены.
- Cambridge 04 Q34: [оригинальный скан](https://www.hasanboy.uz/wp-content/uploads/2018/06/Cambridge-Practice-Tests-for-IELTS-4.pdf), PDF p.12 явно печатает 34; дефектная локальная перепечатка печатала 43.
- Cambridge 06 T2: [читаемая таблица](https://karatalk.com/wp-content/uploads/Cambridge-IELTS-6.pdf), PDF p.29; восстановлены заголовки колонок.
- Cambridge 14 T3: [вторичная репродукция](https://voxcel.org/wp-content/uploads/2025/10/CAMBRIDGE-LISTENING-BOOK-14-TEST-3.pdf), PDF p.1; поля доступны, но источник не повышен до source_verified. Для Verified нужен читаемый первичный источник.
- Пользовательский TXT 04–18 сохранён в `backend/scripts/listening_dataset/sources/answer_keys_04_18.txt`. Это веб-компиляция, как указано в её собственном заголовке; добавлены только отсутствовавшие 160 ключей Cambridge 04 без флага независимой проверки. Остальные существующие ключи не перезаписаны.
- Ключи Cambridge 19 (PDF p.119/121/123/125) и 21 (p.118/120/122/124) сверены визуально с локальными PDF: 320 новых проверенных позиций. Полностью сверены материалы T1 обеих книг: 80 вопросов. Хеши и адресные записи — в `source_reviews.json`; ключевые изображения приватные.
- Исправлены single-position Choose TWO (04 T3 Q38/Q40), сохранены исходные требования обоих вариантов.
- Grading: четыре точных официальных postcode с пробелом теперь проходят лимит одного ответа (10 T2 Q3, 11 T2 Q3, 12 T8 Q8, 18 T1 Q1); альтернативы с запятой тысяч обрабатываются без разрешения неоднозначных составных ответов.

## Что ещё требуется

Для 48 тестов книг **04–08, 10–11, 13, 15–18 (все T1–4)** нужна независимая сверка оставшихся ключей и каждого вопроса/материала с первоисточником. Для ещё 18 тестов ключи уже проверены, но не завершена сверка всех вопросов: **09 T1–3; 12 T6–8; 14 T2–4; 19 T2–4; 20 T1–3; 21 T2–4**.

Три неоднозначные строки остаются без автоматической оценки: **06 T1 Q7** (`10(am),4.30(pm)`), **06 T1 Q19** (`Monday,Thursday`), **11 T1 Q2** (`(£)115 / a/one hundred(and)fifteen`). Нужны адресные правила по оригиналу; статус Preliminary не скрывает это. **14 T3 Q1–10** дополнительно требует читаемого первичного материала вместо вторичной репродукции.

## Проверки

- Importer contracts: 24 PASS; backend Listening/Reading/auth: 32 PASS; дополнительные grading/all-72 проверки: 3 PASS.
- Reading release: 42 PASS. Listening real-backend browser: 36 сценариев Chromium/WebKit/desktop/mobile пройдены (30 основным запуском, 6 после исправления проверки сохранения в тесте). Catalog four-mode regression: 6 PASS.
- Validator с проверкой входных хешей: PASS. Повторный импорт: все 2084 выходных файла побайтово идентичны.
- 72 IDs; 40 номеров/ключей у каждого; варианты, лимиты, поля, assets/хеши; ключи и QA не попадают в публичную проекцию. Строгий editorial gate остаётся FAIL для 66 Preliminary по указанным причинам.
- Каталог использует внутренний `content_mode`: verified без бейджа; остальные Preliminary/Ungraded/Unavailable, blocked сохраняет блокировку запуска. Отсутствие бейджа не определяет статус.

## По каждому тесту

| Тест | Вопросы | Поля | Проверено вопросов | Ключи | Проверено ключей | Статус |
|---|---:|---:|---:|---:|---:|---|
| cambridge-04-test-01 | 40 | 40 | 10 | 40 | 0 | Preliminary |
| cambridge-04-test-02 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-04-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-04-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-05-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-05-test-02 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-05-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-05-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-06-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-06-test-02 | 40 | 40 | 5 | 40 | 0 | Preliminary |
| cambridge-06-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-06-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-07-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-07-test-02 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-07-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-07-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-08-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-08-test-02 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-08-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-08-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-09-test-01 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-09-test-02 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-09-test-03 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-09-test-04 | 40 | 40 | 40 | 40 | 40 | Verified |
| cambridge-10-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-10-test-02 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-10-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-10-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-11-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-11-test-02 | 40 | 40 | 1 | 40 | 0 | Preliminary |
| cambridge-11-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-11-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-12-test-05 | 40 | 40 | 40 | 40 | 40 | Verified |
| cambridge-12-test-06 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-12-test-07 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-12-test-08 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-13-test-01 | 40 | 40 | 5 | 40 | 0 | Preliminary |
| cambridge-13-test-02 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-13-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-13-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-14-test-01 | 40 | 40 | 40 | 40 | 40 | Verified |
| cambridge-14-test-02 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-14-test-03 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-14-test-04 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-15-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-15-test-02 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-15-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-15-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-16-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-16-test-02 | 40 | 40 | 11 | 40 | 0 | Preliminary |
| cambridge-16-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-16-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-17-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-17-test-02 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-17-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-17-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-18-test-01 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-18-test-02 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-18-test-03 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-18-test-04 | 40 | 40 | 0 | 40 | 0 | Preliminary |
| cambridge-19-test-01 | 40 | 40 | 40 | 40 | 40 | Verified |
| cambridge-19-test-02 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-19-test-03 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-19-test-04 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-20-test-01 | 40 | 40 | 10 | 40 | 40 | Preliminary |
| cambridge-20-test-02 | 40 | 40 | 10 | 40 | 40 | Preliminary |
| cambridge-20-test-03 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-20-test-04 | 40 | 40 | 40 | 40 | 40 | Verified |
| cambridge-21-test-01 | 40 | 40 | 40 | 40 | 40 | Verified |
| cambridge-21-test-02 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-21-test-03 | 40 | 40 | 0 | 40 | 40 | Preliminary |
| cambridge-21-test-04 | 40 | 40 | 0 | 40 | 40 | Preliminary |

## Production — 2026-11-05

- Штатный encrypted backup: `alua-20261105T175432Z.dump.age`, success; существующая внешняя копия по-прежнему не настроена. Backup workflow не изменён.
- Backend release: `/opt/alua/releases/listening-data-20261105`; копия активного релиза с заменой только `listening_v1` и `modules/listening/grading.py`. Все прежние assets сохранены. Python delta относительно предыдущего релиза — только grading. Без миграций.
- Frontend Worker: `5a93eac7-3f9f-43cb-8d3a-218d211251ee`. Сборка из HEAD плюс единственная правка каталога; pending Review V2/Reading изменения не опубликованы. OpenNext build и настоящий локальный workerd smoke прошли.
- Проверено: backend active/running; health, Listening/Reading/Login shells 200; защищённые API без токена 401. Загруженный серверный каталог: 6 verified / 66 preliminary, все позиции и хеши assets проверены.
- Counts и агрегированные полнострочные хеши `listening_attempts`, `listening_mutations`, `reading_attempts`, `reading_mutations` до/после идентичны. Production attempts для проверки не создавались; сохранённые результаты не пересчитывались.
- Откат без восстановления БД: убрать только `/etc/systemd/system/alua-api.service.d/zzzzzzz-listening-data-20261105.conf`, daemon-reload/restart alua-api; frontend предыдущая версия `5bd51390-d784-44bc-b930-d46c00728a02`. Предыдущий backend release сохранён.
- Git commit/push не выполнялись. Firebase, авторизация, Reading, Flora и production secrets не изменены.
