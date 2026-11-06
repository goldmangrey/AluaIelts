# Listening: исчезновение исходных материалов — локальное исправление

## Конкретная причина

В `web/src/features/listening/workspace-questions.tsx` условие было:

```ts
const split = active.supporting_assets.length > 0;
```

Это же единственное поле использовалось для списка изображений. При пустом массиве source pane вообще не монтировалась, а workspace становился full-width. Текст источника/общие варианты переносились внутрь прокручиваемого списка вопросов, поэтому после перехода к вопросу часто оказывались выше viewport.

Однако `backend/scripts/listening_dataset/importer.py:765` намеренно записывает `group.supporting_assets = []` для `structured`-групп. Оригинальные страницы при этом остаются в `part.supporting_assets` (строка 1136). `structured` означает способ представления, а не отсутствие оригиналов. Кроме того, старое условие игнорировало `original_source_image`, question visual bindings, текстовый контекст и shared answer bank.

Реальный пример: Cambridge 14 Test 2 Part 1 имеет **две оригинальные страницы** в Part, но пустой массив изображений группы. До исправления форма Total Health Clinic не показывалась слева. Аналогично Cambridge 04 Test 1 Q1–4: Notes on Social Programme существует в PNG, но structured-группа теряла его.

## Исправление

- `source-material.ts` объединяет group assets, authoritative image blocks и question visual bindings. Если прямых ссылок нет, использует оригинальные страницы **того же Part**. Страницы других Parts/экзаменов не подставляются.
- Наличие материала учитывает также текст источника и общий answer bank. Full-width остаётся только для самодостаточной группы без отдельного материала.
- Изображения не фильтруются по `width`, `height`, presentation mode или необязательной metadata. Сами файлы не изменялись.
- Source pane не перемонтируется на каждой смене группы: одинаковые изображения сохраняют свои blob URLs. При смене группы сбрасывается только её scroll; при смене вопроса внутри группы материал остаётся.
- Текущий вопрос определяет согласованный Part и в workspace, и в верхней навигации, включая восстановление рассогласованного старого state.
- Обязательный, но отсутствующий оригинал даёт видимое предупреждение с Cambridge/Test/Part/Questions. Ошибка загрузки изображения даёт понятный текст и Retry image. Панель остаётся на месте.

Проверенные part→asset связи в настоящих JSON и оригинальные файлы существуют. Причина исчезновения — frontend interpretation, поэтому dataset, backend, БД, grading, Firebase и авторизация не менялись. CSS и premium-дизайн в рамках этого исправления не переделывались. Commit, push и deploy не выполнялись.

## Важное уточнение Cambridge 04

Оригинал Accommodation Request Form **сам содержит надпись Test 3**. В dataset это `cambridge-04-test-03`, Part 1 Q1–4. Cambridge 04 Test 1 содержит Notes on Social Programme и Weekend Trips. Подмена формы из Test 3 в Test 1 была бы ошибкой, поэтому проверены оба экзамена.

У Cambridge 04 Test 1 в текущем dataset отдельно отсутствует Q34 (`validation.missing_positions = [34]`), поэтому обычный backend запрещает старт всего экзамена. Этот существующий дефект не относится к исчезновению панели и не исправлялся изменением grading или данных. Его **реальные, неизменённые Part 1 JSON и PNG** проверены в настоящем Listening Workspace через read-only browser snapshot transport. Изображения загружаются из оригинальных dataset files, не нарисованы и не заменены. Записи попытки Cambridge 04 Test 1 в БД не создавались. На его screenshots предупреждение audio ожидаемо: read-only snapshot не имеет реального audio grant.

Cambridge 04 Test 3, Cambridge 14 Test 1 и Test 2 проверяются через обычные попытки и Listening API с настоящими JSON и исходными Cambridge images. Существующий runner подставляет только тестовую сессию в удаляемую копию frontend и короткое синтетическое аудио; исходные вопросы и изображения — настоящий dataset. Основные audio/lifecycle тесты выполняются отдельно с нормальным grant flow.

## Что проверено

**Результат:** 36/36 прежних V3 browser checks прошли; финальный отдельный прогон источников — 18/18. TypeScript, ESLint изменённых файлов (`--max-warnings=0`) и `git diff --check` прошли.

Матрица: Chromium и WebKit × desktop 1600×900, 1366×768, mobile 390×844.

- C04 T1: Q1–4 (notes), Q5–10 (table), возврат, reload.
- C04 T3: Accommodation Request Form Q1 → Q2; смена группы Q5; возврат Q1; reload. Blob изображения сохраняется внутри группы.
- C14 T1: Q1 → 11 → 12 → 13 → 15 → 21 → 1; соответствующие группы/Parts, shared options, возврат и reload.
- C14 T2: восстановлены Total Health Clinic Q1–10 и оригинальные страницы/общие варианты Q25–30.
- Проверяется фактическая видимость source pane, декодирование PNG/JPG, ожидаемые asset IDs и **SHA-256 байтов каждого показанного изображения** из browser blob относительно dataset. На desktop также проверяется, что source и questions видимы рядом, а не просто HTTP 200.
- Resize divider мышью с возвратом к 55/45; отсутствие page overflow.
- Повреждённые/неполные ссылки проверяются отдельно: image blocks, visual bindings, part fallback, shared bank, missing original, настоящая self-contained group и рассогласованный restored Part.
- Browser-проверка 404 → Retry image → декодированный оригинал и видимый fallback при удалённых metadata-ссылках. Эти повреждения вводятся только в тестовый response, dataset не изменяется.

Прежние V3 проверки: Play/Pause, seek ±5 sec, timeline, MP3/M4A, keyboard, autoplay/manual transition race, autosave/retry/conflict reconciliation, reload restore, flags/grid, Submit, Results, Review, independent scroll, divider и compact layout. Размеры сохранены: верх 129 px, footer 61 px; workspace 710 / 578 / 610 px соответственно.

## Скриншоты

`before/` сняты с V3 до изменения source selection. `after/` — исправленная реализация. Это реальные screenshots браузеров, не макеты. Имена включают engine, viewport и текущий экзамен/вопрос.

Рекомендуемые пары:

- `before/listening-chromium-1600-c14-t2-q1.png` → `after/listening-chromium-1600-c14-t2-q1.png`
- `before/listening-chromium-1600-c04-t1-q1.png` → `after/listening-chromium-1600-c04-t1-q1.png` (read-only snapshot из-за существующего missing Q34)
- `before/listening-webkit-mobile-c14-t2-q1.png` → `after/listening-webkit-mobile-c14-t2-q1.png`
- Accommodation: `after/listening-chromium-1600-accommodation-q1.png`, `after/listening-webkit-mobile-accommodation-reload.png`
- C14 T1 shared options: `after/listening-chromium-1600-c14-t1-q13.png`.

На mobile используется сохранённое переключение Source material / Questions; на desktop обе панели видны одновременно. Страницы Part сохраняются полностью и доступны через независимый scroll, включая страницы ниже первой.

## Повторный запуск

Из `backend`:

```sh
ALUA_RUN_LISTENING_BROWSER=1 .venv/bin/python -m pytest tests/test_listening_browser.py -q -s
```

Точечная проверка источников:

```sh
ALUA_RUN_LISTENING_BROWSER=1 ALUA_LISTENING_TEST_GREP='real dataset source visibility|source resolver preserves|source fallback and image retry' .venv/bin/python -m pytest tests/test_listening_browser.py -q -s
```
