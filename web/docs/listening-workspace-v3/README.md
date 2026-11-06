# Listening Workspace V3 — локальная проверка

Изменена только страница активной Listening practice и её компоненты/тесты. Reading, Home, Login, backend, БД, Firebase и grading не изменялись в рамках этой задачи. Оригинальные Cambridge images сохранены. Деплой не выполнялся.

## Размеры (CSS px)

Измерены через `getBoundingClientRect()`, со свёрнутой сеткой, без предупреждений о соединении.

| Версия / viewport | Header + player + Part navigation | Footer | Переключение материалов | Workspace |
| --- | ---: | ---: | ---: | ---: |
| V2, desktop 1440×900 (исходный прогон) | 277.5 | 164 | 0 | 458.5 |
| V2, mobile 390×844 | 287 | 115 | 49 | 393 |
| V3, desktop 1600×900 | 129 | 61 | 0 | 710 |
| V3, desktop 1366×768 | 129 | 61 | 0 | 578 |
| V3, mobile 390×844 | 129 | 61 | 44 | 610 |

Результаты V3 совпадают в Chromium и WebKit. Верх: header 36 px + player 48 px + Part navigation 44 px + border 1 px. Toolbar 60 px + border 1 px. На desktop при высоте 900 px задания получили дополнительно 251.5 px; на mobile — 217 px. При раскрытии сетки её высота вычитается из рабочей области: контент не перекрывается. Предупреждения об ошибках аудио и сохранения также занимают собственное место.

## Поведение

- Play/Pause, ±5 секунд, timeline и время расположены в одной строке.
- Единые вкладки Part переключают задания и аудиотрек. Ручное переключение трека оставляет его на паузе. Повторный выбор текущего Part сохраняет playback.
- Переход по номеру/стрелкам листает задания без смены текущего аудио; значок ♪ показывает аудиотрек.
- Сетка содержит все 40 номеров, зелёные отвеченные вопросы, золотую метку и выделение текущего вопроса. Выбор закрывает сетку, прокручивает и фокусирует вопрос, обновляет материалы.
- Desktop начинается с 55/45. Divider перетаскивается в пределах 30–70%; стрелки клавиатуры меняют ширину на 2%, Home/End задают границы, double-click возвращает 55/45.
- Колонки прокручиваются независимо. Структурированные группы без изображений используют доступную ширину. На mobile остаются вкладки Source material / Questions.

## Проверки

Результат: **30/30 основных browser checks + 12/12 целевых audio/lifecycle checks прошли**. TypeScript (`tsc --noEmit`), ESLint изменённых файлов (`--max-warnings=0`) и `git diff --check` прошли. Последний audio-прогон собран с финальным исправлением отмены autoplay.

Матрица: Chromium и WebKit × 1600×900, 1366×768 и mobile 390×844.

Проверяются: MP3/M4A native audio, Play/Pause, seek, ±5 секунд, keyboard shortcuts, автоматический переход треков, ручной переход без autoplay, autosave, reload restore на паузе, сохранение меток, retry и reconciliation конфликтов, идемпотентный Submit, Results/Review, verified/preliminary/ungraded grading, оригинальные изображения и viewer, independent scroll, адаптивные группы, resize мышью/клавиатурой, все 40 номеров в сетке, переходы к последнему вопросу, отсутствие page overflow и перекрытия footer.

Интеграционные проверки используют существующий изолированный runner: временный PostgreSQL, реальные Listening API/данные и оригинальные изображения, синтетические 12-секундные MP3/M4A для детерминированной проверки playback. Тестовая сессия подставляется только в удаляемую копию frontend; рабочие Firebase-модули не заменяются. Содержимое полноразмерных аудиозаписей Cambridge этим прогоном не проверяется.

Запуск из `backend`:

```sh
ALUA_RUN_LISTENING_BROWSER=1 .venv/bin/python -m pytest tests/test_listening_browser.py -q -s
```

Точечная проверка последнего изменения audio race:

```sh
ALUA_RUN_LISTENING_BROWSER=1 ALUA_LISTENING_TEST_GREP='owned verified lifecycle|manual track switch' .venv/bin/python -m pytest tests/test_listening_browser.py -q -s
```

## Скриншоты

- `before/` — V2, исходный baseline.
- `listening-{chromium,webkit}-{1600,1366}.png` — desktop с материалом слева.
- `listening-{chromium,webkit}-mobile.png` — mobile с материалом.
- `*-questions.png` — вопросы, включая mobile.
- `*-grid.png` — раскрытая сетка с ответом и меткой.

Локальный frontend: http://127.0.0.1:3000/listening (обычная авторизация приложения).
