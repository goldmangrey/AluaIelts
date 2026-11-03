# Reading content integrity — source repair

Локальная сверка и восстановление, 2026-11-03. Без production-запросов, SSH, изменения production records и deployment.

## Результат

Проверены **72 экзамена, 613 групп, 2880 question positions, все 15 типов** Cambridge 04–21. Исходные **18 PDF и 18 TXT найдены локально**. Повторная ручная вычитка всех корректных экзаменов не выполнялась: использованы предыдущий аудит, точечная сверка подозрительных групп и полный автоматический прогон.

| Категория | Исходно | Итог |
|---|---:|---|
| A — Renderer | 7 | Общий Renderer fix предыдущего этапа сохранён; новых A не найдено |
| B — Dataset | 27 | **Все 27 REPAIRED** по исходным PDF |
| Дополнительный B | 1 | Cambridge 14 Test 2 Q14–18: **REPAIRED** |
| C — PDF review | 26 | **8 VERIFIED · 11 REPAIRED · 7 BLOCKED** |

Среди исходных C у 11 групп подтверждены и исправлены ошибки; 8 корректны (обычные слова `unclear`, `unreadable` и пример с пропуском ошибочно попадали под OCR-эвристику). Ещё 7 имеют нерешённые проблемы источника/меток и не объявлены корректными. B/C пересекаются в Cambridge 21 Test 4 Q27–32; количества категорий нельзя складывать как число уникальных групп.

Для новых private-practice запусков серверный каталог разрешает **69 экзаменов** (до ремонта — 63). Все 69 проходят локальный gate без блокирующих ошибок. **Полностью вычитанных и официально release-ready экзаменов по строгому статусу `ready` — 0**, как и до ремонта: доступность private practice не означает ручную сверку каждого слова/ключа всего экзамена.

Заблокированы существующим механизмом `content_status=blocked`:

- Cambridge 07 Test 2 — watermark перекрывает необходимый текст, нужен чистый скан.
- Cambridge 10 Test 1 — переплёт скрывает буквы Passage 1; метки Passage 2 восстановлены, но весь экзамен пока недоступен.
- Cambridge 20 Test 3 — оригинал Q22–23 содержит противоречие A–E / B–F, нужна авторитетная исправленная копия и подтверждение mapping ключа.

## Что изменено

Canonical source authoring хранится в `backend/scripts/reading_dataset/content_repairs.json` и существующем `paragraph_labels.json`; pipeline воспроизводимо собирает `backend/app/content/reading_v1/`. В JSON правок записаны исходные PDF, их SHA-256, страницы, причина, ожидаемый hash исходного фрагмента и статусы C. PDF сравнивались визуально на отрендеренных страницах; OCR использован как поисковый помощник, а не источник придуманных вариантов.

- Восстановлены полные тексты/порядок вариантов, prompts и constraints для 20 исходных B; исправлены 7 групп с потерянными метками абзацев. Отдельно восстановлена ранее пропущенная группа Cambridge 14 Test 2 Q14–18.
- Cambridge 04 Test 3 Q1–4: возвращены настоящие A–D для каждого вопроса; артефакт разбиения `S.K.I.` больше не становится вариантом I. Все четыре поля доступны в Renderer.
- Cambridge 12 Test 8 Q14–18: по PDF исправлен тип `matching_features` → `multiple_choice_single`; IDs, `single_select` и сохраняемые буквы не изменены.
- Cambridge 06 Test 2: A привязана к напечатанному «In fact, Newman…» на PDF 43, а не к начальному «A new study…».
- В Cambridge 14 исправлены проверенные OCR-артефакты контекста, повреждённая ссылка и повторённая source footnote. Дополнительная группа A–I восстановлена только после сверки реальных меток разделов на PDF 42–43.
- `repairs.py` отклоняет устаревший PDF/target hash, неподдерживаемое поле и изменение question ID/number/input type. Неустранимые C создают внутренний `source_required`; generation сохраняет блокировку экзамена.
- Пересобраны **25 exam JSON**, manifest, audit_report и corrections journal. **Все 72 answer key файла побайтово совпадают с исходными.** Question IDs, group IDs, номера, типы полей и answer mapping сохранены. Backend API/grading/Oracle/Firebase/Smart Translate/Exam UI не менялись в этом этапе.
- В существующих `backend/tests/test_reading.py` обновлены только ожидаемые количества доступных экзаменов 63→69 (и 62→68 после искусственного повреждения одного экзамена).

Public projections формирует прежний `ReadingCatalog.public_exam`; приватные ключи в браузер не передаются. Для недоступного нового запуска существующий каталог не выдаёт экзамен, UI показывает `Test unavailable` / `This test is currently unavailable for practice`. Диагностические коды не превращены в пользовательские варианты ответа. Существующие попытки и ответы не удалялись.

## Таблица сверки B/C

Номера страниц ниже — **1-based PDF page**, не обязательно печатная нумерация книги. Для строки Cambridge XX источник — локальный `ieltsbooks/Cambridge-IELTS-XX.pdf`. SHA-256 и отдельные записи source review находятся в authoring JSON. `BLOCKED` означает `source_required`, а не выполненную реконструкцию.

| Cambridge | Test | Passage | Questions | Original issue | Fix | Source page | Final status |
|---|---:|---:|---|---|---|---|---|
| 04 | 3 | 1 | 1–4 | B: Allowed answer has no corresponding option | Restore exact question stems and complete ordered options from PDF; correct OCR segmentation and allowed_values. | 78, 79 | **REPAIRED** |
| 04 | 3 | 3 | 27–31 | C: suspected_text_corruption | Original passage and task pages visually compared. Legitimate source wording triggered the automatic text heuristic; task material is present. | 88, 89, 90, 91, 92, 93 | **VERIFIED** |
| 04 | 3 | 3 | 32–36 | C: suspected_text_corruption | Original passage and task pages visually compared. Legitimate source wording triggered the automatic text heuristic; task material is present. | 88, 89, 90, 91, 92, 93 | **VERIFIED** |
| 04 | 3 | 3 | 37–40 | C: suspected_text_corruption | Original passage and task pages visually compared. Legitimate source wording triggered the automatic text heuristic; task material is present. | 88, 89, 90, 91, 92, 93 | **VERIFIED** |
| 06 | 2 | 1 | 1–5 | B: Referenced heading paragraph labels missing | Восстановлены печатные метки абзацев по точным anchors; без назначения по порядку. | 43 | **REPAIRED** |
| 07 | 1 | 1 | 10–13 | C: suspected_question_corruption | Restore individual completion prompts and instructions verbatim from PDF, preserving blank numbers and answer IDs. | 25 | **REPAIRED** |
| 07 | 2 | 1 | 1–4 | C: source_obscured_by_watermark | source_required: advertising watermark obscures necessary passage wording; need clean source. | 45 | **BLOCKED** |
| 07 | 2 | 1 | 5–10 | C: source_obscured_by_watermark | source_required: advertising watermark obscures necessary passage wording; need clean source. | 45 | **BLOCKED** |
| 07 | 2 | 1 | 11–13 | C: source_obscured_by_watermark; suspected_question_corruption | source_required: advertising watermark obscures necessary passage wording; need clean source. | 45 | **BLOCKED** |
| 08 | 3 | 1 | 1–3 | B: Allowed answer has no corresponding option | Restore exact question stems and complete ordered options from PDF; correct OCR segmentation and allowed_values. | 66 | **REPAIRED** |
| 08 | 3 | 1 | 7–10 | B: Individual question prompt contains another question/source block | Restore complete shared task and source answer bank with exact numbered blanks; remove duplicated/contaminated per-question OCR. | 67 | **REPAIRED** |
| 08 | 4 | 2 | 14–17 | B: Allowed answer has no corresponding option | Restore exact question stems and complete ordered options from PDF; correct OCR segmentation and allowed_values. | 94 | **REPAIRED** |
| 09 | 3 | 1 | 9–12 | B: Duplicate labels in effective question options | Restore complete shared task and source answer bank with exact numbered blanks; remove duplicated/contaminated per-question OCR. | 67 | **REPAIRED** |
| 09 | 4 | 2 | 20–23 | B: Duplicate labels in effective question options | Restore ordered bank and individual prompts from printed task; remove OCR fragments mistaken for additional labels. | 102 | **REPAIRED** |
| 09 | 4 | 2 | 24–26 | B: Individual question prompt contains another question/source block | Restore complete shared task and source answer bank with exact numbered blanks; remove duplicated/contaminated per-question OCR. | 103 | **REPAIRED** |
| 10 | 1 | 1 | 1–5 | C: binding_obscures_text | source_required: binding hides passage letters; need a legible source, not inferred reconstruction. | 9, 10 | **BLOCKED** |
| 10 | 1 | 1 | 6–8 | C: binding_obscures_text | source_required: binding hides passage letters; need a legible source, not inferred reconstruction. | 9, 10 | **BLOCKED** |
| 10 | 1 | 1 | 9–13 | C: binding_obscures_text | source_required: binding hides passage letters; need a legible source, not inferred reconstruction. | 9, 10 | **BLOCKED** |
| 10 | 1 | 2 | 14–21 | B: Referenced heading paragraph labels missing | Восстановлены печатные метки абзацев по точным anchors; без назначения по порядку. | 15 | **REPAIRED** |
| 10 | 2 | 1 | 1–7 | B: Referenced heading paragraph labels missing | Восстановлены печатные метки абзацев по точным anchors; без назначения по порядку. | 34, 35 | **REPAIRED** |
| 10 | 2 | 2 | 14–17 | B: Referenced passage paragraph labels missing | Восстановлены печатные метки абзацев по точным anchors; без назначения по порядку. | 37, 38 | **REPAIRED** |
| 10 | 3 | 1 | 1–4 | B: Referenced heading paragraph labels missing | Восстановлены печатные метки абзацев по точным anchors; без назначения по порядку. | 57 | **REPAIRED** |
| 10 | 3 | 2 | 14–18 | B: Referenced passage paragraph labels missing | Восстановлены печатные метки абзацев по точным anchors; без назначения по порядку. | 61 | **REPAIRED** |
| 10 | 3 | 3 | 27–31 | B: Duplicate labels in effective question options | Restore complete shared task and source answer bank with exact numbered blanks; remove duplicated/contaminated per-question OCR. | 66 | **REPAIRED** |
| 10 | 4 | 2 | 23–26 | B: Referenced passage paragraph labels missing | Восстановлены печатные метки абзацев по точным anchors; без назначения по порядку. | 85 | **REPAIRED** |
| 10 | 4 | 3 | 27–31 | B: Allowed answer has no corresponding option | Restore exact question stems and complete ordered options from PDF; correct OCR segmentation and allowed_values. | 91 | **REPAIRED** |
| 12 | 5 | 3 | 33–36 | B: Individual question prompt contains another question/source block | Restore complete shared task and source answer bank with exact numbered blanks; remove duplicated/contaminated per-question OCR. | 26 | **REPAIRED** |
| 12 | 6 | 1 | 4–9 | B: Duplicate labels in effective question options | Restore ordered bank and individual prompts from printed task; remove OCR fragments mistaken for additional labels. | 40 | **REPAIRED** |
| 12 | 7 | 3 | 32–36 | B: Allowed answer has no corresponding option | Restore exact question stems and complete ordered options from PDF; correct OCR segmentation and allowed_values. | 69 | **REPAIRED** |
| 12 | 8 | 2 | 14–18 | B: Duplicate labels in effective question options | Restore exact question stems and complete ordered options from PDF; correct OCR segmentation and allowed_values. Correct source-confirmed task classification from matching_features to multiple_choice_single; saved letters/IDs unchanged. | 85 | **REPAIRED** |
| 14 | 1 | 1 | 1–8 | C: suspected_text_corruption | Source-confirmed OCR correction in shared passage context; task pages compared and readable. | 16, 17, 18, 19 | **REPAIRED** |
| 14 | 1 | 1 | 9–13 | C: suspected_text_corruption | Source-confirmed OCR correction in shared passage context; task pages compared and readable. | 16, 17, 18, 19 | **REPAIRED** |
| 14 | 2 | 1 | 1–8 | C: suspected_text_corruption | Source-confirmed OCR correction in shared passage context; task pages compared and readable. | 38, 39, 40, 41 | **REPAIRED** |
| 14 | 2 | 1 | 9–13 | C: suspected_text_corruption | Source-confirmed OCR correction in shared passage context; task pages compared and readable. | 38, 39, 40, 41 | **REPAIRED** |
| 14 | 2 | 2 | 14–18 | B: OCR A–I → A–!; missing A–I controls and section labels E–I | Additional B missed by earlier audit: recover literal A–I range from PDF, with actual A–I passage sections; not inferred from keys. | 42, 43, 44 | **REPAIRED** |
| 14 | 3 | 2 | 14–20 | C: suspected_text_corruption | Source-confirmed OCR correction in shared passage context; task pages compared and readable. | 63, 64, 65, 66 | **REPAIRED** |
| 14 | 3 | 2 | 21–22 | C: suspected_text_corruption | Source-confirmed OCR correction in shared passage context; task pages compared and readable. | 63, 64, 65, 66 | **REPAIRED** |
| 14 | 3 | 2 | 23–26 | C: suspected_text_corruption | Source-confirmed OCR correction in shared passage context; task pages compared and readable. | 63, 64, 65, 66 | **REPAIRED** |
| 14 | 4 | 1 | 1–8 | C: suspected_text_corruption | Source-confirmed OCR correction in shared passage context; task pages compared and readable. | 82, 83, 84, 85 | **REPAIRED** |
| 14 | 4 | 1 | 9–13 | C: suspected_text_corruption | Source-confirmed OCR correction in shared passage context; task pages compared and readable. | 82, 83, 84, 85 | **REPAIRED** |
| 15 | 2 | 3 | 32–36 | B: Duplicate labels in effective question options | Restore complete shared task and source answer bank with exact numbered blanks; remove duplicated/contaminated per-question OCR. | 49 | **REPAIRED** |
| 16 | 1 | 2 | 14–20 | C: suspected_text_corruption | Original passage and task pages visually compared. Legitimate source wording triggered the automatic text heuristic; task material is present. | 22, 23, 24, 25 | **VERIFIED** |
| 16 | 1 | 2 | 21–24 | C: suspected_text_corruption | Original passage and task pages visually compared. Legitimate source wording triggered the automatic text heuristic; task material is present. | 22, 23, 24, 25 | **VERIFIED** |
| 16 | 1 | 2 | 25–26 | C: suspected_text_corruption | Original passage and task pages visually compared. Legitimate source wording triggered the automatic text heuristic; task material is present. | 22, 23, 24, 25 | **VERIFIED** |
| 16 | 2 | 3 | 27–30 | B: Allowed answer has no corresponding option | Restore exact question stems and complete ordered options from PDF; correct OCR segmentation and allowed_values. | 51 | **REPAIRED** |
| 17 | 3 | 3 | 36–40 | B: Duplicate labels in effective question options | Restore complete shared task and source answer bank with exact numbered blanks; remove duplicated/contaminated per-question OCR. | 64 | **REPAIRED** |
| 18 | 1 | 2 | 22–26 | B: Individual question prompt contains another question/source block | Restore individual completion prompts and instructions verbatim from PDF, preserving blank numbers and answer IDs. | 26 | **REPAIRED** |
| 18 | 3 | 3 | 27–30 | B: Allowed answer has no corresponding option | Restore exact question stems and complete ordered options from PDF; correct OCR segmentation and allowed_values. | 74 | **REPAIRED** |
| 20 | 3 | 2 | 22–23 | C: source_option_label_anomaly | source_required: original prints A–E instructions but B–F options with stem labelled A; authoritative corrected source/key mapping required. Keys unchanged. | 94 | **BLOCKED** |
| 21 | 4 | 2 | 14–19 | B: Duplicate labels in effective question options | Restore complete shared task and source answer bank with exact numbered blanks; remove duplicated/contaminated per-question OCR. | 88 | **REPAIRED** |
| 21 | 4 | 3 | 27–32 | B+C: Duplicate labels in effective question options; suspected_text_corruption | Restore complete shared task and source answer bank with exact numbered blanks; remove duplicated/contaminated per-question OCR. | 90, 91, 92 | **REPAIRED** |
| 21 | 4 | 3 | 33–36 | C: suspected_text_corruption | Original passage and task pages visually compared. Legitimate source wording triggered the automatic text heuristic; task material is present. | 90, 91, 92, 93, 94 | **VERIFIED** |
| 21 | 4 | 3 | 37–40 | C: suspected_text_corruption | Original passage and task pages visually compared. Legitimate source wording triggered the automatic text heuristic; task material is present. | 90, 91, 92, 93, 94 | **VERIFIED** |

## Проверки

- Существующий Python generation/validator: **PASS**, 72 exams / 216 passages / 2880 questions / 2880 answers / 144 schema validations / 36 source hashes / 60 PNG assets. Ошибок структуры, ссылок, SHA-256 или размеров изображений нет. Строгий `release_ready` не повышался искусственно.
- Постоянный быстрый gate: `node web/scripts/check-reading-integrity.mjs`. Он использует настоящий серверный public projection, `parseExam`, `questionIntegrity`, React SSR `QuestionGroup`; проверяет все 613 групп, все 15 типов, позиции 1–40, IDs, options/allowed values, paragraph labels, blank/table/image references и один answer anchor на позицию. Валидные исходные image-fallback задания проверяются как image tasks, а не как отсутствующий typed bank.
- Дополнительный `--baseline /path/to/previous/dataset` проверяет неизменность всех answer key bytes и question/group/input mapping. Итог: **0 ошибок**. На исходном dataset отрицательный контроль выявляет **68 диагностик**, gate завершает процесс с ненулевым кодом. Это диагностики, не число уникальных групп.
- Все исходные 27 B + дополнительный B после восстановления проходят runtime integrity guard. Проверенные C записаны отдельно; исходная осторожная текстовая эвристика продолжает выдавать warnings для корректных слов — они не скрыты глобально.
- Защита overlays проверена адресно: повторное применение к изменённому target отклоняется, не перезаписывает новый контент.
- **Настоящий локальный Renderer в Chromium**, desktop 1440×900 и mobile 390×844: Cambridge 04 Test 1 Q9–13 / View options / Escape; Cambridge 04 Test 3 Q1–4 (по 4 radio, выбор D); Cambridge 12 Test 6 Q4–9 (банк исследователей, выбор B); Cambridge 14 Test 2 Q14–18 (9 кнопок A–I); Cambridge 18 Test 1 Q22–26 (completion input); корректные source-image и inline notes примеры. IDs/выбранные значения проверены. Это локальная компонентная интеграция с реальными исправленными данными, **не authenticated production E2E и не backend autosave тест**. Production attempts не создавались/не завершались.
- Frontend: **typecheck PASS · lint PASS · build PASS**.
- Targeted existing backend tests: **3 PASS, 6 deselected** — `test_catalog_and_all_grading_types`, `test_alternatives_and_unordered_semantics`, `test_catalog_isolates_invalid_exam`. Существующие тесты исполнялись без PostgreSQL fixture/production connection; lifecycle E2E не запускался.

Представитель каждого из 15 типов проходит parser и SSR; полный список первых представителей выводит gate. Типов после исправления классификации по-прежнему 15 (MC single 73 группы, matching features 47; остальные количества сохранены).

Скриншоты адресной локальной проверки: `/tmp/alua-repair-pages/qa-desktop-0.png` … `qa-desktop-6.png` и `qa-mobile-0.png` … `qa-mobile-6.png`. Рендеры источников и временные QA-скрипты оставлены только в `/tmp`, не в репозитории.

## Ограничения и доставка

Отсутствующих книг PDF нет. Для 07/2 и 10/1 нужны более читаемые оригиналы; для 20/3 — авторитетное исправление печатной аномалии, не догадка по ответам. Локальный PDF Cambridge 09 не содержит ключей: существующие TXT keys сохранены без изменений, их source verification остаётся ограниченным. Остальные прежние warnings о полной вычитке, title review и визуальной проверке нетронутых crops не объявлены устранёнными.

**Активные и завершённые attempts используют сохранённый snapshot**. Обновление каталога исправит только новые попытки; уже сохранённые повреждённые snapshots сами не изменятся. Миграция старых attempts не выполнялась — потребует отдельного согласованного решения с сохранением answers и revision mapping. В частности, продолжение старой попытки может показывать прежний контент.

Безопасный порядок доставки (не выполнялся):

1. Проверить diff authoring и source provenance; локально собрать dataset существующим `generate.py`, затем запустить Python validator и frontend gate. Нужны локальные источники и зависимости существующего pipeline.
2. Доставить на backend **единый собранный `backend/app/content/reading_v1` artifact** вместе с pipeline/provenance; не смешивать exam JSON и manifest разных revisions. Текущая revision: `02aae2c9dfda0b052f8835311af6ce6cc5856dffb3ae677f7d983a84a5a099b9`.
3. Перезапустить backend workers / существующий процесс, чтобы сбросился `get_catalog()` cache. Данные находятся в файловом каталоге; **Oracle migrations и изменение production records не требуются**. Отдельный Cloudflare frontend deployment для этих данных не нужен.
4. Подтвердить 69 доступных новых экзаменов, три исключённых и корректность Q1–4 в новом snapshot Cambridge 04 Test 3 в staging; production попытку ради проверки не создавать.
5. Rollback — предыдущий цельный content artifact и перезапуск процесса; snapshots/ответы старых попыток остаются неизменными.

Локальные изменения подготовлены; commit, push и deployment не выполнялись. Полную ручную вычитку всех 72 экзаменов и отсутствие любого возможного OCR-дефекта эти проверки не доказывают.
