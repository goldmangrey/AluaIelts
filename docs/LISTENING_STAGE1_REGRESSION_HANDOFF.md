# ALUA — Stage 1 Regression Handoff

**Production update, 2026-11-06:** Stage 1 coverage and Stage 2 image repairs are deployed. Backend `listening-visuals-20261106-61433b63`; real production Exam/Review smoke PASS and user-data fingerprints unchanged. C014/C028 exceptions remain. Read [LISTENING_FINAL_RELEASE.md](LISTENING_FINAL_RELEASE.md) for the current release IDs, evidence and rollback; earlier local-only statements below describe the historical stages.

## Текущий статус — исправлено локально, 2026-11-06

Пользователь отдельно разрешил исправление Stage 1 Part coverage. **Реализация завершена; заново исследовать причину или повторно исправлять active-group image selection не требуется.** Ниже этого раздела сохранён исторический аудит до исправления: его 157 Parts / 380 состояний и указания получить разрешение относятся к прежнему состоянию, а не к текущей задаче. Commit/push/deploy не выполнялись.

### Что изменено

- `web/src/features/listening/source-material.ts:53–77`, новая `visibleSourceMaterial(exam, part, groups)`: вызывает существующий `sourceMaterial` для каждой отображаемой группы, объединяет выбранные IDs, убирает повторы по ID и подтверждённым canonical/alternative families, сортирует по `display_order`, затем `question_range`. Не добавляет ID, которого нет в результатах group resolver; совместимость с allowlist старых snapshots сохраняется. Сам `sourceMaterial` и Stage 1 metadata не изменены.
- `web/src/features/listening/workspace-questions.tsx:24–44,63–67`, `WorkspaceQuestions`: изображениями управляет union отображаемых `groups`, а не `active`. Exam / Review All получают весь Part; filtered Review — объединение контекста только групп с видимыми вопросами. Заголовок показывает диапазон видимых вопросов. Active group продолжает определять answer bank / source lines; inputs, ответы и навигация не переписаны.
- `materialKey` зависит от Part, списка изображений и видимых group IDs. Фокус другого вопроса больше не заменяет изображения и не обнуляет ручной scroll источника. Смена Part или набора групп по-прежнему начинает новый source context. CSS двух независимых колонок не менялся.
- `web/scripts/audit-listening-part-coverage.mjs`: acceptance gate проверяет реальный SSR output против canonical union, включая порядок и отсутствие чужих материалов. Добавлен небольшой regression test C04 T1 P1: ровно Q1–4 / Q5–10, оба изображения смонтированы при current Q1/Q4/Q5/Q10. Filtered Review проверяется с видимыми Q1+Q5 и только Q5. Browser assertions проверяют стабильность IDs и ручного source scroll при focus переходе, независимость обеих прокруток, загрузку каждого изображения и desktop split.
- `web/tests/listening.spec.ts`, `web/tests/listening-review.spec.ts`: существующие ожидания source header обновлены с active-group range на visible-Part range. Полные backend-dependent suites не запускались; их lint/typecheck прошли.

### Acceptance результат

| Проверка | До | После |
|---|---:|---:|
| Tests / Parts / groups | 72 / 288 / 568 | 72 / 288 / 568 |
| Missing rendered states | 380 | **0** |
| Problematic Parts | 157 | **0** |
| Parts с несколькими уникальными изображениями | 177 | 177 |
| Known duplicate pairs / order inversions / wrong Part | 0 / 0 / 0 | **0 / 0 / 0** |
| Filtered Review component cases | 2 failures | **2 PASS** |
| Chromium desktop Exam / Review | воспроизведена регрессия | **16/16 PASS**, 8 Parts × 2 режима |

Проверены C04 T1 P1, C05 T1 P1, C09 T2 P2, C14 T2 P2, C18 T2 P4, C19 T3 P1; контроли C14 T1 P1 и текстовый C04 T2 P2. Все нужные asset IDs присутствуют одновременно в source DOM и изображения реально загружаются. При переходе в другую группу IDs сохраняются. Manual source scroll не сбрасывается; прокрутка вопросов не перемещает source и наоборот. Browser page errors: **0**. Оставшиеся 16 состояний без изображений относятся к полностью текстовым Parts; Q39/Q40 C04 T3 P4 теперь сохраняют изображения соседних видимых вопросов.

Команды проверки (из корня, кроме отмеченных):

```sh
node web/scripts/audit-listening-part-coverage.mjs --browser --assert-complete
# Из web/:
pnpm exec eslint src/features/listening/source-material.ts src/features/listening/workspace-questions.tsx scripts/audit-listening-part-coverage.mjs tests/listening.spec.ts tests/listening-review.spec.ts --max-warnings=0
pnpm exec tsc --noEmit
```

Все три команды завершились exit 0. Результаты: [part-coverage.json](listening-visual-audit/stage1/part-coverage.json), [regression-findings.csv](listening-visual-audit/stage1/regression-findings.csv) (только заголовок, текущих дефектов покрытия нет), [browser evidence](listening-visual-audit/stage1/regression-browser-evidence.json). Screenshots `stage1/regression-*-exam.png` / `*-review.png` обновлены после исправления. Исходные machine-readable результаты 157/380 и browser evidence сохранены в [coverage-before-fix/](listening-visual-audit/stage1/coverage-before-fix/). Детальные cases ниже — исторические, а не открытые дефекты.

### Границы доказательства и остаточная работа

- Chromium PASS относится к локальному wrapper настоящего `WorkspaceQuestions` (Exam props) и настоящему `ListeningReview` с synthetic ungraded results, с актуальными CSS/resolver/Asset. Это browser verification, но не полный authenticated production flow. Backend/auth/AI/audio не вызывались. Полный Exam autosave shell, реальные attempts/results, playback/AI Play/Loop, mobile, WebKit и browser-filter interactions в этой сессии не проверялись. Filtered Review проверен component-level.
- SHA-256 сравнение с baseline начала задачи подтвердило: dataset, registry, importer, audio/transcripts и остальные Listening component files не изменились; в защищённом наборе отличаются только `source-material.ts` и `workspace-questions.tsx`. Следовательно canonical full-page choices Stage 1 сохранены; повреждённые crop не возвращены.
- Физические 26 damaged crop и 21 suspected crop остаются задачей Stage 2. Изображения не редактировались, физическое качество повторно не аудировалось.
- Все найденные missing-render регрессии устранены одним общим UI/resolver изменением. Новые data exceptions не потребовались.

---

## Архив аудита до исправления


Дата: 2026-11-06 (Asia/Almaty). Проект: `/Users/yeskendir/Projects/Alua`. **Только аудит: production UI, resolver, metadata, exams, изображения, audio/transcripts/keys не менялись. Исправление требует отдельного разрешения пользователя. Stage 2, commit/push, deploy и Oracle запрещены в рамках этого задания.**

## 1. С чего начать следующей сессии

Этот файл самодостаточен: ниже точная причина, все 157 проблемных Parts с asset IDs и 380 состояниями, ожидаемое исправление и критерии. Огромный исходный аудит повторно открывать не требуется.

1. Получить отдельное разрешение на исправление. Не принимать этот handoff за такое разрешение.
2. Прочитать `web/AGENTS.md` перед frontend изменениями. Не стирать существующие незакоммиченные изменения.
3. Для проверки текущего состояния: `node web/scripts/audit-listening-part-coverage.mjs --browser`. Для будущего acceptance gate: тот же вызов с `--assert-complete` (сейчас ожидается exit 1 из-за подтверждённых регрессий). Без --browser доступна component-only проверка. Скрипт меняет только audit-артефакты в docs, поднимает disposable local Next в temp и закрывает сервер/браузер; не запускает importer.
4. Использовать один canonical ordered union материалов для всех **фактически отображаемых вопросов**, а не только активной группы. Не отменять Stage 1 дедупликацию.

## 2. Результат и единицы подсчёта

- Tests: **72/72**, Parts: **288/288**, groups: **568/568**.
- Parts с несколькими каноническими изображениями: **177**.
- Подтверждённая регрессия видимого покрытия: **157 Parts**; **380 состояний** активной группы из 568. При первом вопросе Part затронуто 149 Parts; ещё 8 проявляются при переходе к другой группе. Нельзя проверять только initial state.
- Suspected cases: **0** в рамках этой проверенной регрессии. Это не общий PASS семантического качества dataset.
- Browser verified: **5 проблемных Parts × 2 режима = 10 проблемных mode cases**. Всего 16 browser mode cases: пять проблемных Parts, C18 T2 P4 и два контроля. Остальные 152 проблемных Parts — **component verified**, а не browser verified.
- Canonical union сохраняет **0 известных duplicate pairs**, **0 order inversions**, **0 запрещённых Part bindings**. Coverage UI при этом НЕ проходит.
- 18 групп не получают изображений. Все structured: 16 групп в семи прежних полностью текстовых Parts и Q39/Q40 C04 T3 P4. Последние два допустимо не требуют собственных картинок, но при активном Q39/Q40 UI всё равно показывает остальные вопросы Part с таблицей — их материалы скрываются.

**Group coverage**: canonical материалы одной группы с её контекстом/инструкциями. **Part coverage**: упорядоченное множество canonical материалов всех отображаемых групп Part. **Rendered coverage**: `data-source-asset` элементы, реально смонтированные в source panel при данном current/filter. В данной проверке ожидаемое покрытие выводится из Stage 1 metadata; не из полного прежнего списка PDF/crop и не из OCR.

## 3. Exact root cause — подтверждено кодом, компонентом и браузером

Основной дефект — несовпадение областей видимости: WorkspaceQuestions рендерит весь Part (или все выбранные Review-фильтром вопросы), но вызывает sourceMaterial **один раз для active group**. Это общий UI/resolver contract mismatch, а не удаление файлов.

| Шаг | Точный участок | Поведение |
|---|---|---|
| Dataset → registry | `backend/app/content/listening_v1/exams/*.json`, `Part.visual_materials`; исходный registry **`web/src/features/listening/visual-materials.json`**; packaged copy `backend/app/content/listening_v1/qa/visual_materials.json` | Canonical assets, applicability question_range, display_order и alternative_asset_ids уже доступны для всей Part. Файлы изображений существуют в public allowlist. |
| Importer projection | `backend/scripts/listening_dataset/visual_materials.py`, `apply_visual_materials`, строки 24–62 (особенно 36–46, 59–61) | Part получает полный canonical список; group supporting_assets и visual_binding ограничены пересечением диапазонов. Это корректный group contract, который UI ошибочно использует как whole-Part contract. |
| Group resolver | `web/src/features/listening/source-material.ts`, `sourceMaterial`, 10–47: suitable 25–30, final assets 34–35 | Принимает единственную Group. Фильтрует материалы по group.question_range, canonical/альтернативы и display_order. Не знает, что соседние группы тоже видимы. |
| Active context | `web/src/features/listening/workspace-questions.tsx`, `WorkspaceQuestions`, 24–28 | groups = все группы selectedPart либо пересечение visibleQuestions. active = группа current, иначе первая. sourceMaterial вызывается только для active. |
| Images mounted | тот же файл, 59–65: header 60, Bank 62, assets.map 63 | Источник содержит material.assets active group. Нужных соседним вопросам элементов **нет в DOM**, они не просто ниже viewport или CSS-clipped. |
| Questions mounted | тот же файл, 72–81 | groups.map и group.questions.filter показывают все вопросы выбранного Part/Review filter. Этот набор шире active. |
| Transitions / scroll | тот же файл, 40–48, 50–51, 75 | materialKey меняется и source.scrollTop сбрасывается при изменении assets/bank/lines. Passive scroll не меняет current. onFocus question или explicit navigation меняют current/active, заменяя список картинок. |
| Exam | `web/src/features/listening/pages.tsx`, `Workspace`, go 35, WorkspaceQuestions 37 | visibleQuestions не передаётся, поэтому весь Part видим; current меняется при фокусе или navigation, включая autosave state. |
| Review | `web/src/features/listening/review.tsx`, `ListeningReview`, 47–65 и 87 | All: весь Part. Filter: все подходящие вопросы Part. Тот же WorkspaceQuestions. Saved answers не скрывают соседние группы. focus/go меняют контекст. |
| Actual image | `web/src/features/listening/questions.tsx`, `Asset`, строка 9 | Загружает лишь уже переданные IDs. Здесь не причина исключения: отсутствующий ID не достигает Asset. |

Пользователь описал изображения «справа». В текущем desktop CSS source panel расположен **слева**, questions — справа (`workspace.module.css:14–17`). Дефект относится к source panel независимо от стороны. На mobile панели переключаются вкладкой, но набор переданных IDs такой же; mobile отдельно не проверялся.

### Почему предыдущий показатель Missing required images = 0 был недостаточен

`web/scripts/check-listening-visuals.mjs:27–43`: проверяет sourceMaterial отдельно для каждой группы; строка 33 сравнивает именно с подходящими материалами этой же группы. `shown` накапливает assets **между разными вызовами** (35), затем проверяет сохранность каждого исходного материала через replacement (42–43). Это доказывает, что картинку можно получить в каком-то контексте, но не что она доступна вместе со всеми видимыми вопросами. Старый contact sheet также объединяет разные group states на одной обзорной странице и не является screenshot реального UI.

### Как пользователь достигает пропавшей картинки

Все нужные изображения можно получить без переключения Part: сфокусировать вопрос другой группы или перейти к нему навигацией. Но тогда предыдущая картинка исчезает. При простом scroll до следующих вопросов активная группа не меняется. Поэтому «файл доступен после фокуса» не удовлетворяет полному rendered coverage. Браузер подтвердил passive scroll и последующую смену материала после programmatic DOM focus (тот же React onFocus), а не только статическое чтение кода.

## 4. Browser/component evidence и ограничения

Скрипт использует настоящий TypeScript resolver (ES2022) и `renderToStaticMarkup` настоящего **WorkspaceQuestions + Input + Asset** для 568 group-first current states. Сравнивает все 10 смонтированных question nodes Part и реально смонтированные `data-source-asset` IDs с expected canonical union. Не подменяет алгоритм выбора картинок. SSR не выполняет сетевые эффекты Asset; поэтому загрузка пикселей отдельно проверена браузером.

Headless Chromium из уже установленного `@playwright/test`: 1440×900. Нативный CUA не потребовался. Local Next fixture копирует неизменённые Listening компоненты, CSS и registry. Exam — минимальный wrapper настоящего WorkspaceQuestions с теми же props, что pages.tsx:37; полный ListeningPage/autosave shell не запускался. Review — настоящий ListeningReview с synthetic ungraded rows, All filter; для начала с Part 2/4 fixture меняет только порядок synthetic rows, чтобы установить initial current. Реальные attempts/results не используются. Auth/API заменены только temp fixture boundary; читаются allowlisted public images, AI/audio/backend не вызываются.

В каждом browser case: проверены 10 question nodes, actual source IDs, завершение загрузки изображений, desktop split и независимость scroll; после scroll вопросов actual assets остаются прежними. В multi-group кейсах focus первого вопроса следующей группы проверяет результирующий набор: он меняется при другом материале и сохраняется для общего материала (например Q1–4 → Q5–6 C05 T1 P1). Browser page_errors: **0**. Само наличие ошибок покрытия — успешное воспроизведение дефекта, не acceptance PASS.

| Case | Exam / Review All | Наблюдение |
|---|---|---|
C04 T1 P1|browser verified / browser verified|Q1–10 смонтированы; при current Q1 только материал Q1–4. Scroll к Q5–10 не добавляет вторую страницу; focus Q5 заменяет первую.|
C05 T1 P1|browser verified / browser verified|Q1–10 смонтированы; поздняя страница отсутствует при current Q1. Дубли Dreamtime не вернулись.|
C09 T2 P2|browser verified / browser verified|При current Q11 карта/страница Q16–20 отсутствует. Shared Q14–16 state получает обе страницы, поэтому нельзя считать, что каждый state здесь неполный.|
C14 T2 P2|browser verified / browser verified|При current Q11 отсутствует plan Q16–20; focus Q16 подменяет материал.|
C19 T3 P1|browser verified / browser verified|При current Q1 отсутствует Q7–10; focus Q7 подменяет материал.|
C18 T2 P4|control covered / control covered|Один canonical материал Q31–40 доступен; чужая Q6–10 таблица не возвращена.|
C14 T1 P1|control covered / control covered|Один общий материал Q1–10, coverage полный.|
C04 T2 P2|text-only control / text-only control|Все десять MC вопросов, source images не требуются.|

Полный протокол: [regression-browser-evidence.json](listening-visual-audit/stage1/regression-browser-evidence.json). 16 screenshots имеют имя `regression-<test_id>-p<part>-exam|review.png` в том же каталоге. Показательный screenshot: [Exam C04](listening-visual-audit/stage1/regression-cambridge-04-test-01-p1-exam.png), [Review C04](listening-visual-audit/stage1/regression-cambridge-04-test-01-p1-review.png).

Дополнительно actual component проверен с visibleQuestions={1,5} для C04 T1 P1: отображаются два отфильтрованных вопроса из разных групп, но отсутствует второй материал. visibleQuestions={5}: только одна группа, coverage корректный. Это component proof filtered-props; реальное нажатие Incorrect/Unanswered filter в браузере не выполнялось. WebKit не запускался в этом прицельном аудите.

18 empty-image групп проверены по structured layout, source lines/options/answer bank и отсутствию image-backed требований. Они не объявлены defects только за пустой список. Семантический визуальный повторный аудит всех изображений/альтернатив не выполнялся. Использованы доказанные Stage 1 canonical relations; новых случаев удаления уникального материала внутри alternative family не доказано. Неизвестные legacy ревизии, mobile и player/AI interactions не охвачены.

## 5. Fix specification — НЕ РЕАЛИЗОВАНО

Нужно общее исправление visible-material aggregation, совместимое с существующим sourceMaterial(group). **Не превращать group resolver в безусловный part.supporting_assets fallback.**

1. В WorkspaceQuestions сначала определить selectedPart и **все фактически видимые вопросы** после visibleQuestions filter. Когда фильтра нет (Exam/Review All), это все вопросы выбранного Part.
2. Добавить небольшую pure функцию, например `visibleSourceMaterial(exam, part, visibleGroups, visibleQuestionNumbers)`, рядом с sourceMaterial. Она должна собрать результаты всех видимых групп, нормализовать через Stage 1 canonical/alternative metadata и вернуть единственный упорядоченный список. Не использовать runtime OCR/AI/pHash и не добавлять excluded assets.
3. Для полного Part expected = union подходящих group materials; сортировать по explicit display_order, затем подтверждённому question_range и стабильному исходному порядку для неизвестной legacy metadata. Для текущего dataset можно брать порядок из part.visual_materials/registry; **нельзя потерять совместимые IDs из snapshot allowlist**, которые legacy sourceMaterial выбрал вместо отсутствующего canonical.
4. Дедуплицировать по canonical identity/alternative family и отображаемому ID. Общая картинка нескольких групп появляется один раз. Уникальные страницы/инструкции сохраняются; соседние диапазоны или близкие hashes не означают альтернативность.
5. При фильтре Review показывать материалы для **всех видимых вопросов**, даже если это несколько групп. Допускается group-only набор, только когда фактически отображаемые вопросы относятся к одной группе/материальному контексту, либо в будущем есть явный режим single-group, который одновременно скрывает остальные вопросы. Один current/focus не является таким режимом.
6. Проверить shared instruction/continuation pages: простой фильтр страницы по одному номеру вопроса может скрыть инструкцию на соседней странице. Сначала сохранять полный материал каждой участвующей группы, как в Stage 1; уточнять question-level applicability только по подтверждённой metadata, не по OCR.
7. Source header должен отражать область отображаемого набора (Part question range или Review visible range), не создавать впечатление, что все материалы относятся только к active range. Active bank/text context можно оставить активным; не дублировать banks/все source lines бесконтрольно. Для image completeness эту семантику решить явно и покрыть тестом.
8. Разделить selection контекст и identity material set. При фокусе внутри того же visible set список изображений не должен заменяться/перемонтироваться; source scroll не сбрасывать из-за одной смены active group/bank/text. При смене Part или фактически видимых фильтром материалов допустим осмысленный reset. Сохранить независимый scroll вопросов, navigation target focus и existing keys.
9. Exam и Review должны вызывать один shared aggregation path. Результаты пользователей/answer draft/state/AI evidence/audio timelines не переписывать.

### Scope correction, не dataset rewrite

Для всех **157 найденных coverage regressions** достаточно одного общего изменения resolver/UI contract; отдельные data exceptions для этой причины **не обнаружены**. Реестр Stage 1 и exam JSON менять для данного исправления не требуется. C18 T2 P4 исправление ownership и 107 alternative IDs сохраняются. Повреждённые физические crop — отдельный Stage 2, не часть этого фикса. Это не обещание семантической безошибочности всех данных вне узкого regression audit.

## 6. Implementation map

| File | Function / lines | Required change | Regression test |
|---|---|---|---|
| `web/src/features/listening/source-material.ts` | sourceMaterial 10–47; новая pure visible aggregation рядом | Сохранить group resolver, добавить union visible groups с canonical identity/order и legacy allowlist compatibility | C04 Q1+Q5 expected оба IDs; filtered {5} один; C09 middle group обе страницы; 86+22 pairs не повторяются |
| `web/src/features/listening/workspace-questions.tsx` | WorkspaceQuestions 24–28, 40–48, 59–65, 72–81 | Material scope синхронизировать со смонтированными вопросами; стабильный material key; корректный source header | C04 passive scroll до Q10 не скрывает source; focus Q5 не меняет union/scroll; Part/filter меняет только необходимый набор |
| `web/scripts/check-listening-visuals.mjs` | group loop 27–43 | Сохранить прежние group integrity проверки, добавить rendered set для full visible Part и фильтров; не выдавать старый Missing=0 за UI completeness | Проверить каждый group-first current, не только первый; полнота expected union в DOM |
| `web/scripts/audit-listening-part-coverage.mjs` | read-only component/browser reproduction, весь файл | После разрешённого фикса сохранить сценарии и обновить expected assertion, если scope меняется; --assert-complete должен проходить | 72/288/568; missing_render_states=0; screenshot/DOM IDs Exam+Review |
| `web/tests/listening.spec.ts` | существующие source visibility / scroll tests | Добавить visible-Part ожидания реального Exam shell, autosave не подменять | C04/C05/C09/C14/C19, question navigation + reload, source union сохраняется |
| `web/tests/listening-review.spec.ts` | Review source/filter/navigation tests | Реальный Review All и filtered subset через UI, те же expected canonical IDs | All: полный Part; filter {Q1,Q5}: оба; single group: один; focus не меняет source union |
| `web/src/features/listening/pages.tsx` | Workspace go 35 / render 37 | Изменений не требуется, если агрегация в общем компоненте; не трогать draft/navigation | Real shell passes same visible-Part контракт, autosave/input state не меняются |
| `web/src/features/listening/review.tsx` | ListeningReview 47–65 / render 87 | Сохранить visibleQuestions contract; при необходимости только явная передача visible scope shared helper | Actual filters/nav сохраняют correct union, submitted result read-only |
| `web/src/features/listening/questions.tsx` | Asset 9 | Для этой регрессии не менять: получает IDs от общего компонента | Все ожидаемые IDs смонтированы и blob images загружены; не только count>0 |
| `backend/scripts/listening_dataset/visual_materials.py`, dataset, registry | apply_visual_materials / source input | Для этого фикса изменений не требуется | Metadata/files SHA сохраняются; Stage 1 group contracts остаются валидны |

## 7. Guardrails

- Не отменять Stage 1 canonical choices, alternative relations, display_order и wrong-Part exclusion. Не возвращать все исходные PDF/crop без отбора.
- Не менять question order, labels/options, answer inputs, constraints/grading, drafts/autosave, audio player и audio/transcript IDs/times.
- Не менять AI Review, Play Moment, Loop Moment, provider routing, Firebase/Reading.
- Не мигрировать/переписывать старые attempts/results. Старые snapshot должны сохранить доступные IDs и canonical-compatible выбор.
- Не менять CSS split-screen/Soft Capsules и независимый scroll; не делать hidden group inputs вместо исправления material scope.
- Не объявлять HTTP200, хотя бы одну картинку или union всех последовательных состояний доказательством rendered completeness.

## 8. Acceptance criteria следующего разрешённого исправления

- 72/72 Tests, 288/288 Parts, 568/568 groups; group coverage сохранён.
- Для каждого смонтированного visible question set и каждого group-first current: rendered canonical material set покрывает expected union одновременно. **Missing required rendered materials = 0**, missing_render_states = 0.
- Duplicate pairs = 0 (86 исходных + 22 дополнительных Stage 1); order inversions = 0 (все 9 regressions); wrong Part = 0, C18 T2 P4 не содержит Q6–10.
- Не теряются общие инструкции/уникальные continuation pages; empty text-only groups не требуют фиктивных картинок.
- Все пять browser regressions ниже проходят в Exam и Review. C18 и оба controls остаются корректными. Реальный Review filter и Exam navigation/autosave дополнительно проверены после фикса.
- Passive scroll и focus внутри неизменного visible set не подменяют и не сбрасывают source images/scroll; при Part/filter transition корректный новый set.
- TypeScript/ESLint, существующие relevant Listening contracts/browser tests и `node web/scripts/audit-listening-part-coverage.mjs --browser --assert-complete` проходят. Скрипт аудита по умолчанию фиксирует текущие defects и возвращает 0; только --assert-complete является acceptance gate.
- Никакой deployment до отдельного разрешения и завершения local QA.

## 9. Полный перечень подтверждённых Parts и состояний

Все записи ниже — HIGH: необходимый материал не смонтирован при одновременно доступных вопросах. На каждом Part буквы A/B/C — **только локальные алиасы точных IDs, определённых тут же**. Expected всегда указан полностью; actual/missing перечислены для каждого проблемного active state. Числа current означают первый вопрос группы; остальные вопросы той же группы дают тот же source set. Доступные после смены фокуса материалы не считаются одновременно rendered. Для всех случаев reproduction: открыть выбранный Part в Exam или Review All; установить current из таблицы; прокрутить список вопросов без смены фокуса.

### C04 / Test 1 / Part 1

ID: `cambridge-04-test-01-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **browser verified (initial state, Exam + Review); other states component verified**.

- **A** = `asset-5d5797fc540a6809abe3cc84e3e4b1c331f4c3a9be431d8bbe0984509705afca`; applicability Q1–4; display_order 1; source `Test_1_Section_1_PDF_Page_001_NOTES_ON_SOCIAL_PROGERAMME.png`.
- **B** = `asset-6fdc69064206de9950014eabdb5a957550ff8cf3e344ffd3e8b18c5c64c989c9`; applicability Q5–10; display_order 2; source `Test_1_Section_1_PDF_Page_002_WEEKEND_TRIPS_TABLE.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–4 | A | B |
| Q5 | Q5–10 | B | A |

### C04 / Test 2 / Part 3

ID: `cambridge-04-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-91e55ddd2a082a1f55c8c62a41092a700a9bd0b7a0c8538267017ba67d00a89b`; applicability Q21–26; display_order 1; source `Test_2_Section_3_PDF_Page_038_DETAILS_OF_ASSIGNMENT_FORM.png`.
- **B** = `asset-cdd9305f124af2e56abca78f003b0d71317fe0bd8b5419eb0fb506312dab8c7b`; applicability Q27–30; display_order 2; source `Test_2_Section_3_PDF_Page_039_ASSIGNMENT_BIBLIOGRAPHY_TABLE.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–26 | A | B |
| Q27 | Q27–30 | B | A |

### C04 / Test 3 / Part 4

ID: `cambridge-04-test-03-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-9315de6a08003966fc0ea249fc7b0f932408ee7ed565c618a315d93971f6daad`; applicability Q31–37; display_order 1; source `Test_3_Section_4_PDF_Page_071_NEW_UNION_BUILDING_NOTES.png`.
- **B** = `asset-f67fe4e6288c1de06836ed9883b7c911da421256199663e6dec32ba1d37ba630`; applicability Q33–38; display_order 2; source `Test_3_Section_4_PDF_Page_072_CHOICE_OF_SITE_TABLE.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–32 | A | B |
| Q38 | Q38–38 | B | A |
| Q39 | Q39–39 | ∅ | A, B |
| Q40 | Q40–40 | ∅ | A, B |

### C05 / Test 1 / Part 1

ID: `cambridge-05-test-01-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **browser verified (initial state, Exam + Review); other states component verified**.

- **A** = `asset-0d7083daf984f67cc1c9a5c193ee897d7728c4320b6e87138280551eaff169c8`; applicability Q1–6; display_order 1; source `Test_1_Section_1_PDF_Page_011.jpg`.
- **B** = `asset-5e06a6915b144a4d2c67ba335b9ceebafe2473c322cacd083b762f34df1c2b48`; applicability Q5–10; display_order 2; source `Test_1_Section_1_PDF_Page_012.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–4 | A | B |
| Q7 | Q7–10 | B | A |

### C05 / Test 1 / Part 3

ID: `cambridge-05-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-c50b6517d80cfa56cb29d9766fa0495b63fcea0b1bd3b2d014e2dac210aea3b0`; applicability Q21–25; display_order 1; source `Test_1_Section_3_PDF_Page_014.jpg`.
- **B** = `asset-2e684c3b4e4cf399b0104228f0e1a46e72687d75bf4dd4510c9f02a07ac69988`; applicability Q26–30; display_order 2; source `Test_1_Section_3_PDF_Page_015.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–23 | A | B |
| Q24 | Q24–25 | A | B |
| Q26 | Q26–30 | B | A |

### C05 / Test 2 / Part 2

ID: `cambridge-05-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-ee901e6af5b80024f2378c27f9866bd8b32d67cea277a91d7d788f3fb0a5b084`; applicability Q11–15; display_order 1; source `Test_2_Section_2_PDF_Page_034.jpg`.
- **B** = `asset-4119eb3cafa1db177a779bf4a006734e7410f0e81354e11f325ade8916b326da`; applicability Q16–20; display_order 2; source `Test_2_Section_2_PDF_Page_035.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–15 | A | B |
| Q16 | Q16–17 | B | A |
| Q18 | Q18–20 | B | A |

### C05 / Test 3 / Part 2

ID: `cambridge-05-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-1decd1de6515df4db621cd124b544857a633fd512ad9eb78c7ec0fa7dfdca4f8`; applicability Q11–15; display_order 1; source `Test_3_Section_2_PDF_Page_058.jpg`.
- **B** = `asset-14e70563ed61f23e7c32fe7e149d401cf004a16ecc910f34f3df1bfd0e217dd7`; applicability Q16–20; display_order 2; source `Test_3_Section_2_PDF_Page_059.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–15 | A | B |
| Q16 | Q16–20 | B | A |

### C05 / Test 3 / Part 4

ID: `cambridge-05-test-03-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-0c6d9f11ca62fac35fdf04b7c6e364871ca6b9646d7032a10646191a5a737b3c`; applicability Q31–35; display_order 1; source `Test_3_Section_4_PDF_Page_061.jpg`.
- **B** = `asset-c78cfcc68b5e42eca2cfd2f88496a16dec48d99b1eab27611ac81d9ac0f6e5a6`; applicability Q36–40; display_order 2; source `Test_3_Section_4_PDF_Page_062.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–35 | A | B |
| Q36 | Q36–40 | B | A |

### C05 / Test 4 / Part 2

ID: `cambridge-05-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-836ead9b1ae567c09511b557cd526a4a45539140fb88c722996a3a82da2b1437`; applicability Q11–17; display_order 1; source `Test_4_Section_2_PDF_Page_080.jpg`.
- **B** = `asset-69df9f63bd1c5b1094d3966b54e1e25a0eadd64baabbd4539fcb592bbc6a1dc0`; applicability Q18–20; display_order 2; source `Test_4_Section_2_PDF_Page_081.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–13 | A | B |
| Q14 | Q14–17 | A | B |
| Q18 | Q18–20 | B | A |

### C05 / Test 4 / Part 3

ID: `cambridge-05-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-d8d95abf2072e5b22871e6e2349b8abf34e786cb3f720a87e7969842b037c4ce`; applicability Q21–27; display_order 1; source `Test_4_Section_3_PDF_Page_082.jpg`.
- **B** = `asset-b9a06bf8325b389b51e0417a14a7563e74e688f74add45b974289a620547187e`; applicability Q28–30; display_order 2; source `Test_4_Section_3_PDF_Page_083.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–27 | A | B |
| Q28 | Q28–30 | B | A |

### C05 / Test 4 / Part 4

ID: `cambridge-05-test-04-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-526e262f9a12dda25ba7e1e62d08ca8e4c5ef74202105cbdb4e3b277fe41abc2`; applicability Q31–36; display_order 1; source `Test_4_Section_4_PDF_Page_084.jpg`.
- **B** = `asset-4f86c83b48874546601c830feadd0bd6f504ddf6fcb7337afb606447cbcb1358`; applicability Q37–40; display_order 2; source `Test_4_Section_4_PDF_Page_085.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–36 | A | B |
| Q37 | Q37–40 | B | A |

### C06 / Test 1 / Part 1

ID: `cambridge-06-test-01-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-7d4a9ac26a921bff190733982eed754af7342f87429a4e89ad94b14336d726ff`; applicability Q1–4; display_order 1; source `Test_1_Section_1_PDF_Page_011.jpg`.
- **B** = `asset-151efc63b36d2e2ddc5d0317ed50c5dd81841931e8b51957686a1469418a0371`; applicability Q5–10; display_order 2; source `Test_1_Section_1_PDF_Page_012.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–4 | A | B |
| Q5 | Q5–8 | B | A |
| Q9 | Q9–10 | B | A |

### C06 / Test 1 / Part 2

ID: `cambridge-06-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-d0ac2f4c3d16d17a4398ba1935acd15dc5315d25ed67ef6cf3a34604c7a7a933`; applicability Q11–16; display_order 1; source `Test_1_Section_2_PDF_Page_013.jpg`.
- **B** = `asset-37fb8b707fd13756db402eb492cdd5df9304a713a49ed705f5f7ef4722cf58ad`; applicability Q17–20; display_order 2; source `Test_1_Section_2_PDF_Page_014.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–20 | B | A |

### C06 / Test 1 / Part 3

ID: `cambridge-06-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-bc14460407ac8edcc5325334996a802129272ebda6ffbcc53f12bee59acf9292`; applicability Q21–25; display_order 1; source `Test_1_Section_3_PDF_Page_015.jpg`.
- **B** = `asset-1eb4551e4cb970d5ff3885ef4a274cbe3c622c7588c84a8da43f0e00e105107d`; applicability Q26–30; display_order 2; source `Test_1_Section_3_PDF_Page_016.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–21 | A | B |
| Q22 | Q22–25 | A | B |
| Q26 | Q26–30 | B | A |

### C06 / Test 1 / Part 4

ID: `cambridge-06-test-01-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-9789f09ec602ee1b5f367a5bfc21804cb0e7a0d51dbbd0a0cf2bdc98087da4b0`; applicability Q31–37; display_order 1; source `Test_1_Section_4_PDF_Page_017.jpg`.
- **B** = `asset-4b954f0dc7810094931966865150fbca8294dcf200f8d00cc04a7859d3bb7a4d`; applicability Q38–40; display_order 2; source `Test_1_Section_4_PDF_Page_018.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–37 | A | B |
| Q38 | Q38–40 | B | A |

### C06 / Test 2 / Part 1

ID: `cambridge-06-test-02-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-f3b18bdf58d5a232baaca6da50d1a7d3ce4c3cc9bd120281d7f4ea8d239ad99b`; applicability Q1–5; display_order 1; source `Test_2_Section_1_PDF_Page_034.jpg`.
- **B** = `asset-1ab319d4dff1ce6fcde22c5f6db4d3c9d12456f57018a54229f374081146e03a`; applicability Q6–10; display_order 2; source `cambridge-06-test-02-part-1.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–5 | A | B |
| Q6 | Q6–10 | B | A |

### C06 / Test 2 / Part 2

ID: `cambridge-06-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-7a6bd325e3f99857c030c99087ca00a392cb8dd36a8c783745d66950fe01295f`; applicability Q11–17; display_order 1; source `Test_2_Section_2_PDF_Page_036.jpg`.
- **B** = `asset-9bb29f544292bdb5ac91b62099d22473f9893a3597c349074e9a26ddb0c6e5f4`; applicability Q18–20; display_order 2; source `Test_2_Section_2_PDF_Page_037.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–17 | A | B |
| Q18 | Q18–20 | B | A |

### C06 / Test 2 / Part 4

ID: `cambridge-06-test-02-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-aaa49ae52d4c5dd92be5633532ae2517d9cf4d55dbccc7ccf1492d29241a8815`; applicability Q31–38; display_order 1; source `Test_2_Section_4_PDF_Page_039.jpg`.
- **B** = `asset-750ec18314f8574ceb29439770252d5c7d8b39eda1bc56d8d9a7dea8c9792b6b`; applicability Q38–40; display_order 2; source `Test_2_Section_4_PDF_Page_040.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–37 | A | B |

### C06 / Test 3 / Part 2

ID: `cambridge-06-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-e311c0f9b6ab96ae7472b91ce6783e1f514f3699731d14c3697bed8e73941dfa`; applicability Q11–13; display_order 1; source `Test_3_Section_2_PDF_Page_058.jpg`.
- **B** = `asset-466e2e0c2e5b3874455fe5fcf48f05dc44dd3f1eb6c688fba080caf9fa093d17`; applicability Q14–20; display_order 2; source `Test_3_Section_2_PDF_Page_059.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–13 | A | B |
| Q14 | Q14–17 | B | A |
| Q18 | Q18–20 | B | A |

### C06 / Test 3 / Part 3

ID: `cambridge-06-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-395e75b6424d0572230e5992eb94f21ff04aaa5837aa8ea25cbac27628ad0776`; applicability Q21–24; display_order 1; source `Test_3_Section_3_PDF_Page_060.jpg`.
- **B** = `asset-a3d806a65c12507c335671bba162d72ddfdd1fd91e0e8b0447cef5dcd1979027`; applicability Q25–30; display_order 2; source `Test_3_Section_3_PDF_Page_061.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–30 | B | A |

### C06 / Test 3 / Part 4

ID: `cambridge-06-test-03-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-74feab8aaa0a830142b767bdc7c88d8408524ff8a33b857415dca002b14ee11b`; applicability Q31–34; display_order 1; source `Test_3_Section_4_PDF_Page_062.jpg`.
- **B** = `asset-0cce2c930e6f20787568f2f2257fa3395a9b66803b358d5e8b415c05d341c50d`; applicability Q35–40; display_order 2; source `Test_3_Section_4_PDF_Page_063.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–34 | A | B |
| Q35 | Q35–40 | B | A |

### C06 / Test 4 / Part 2

ID: `cambridge-06-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-a2c418ba82eba241e82054e6c36388ac3815ae6ee61d9366e8b0cd5683758501`; applicability Q11–13; display_order 1; source `Test_4_Section_2_PDF_Page_080.jpg`.
- **B** = `asset-77cd449a6cf2ace309feeab7e32376c22f82e0e7f40791906bf076fe3112f6a1`; applicability Q14–20; display_order 2; source `Test_4_Section_2_PDF_Page_081.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–13 | A | B |
| Q14 | Q14–20 | B | A |

### C06 / Test 4 / Part 3

ID: `cambridge-06-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-b723ab26cf04d9dc32c6db53c62c568294a8c1681a27f0eb667c0f2563e01c9a`; applicability Q21–27; display_order 1; source `Test_4_Section_3_PDF_Page_082.jpg`.
- **B** = `asset-9d0fc3e969a74a68563925ca319f202c27a2632a2bf206fdad22c1c9592881a6`; applicability Q28–30; display_order 2; source `Test_4_Section_3_PDF_Page_083.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–27 | A | B |
| Q28 | Q28–30 | B | A |

### C06 / Test 4 / Part 4

ID: `cambridge-06-test-04-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-47a9009e573ce4e8247fa0eda7e355a4e6bf679d6e49128df96ff1fce03ca3fe`; applicability Q31–34; display_order 1; source `Test_4_Section_4_PDF_Page_084.jpg`.
- **B** = `asset-4eab841462527432d0a01741a95478adfc4e9a430c4fc80e16d414d471671a01`; applicability Q35–40; display_order 2; source `Test_4_Section_4_PDF_Page_085.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–34 | A | B |
| Q35 | Q35–40 | B | A |

### C07 / Test 1 / Part 1

ID: `cambridge-07-test-01-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-25cdb5d102569063751ef3324607bc381475898ef52fc6f2f6ceec579e13c4b4`; applicability Q1–5; display_order 1; source `Test_1_Section_1_PDF_014.png`.
- **B** = `asset-717877a86b42c5d736524fdbde6cc9a14f6100235b5f7223f436d6987cade147`; applicability Q6–10; display_order 2; source `Test_1_Section_1_PDF_015.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–5 | A | B |
| Q6 | Q6–10 | B | A |

### C07 / Test 1 / Part 2

ID: `cambridge-07-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-bac0213c0bb6a359e909d423f45ce463433a1b34e9217df21672d8b4e8499a99`; applicability Q11–16; display_order 1; source `Test_1_Section_2_PDF_016.png`.
- **B** = `asset-ee2fdfb52ef03fd107e91c1a1ebb0ef5d12f7fbf65f30b2472883e46afa046ff`; applicability Q17–20; display_order 2; source `Test_1_Section_2_PDF_017.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–20 | B | A |

### C07 / Test 1 / Part 3

ID: `cambridge-07-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-65bcf1e805dd85e509e597061c84d6d7806c991a839752aabfe26960a0765da2`; applicability Q21–23; display_order 1; source `Test_1_Section_3_PDF_018.png`.
- **B** = `asset-95e7a429e028c4c23222563fb7c2572f79bb1cb6682d443f04d3c769f9ad2045`; applicability Q24–30; display_order 2; source `Test_1_Section_3_PDF_019.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–23 | A | B |
| Q24 | Q24–27 | B | A |
| Q28 | Q28–30 | B | A |

### C07 / Test 1 / Part 4

ID: `cambridge-07-test-01-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-21a25aca1fd2ff920ca0a44f222fcd19fb9308c961aca9b3a5c60e1547e3965b`; applicability Q31–35; display_order 1; source `Test_1_Section_4_PDF_020.png`.
- **B** = `asset-367570d685129067d3bb2c8f66f1ac7cb85d00758a3c2ec2324cb29b3010fab8`; applicability Q36–40; display_order 2; source `Test_1_Section_4_PDF_021.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–35 | A | B |
| Q36 | Q36–40 | B | A |

### C07 / Test 2 / Part 2

ID: `cambridge-07-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-91461cc55d6b2e1625c02e4e508a0652df376011bb67c711b7059dd27f5f3e21`; applicability Q11–12; display_order 1; source `Test_2_Section_2_PDF_038.png`.
- **B** = `asset-8c33e5754ef42eb9433c138157b7351310e340c08c17ddb86a77b1e90779276c`; applicability Q13–20; display_order 2; source `Test_2_Section_2_PDF_039.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–18 | B | A |
| Q19 | Q19–20 | B | A |

### C07 / Test 2 / Part 3

ID: `cambridge-07-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-8a4e8d0131b41e1184e290d2fb0b687093a5c92f9935b58a0f4ca88348aaad11`; applicability Q21–26; display_order 1; source `Test_2_Section_3_PDF_040.png`.
- **B** = `asset-902c0f421290873f78fcef47a1daa8d2c7e4abbbf77587060e8163ba51885bbf`; applicability Q27–30; display_order 2; source `Test_2_Section_3_PDF_041.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–26 | A | B |
| Q27 | Q27–28 | B | A |
| Q29 | Q29–30 | B | A |

### C07 / Test 2 / Part 4

ID: `cambridge-07-test-02-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-3b52ae72f129e7789100cb84f3aded368da668488dd9fdb44e363cb9fd91d72d`; applicability Q31–38; display_order 1; source `Test_2_Section_4_PDF_042.png`.
- **B** = `asset-c9299a1252555da23575e7f583bb285c6a5a879278925b8d99464c09688a9cfa`; applicability Q36–40; display_order 2; source `Test_2_Section_4_PDF_043.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–35 | A | B |

### C07 / Test 3 / Part 1

ID: `cambridge-07-test-03-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-00f25a609c603d5aad1aa1b54f89382635d7178afaccb7cc595350eea9fead8b`; applicability Q1–5; display_order 1; source `Test_3_Section_1_PDF_060.png`.
- **B** = `asset-5b59329c7a11c0e140f1bca31a920b7c8e884ac5d12c72bdaa0c94dee3d59e74`; applicability Q6–10; display_order 2; source `Test_3_Section_1_PDF_061.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–2 | A | B |
| Q3 | Q3–5 | A | B |
| Q6 | Q6–10 | B | A |

### C07 / Test 3 / Part 2

ID: `cambridge-07-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-6b15dcbeb6d7f4cb3f908718164519c472664817308a82afb60ddf56f46a9360`; applicability Q11–16; display_order 1; source `Test_3_Section_2_PDF_062.png`.
- **B** = `asset-f5ab4ba50efdeb3013bb5006b9bd1e61fffdcd2fb8cd74a2354fb39cfe2d20ff`; applicability Q17–20; display_order 2; source `Test_3_Section_2_PDF_063.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–20 | B | A |

### C07 / Test 3 / Part 3

ID: `cambridge-07-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B, C**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-bd09bfe9283047c685ef224e3ad2fd8d1f9a363191ff2eb9ed6180b182d77e90`; applicability Q21–22; display_order 1; source `Test_3_Section_3_PDF_064.png`.
- **B** = `asset-9b12f7d7e2bb1dec0eb999c79fc6dfd05645eb67f665d07a4d523132699fb707`; applicability Q23–25; display_order 2; source `Test_3_Section_3_PDF_065.png`.
- **C** = `asset-63e71302a4a635324335674475a4194c715e1ca0b52fa9690666753e3f41057e`; applicability Q26–30; display_order 3; source `Test_3_Section_3_PDF_066.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B, C |
| Q23 | Q23–25 | B | A, C |
| Q26 | Q26–30 | C | A, B |

### C07 / Test 3 / Part 4

ID: `cambridge-07-test-03-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-5edce90b3f20bec803002f4d98b38cc711a326826985bca0bb8b13307a3fcde9`; applicability Q31–34; display_order 1; source `Test_3_Section_4_PDF_067.png`.
- **B** = `asset-1a5d69427481125af0f55a588bd0e5fdcd3cd65685446f9591380b7399dbbeb7`; applicability Q35–40; display_order 2; source `Test_3_Section_4_PDF_068.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–34 | A | B |
| Q35 | Q35–40 | B | A |

### C07 / Test 4 / Part 1

ID: `cambridge-07-test-04-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-2d699765d75235aa6ec60a141a5011ed1349bffb7c57443faf06b55459a2f7ec`; applicability Q1–6; display_order 1; source `Test_4_Section_1_PDF_085.png`.
- **B** = `asset-d04971525e7b57b63c9016f73a2093406d57bcab0b46d22a08bba25a53bcf3ac`; applicability Q7–10; display_order 2; source `Test_4_Section_1_PDF_086.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–6 | A | B |
| Q7 | Q7–10 | B | A |

### C07 / Test 4 / Part 2

ID: `cambridge-07-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-1e3088d31ccbbf6d1e3db2562165b23f1eb57526261836a3e6016b16442c6e62`; applicability Q11–14; display_order 1; source `Test_4_Section_2_PDF_087.png`.
- **B** = `asset-a7c67992a6b3326150d18cea0d9d508d4740d67ced286623e398bdb260d70a7b`; applicability Q15–20; display_order 2; source `Test_4_Section_2_PDF_088.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–17 | B | A |
| Q18 | Q18–20 | B | A |

### C07 / Test 4 / Part 3

ID: `cambridge-07-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-7b21f4f844067596457c5c5bb474a1e7b467b01ccfa645b9a81a41e5e2b78cc7`; applicability Q21–26; display_order 1; source `Test_4_Section_3_PDF_089.png`.
- **B** = `asset-287610408dc88a1984212fb8e500eb2bc0da70f8a5723e5716b53c3002affbd0`; applicability Q27–30; display_order 2; source `Test_4_Section_3_PDF_090.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–26 | A | B |
| Q27 | Q27–30 | B | A |

### C07 / Test 4 / Part 4

ID: `cambridge-07-test-04-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-fcf217c0e72c8aa0b6f8ff0baf1514845e297395a71123fdfdd370b9de3da290`; applicability Q31–33; display_order 1; source `Test_4_Section_4_PDF_091.png`.
- **B** = `asset-56cc904097a50cdc6107b0ede3bd6657fb1ba75c499a2a0a0ce71c8359fd573e`; applicability Q34–40; display_order 2; source `Test_4_Section_4_PDF_092.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–33 | A | B |
| Q34 | Q34–40 | B | A |

### C08 / Test 1 / Part 2

ID: `cambridge-08-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-70d249cfaab68fbdd79843d3bdfdb13fc555575e45f2a3837d1b1c56aae93ddb`; applicability Q11–18; display_order 1; source `Test_1_Section_2_PDF_011.png`.
- **B** = `asset-8ec70fb94a322b6a4d516eeaa4273586fd675612d0d828e5f8a3e320dcfc2201`; applicability Q13–20; display_order 2; source `Test_1_Section_2_PDF_012.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q19 | Q19–20 | B | A |

### C08 / Test 1 / Part 3

ID: `cambridge-08-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-4eea84dd076b92b700e5e936ad45174ce2c3e039c745e5a662dcada3780ee741`; applicability Q21–24; display_order 1; source `Test_1_Section_3_PDF_013.png`.
- **B** = `asset-a43b0b429c52dc7e7837dd2a81ff3125f875063d993aa62f986d5f3d5e1ce82e`; applicability Q25–30; display_order 2; source `Test_1_Section_3_PDF_014.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–27 | B | A |
| Q28 | Q28–30 | B | A |

### C08 / Test 2 / Part 1

ID: `cambridge-08-test-02-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-028def577baf073853409b3e49311d878f4658dd99e053d61acc35942d87f651`; applicability Q1–3; display_order 1; source `Test_2_Section_1_PDF_032.png`.
- **B** = `asset-6e5743b8cc2ff709113a27b4c56503a0e0f74cdf7d5b505c3979e5856d89b54e`; applicability Q4–10; display_order 2; source `Test_2_Section_1_PDF_033.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–3 | A | B |
| Q4 | Q4–10 | B | A |

### C08 / Test 2 / Part 2

ID: `cambridge-08-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-e19b974bcd191abbd7e6f7f563a936053778b04c700cad1f9064384e4d824712`; applicability Q11–14; display_order 1; source `Test_2_Section_2_PDF_034.png`.
- **B** = `asset-e0d8489890ff0b7991cd97bf003b9e8ff84f84c0d110883dc173372bc265369b`; applicability Q15–20; display_order 2; source `Test_2_Section_2_PDF_035.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–11 | A | B |
| Q12 | Q12–14 | A | B |
| Q15 | Q15–20 | B | A |

### C08 / Test 2 / Part 3

ID: `cambridge-08-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-d6724540a6a2990b6e8d2abbe61b070ab1ddf7aca9daa9eca83f1c100c6e340c`; applicability Q21–24; display_order 1; source `Test_2_Section_3_PDF_036.png`.
- **B** = `asset-0863b178eb14f521c3f296035e555a5493c6c5571b3f22ad5e65c54912a63241`; applicability Q25–30; display_order 2; source `Test_2_Section_3_PDF_037.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–30 | B | A |

### C08 / Test 2 / Part 4

ID: `cambridge-08-test-02-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-3ae1b249261f640f9fd87f6db006b4bbaa501a841e4e4eaaa0f48f9d834bd23e`; applicability Q31–39; display_order 1; source `Test_2_Section_4_PDF_038.png`.
- **B** = `asset-1174cca9fed40e5c2ae55c3f777a78c3755d87a8d018e81441681121cccb3dd3`; applicability Q37–40; display_order 2; source `Test_2_Section_4_PDF_039.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–36 | A | B |

### C08 / Test 3 / Part 1

ID: `cambridge-08-test-03-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B, C**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-b6e6f96e1f332d70f5b94d9cf7d8f3d0a4a595c9ad052dac3877ac8694229f87`; applicability Q1–3; display_order 1; source `Test_3_Section_1_PDF_055.png`.
- **B** = `asset-c1a0f801298f2422058984c18336096fa41648b81aa927812fb881bb203d6015`; applicability Q4–8; display_order 2; source `Test_3_Section_1_PDF_056.png`.
- **C** = `asset-dc0a174a323f297d4ee38e4c7c13b1c17687dfd1aa8e76ca6344b81e3d33b0b3`; applicability Q9–10; display_order 3; source `Test_3_Section_1_PDF_057.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–3 | A | B, C |
| Q4 | Q4–8 | B | A, C |
| Q9 | Q9–10 | C | A, B |

### C08 / Test 3 / Part 2

ID: `cambridge-08-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-bb408ea9727f85aff70aa26c1da8c16a7cc3fa9bc3671192b54c831edc7b14fe`; applicability Q11–16; display_order 1; source `Test_3_Section_2_PDF_058.png`.
- **B** = `asset-638515a53f20af17e124abc1a3302101f73062e8d748dff2a89b4710d648a36c`; applicability Q17–20; display_order 2; source `Test_3_Section_2_PDF_059.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–20 | B | A |

### C08 / Test 3 / Part 3

ID: `cambridge-08-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-b6cc69dc513ea5cad2c5d09579446c217bbe276d46fcdc34f82c458eb2812702`; applicability Q21–26; display_order 1; source `Test_3_Section_3_PDF_060.png`.
- **B** = `asset-86673bec815ed72c553bb6c62672ab3dafcd50f3b18b2e86a6be608a938828ae`; applicability Q27–30; display_order 2; source `Test_3_Section_3_PDF_061.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–26 | A | B |
| Q27 | Q27–30 | B | A |

### C08 / Test 3 / Part 4

ID: `cambridge-08-test-03-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-7e181de3963b28e0758a6d7d0ef14fd1e9bbfc2d120f547f91743c5620759baa`; applicability Q31–34; display_order 1; source `Test_3_Section_4_PDF_062.png`.
- **B** = `asset-213a607bdbe5d3e649ebda15f02744ba77829d7a61275d8552cec74658d9a007`; applicability Q35–40; display_order 2; source `Test_3_Section_4_PDF_063.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–34 | A | B |
| Q35 | Q35–40 | B | A |

### C08 / Test 4 / Part 2

ID: `cambridge-08-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-1a9c390695b0913cf0740420d060df0d87ba0231311369ecc0d6445c51080fad`; applicability Q11–13; display_order 1; source `Test_4_Section_2_PDF_081.png`.
- **B** = `asset-3178707596fe8f7cdad3ad479feabf23dc6a7444d8a2ec036317816ec5254650`; applicability Q14–20; display_order 2; source `Test_4_Section_2_PDF_082.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–13 | A | B |
| Q14 | Q14–20 | B | A |

### C08 / Test 4 / Part 3

ID: `cambridge-08-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-d6945092111c4e01f9b825c1d3ad4b1411acb98dfbb2212b366fbf424527e355`; applicability Q21–26; display_order 1; source `Test_4_Section_3_PDF_083.png`.
- **B** = `asset-30cacbb0e9648ba154c1279f2f0d37228f08947e04fb8a9ece20c911c3b9ade0`; applicability Q27–30; display_order 2; source `Test_4_Section_3_PDF_084.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–26 | A | B |
| Q27 | Q27–30 | B | A |

### C08 / Test 4 / Part 4

ID: `cambridge-08-test-04-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-199a193fe8ec7ebce829af2fe5367e7fc73a24775df6673abaeb0dbb289c1d59`; applicability Q31–36; display_order 1; source `Test_4_Section_4_PDF_085.png`.
- **B** = `asset-eae182439414707c6a710c554c4f58d739621514f6a68d738da459867bc4a7c5`; applicability Q37–40; display_order 2; source `Test_4_Section_4_PDF_086.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–36 | A | B |
| Q37 | Q37–40 | B | A |

### C09 / Test 1 / Part 2

ID: `cambridge-09-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-254aa9c201309cc271774c1c0143410c82b0b950355d4a15f50b0c7a86fbf46c`; applicability Q11–18; display_order 1; source `Test_1_Section_2_PDF_Page_002.jpg`.
- **B** = `asset-d8b31ff576a109f9af1a01612c59820da253cce2d20f7e6cfb3bc74b31d83eda`; applicability Q19–20; display_order 2; source `Test_1_Section_2_PDF_Page_003.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–18 | A | B |
| Q19 | Q19–20 | B | A |

### C09 / Test 2 / Part 2

ID: `cambridge-09-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **browser verified (initial state, Exam + Review); other states component verified**.

- **A** = `asset-dee84aae600590be7edc3b69e6d62c27799f31546f7f7e994a040febe65e8fec`; applicability Q11–15; display_order 1; source `Test_2_Section_2_PDF_Page_029.jpg`.
- **B** = `asset-c807b06d0f8e77a0799e466a8b72b9b624a990e702f61bd3868321fd5d7f2156`; applicability Q16–20; display_order 2; source `Test_2_Section_2_PDF_Page_030.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–13 | A | B |
| Q17 | Q17–20 | B | A |

### C09 / Test 2 / Part 3

ID: `cambridge-09-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-96ebadd5eed2d2348bf4acbd3ba0ece93cbed49e56518a65ccb593aae8ac2804`; applicability Q21–24; display_order 1; source `Test_2_Section_3_PDF_Page_031.jpg`.
- **B** = `asset-4f2f5d580856dc53579c221c4711a0a5dce98edf2b7129d40a6d877fbb9c70c0`; applicability Q25–30; display_order 2; source `Test_2_Section_3_PDF_Page_032.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–30 | B | A |

### C09 / Test 3 / Part 1

ID: `cambridge-09-test-03-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-8a5ba7d63bdc0feb7e5806b471dcd6e11ab216b00d0892a6c4529f7de91e16f3`; applicability Q1–5; display_order 1; source `Test_3_Section_1_PDF_Page_057.jpg`.
- **B** = `asset-e12eb8e777eda29b77550c94a8a924d451c16e500f2c2c1c4b5e5af5a7869a73`; applicability Q6–10; display_order 2; source `Test_3_Section_1_PDF_Page_058.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–5 | A | B |
| Q6 | Q6–10 | B | A |

### C09 / Test 3 / Part 2

ID: `cambridge-09-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-4ccf020e6eb7b1dbb22d7c404674a8dbaa405785a05626063cf1ede0bc55fda4`; applicability Q11–18; display_order 1; source `Test_3_Section_2_PDF_Page_059.jpg`.
- **B** = `asset-fb72d3e631e047c6ac5b2fd3e158ce0a5b61f758bd0948f23dae34294f61c7d5`; applicability Q14–20; display_order 2; source `Test_3_Section_2_PDF_Page_060.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–13 | A | B |
| Q19 | Q19–20 | B | A |

### C09 / Test 3 / Part 4

ID: `cambridge-09-test-03-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-d3051fd52a764df6e443ced002a23b7217014228fa4813a51083484f3ec42116`; applicability Q31–34; display_order 1; source `Test_3_Section_4_PDF_Page_062.jpg`.
- **B** = `asset-20f6e0511ac715526796873642ed63c8393ce12353b5bcc40726f710cf090f9c`; applicability Q35–40; display_order 2; source `Test_3_Section_4_PDF_Page_063.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–32 | A | B |

### C09 / Test 4 / Part 1

ID: `cambridge-09-test-04-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-65b0f3165011ab12fb47befbd7e9fe4439e03b3a9c4b73ba5888b6f91e2b760d`; applicability Q1–6; display_order 1; source `Test_4_Section_1_PDF_Page_084.jpg`.
- **B** = `asset-836fcd8aaf3acb5d5d90c130499c9e2a3cfa7639486cfc0e8d117ee0f8413ea8`; applicability Q7–10; display_order 2; source `Test_4_Section_1_PDF_Page_085.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–4 | A | B |
| Q5 | Q5–6 | A | B |
| Q7 | Q7–10 | B | A |

### C09 / Test 4 / Part 2

ID: `cambridge-09-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B, C**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-8e2da65e03f2eeba90643b644dd61575beed6dcf670536e05b70b8432c9e3968`; applicability Q11–13; display_order 1; source `Test_4_Section_2_PDF_Page_086.jpg`.
- **B** = `asset-0ff3eeb103536bfe7a3b28d8a3e165641eb87789af16bbb9b41b8512844efad1`; applicability Q14–18; display_order 2; source `Test_4_Section_2_PDF_Page_087.jpg`.
- **C** = `asset-81ca2eb286ac2c8b46efb51201fa95f74e37d9cf56bb77d53094cd7cc9021531`; applicability Q19–20; display_order 3; source `Test_4_Section_2_PDF_Page_088.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–13 | A | B, C |
| Q14 | Q14–18 | B | A, C |
| Q19 | Q19–20 | C | A, B |

### C09 / Test 4 / Part 3

ID: `cambridge-09-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-acc06a3c7e43ba19cc7a514b79daca2214c9f7de005c5554a71d75cb20165481`; applicability Q21–25; display_order 1; source `Test_4_Section_3_PDF_Page_089.jpg`.
- **B** = `asset-fdcf4ea2fcb8a7f15d25636d4ff6315e474e90db2d882d8c88b3d38fdbaff1ad`; applicability Q26–30; display_order 2; source `Test_4_Section_3_PDF_Page_090.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–25 | A | B |
| Q26 | Q26–30 | B | A |

### C09 / Test 4 / Part 4

ID: `cambridge-09-test-04-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-5df6f929af2ae70c7c359639a620fa694112be90af5c7be76aea67e0ff2f73a6`; applicability Q31–34; display_order 1; source `Test_4_Section_4_PDF_Page_091.jpg`.
- **B** = `asset-c38885c8f6f347ff4fc82bd77d11899cbc5aaddc30cfb9661417c3c404236ab9`; applicability Q35–40; display_order 2; source `Test_4_Section_4_PDF_Page_092.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q37 | Q37–40 | B | A |

### C10 / Test 1 / Part 1

ID: `cambridge-10-test-01-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-2178fce027006ff693252b36d5a044134c0a944d23fd0fc5807a071f5f71245a`; applicability Q1–6; display_order 1; source `PDF_002.jpg`.
- **B** = `asset-87f33bf1c42357e1530bcda6eddef59a917004510b65cce6a10de8632f1f8d15`; applicability Q10–10; display_order 2; source `PDF_003.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–6 | A | B |
| Q7 | Q7–10 | B | A |

### C10 / Test 1 / Part 2

ID: `cambridge-10-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-580efbc74c9e4f8c9c38ac6d088902255960a2a17887f7bf443b0b86f58ba688`; applicability Q11–12; display_order 1; source `PDF_004.jpg`.
- **B** = `asset-1b7d2be909968462b719d3ed90755375e4b30b03a5b0248e0499e5f1c60e28bd`; applicability Q13–20; display_order 2; source `PDF_005.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–20 | B | A |

### C10 / Test 1 / Part 3

ID: `cambridge-10-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-85dda2b96a0e507d53487e0edfb8412d9dcbf1bfe9a78289f46bbcd081d62371`; applicability Q21–25; display_order 1; source `PDF_006.jpg`.
- **B** = `asset-d629ce27e47b0b2f87fa8c267cad7e52899cbdc50ba775a9ca18defa97857de2`; applicability Q26–30; display_order 2; source `PDF_007.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–30 | B | A |

### C10 / Test 2 / Part 2

ID: `cambridge-10-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-66627198b4b359bda0460f5db7e5fb7b37c4d0706517c6fa4de42c7d5ed1edeb`; applicability Q11–14; display_order 1; source `PDF_027.jpg`.
- **B** = `asset-8e9adb66622afa74ec1ce9426a0baf52883679ae73e9dd6b24e7fa32990c236c`; applicability Q15–20; display_order 2; source `PDF_028.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–20 | B | A |

### C10 / Test 2 / Part 3

ID: `cambridge-10-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-e6bd4328aa2fd18a07dbfae47141b0ff13621d0b1f1ad4dd0b3b95eb257604d1`; applicability Q21–29; display_order 1; source `PDF_029.jpg`.
- **B** = `asset-3b5e98604394a31b2057b5522c619ca71df07dff3a9c6286fd7ab397788f925d`; applicability Q30–30; display_order 2; source `PDF_030.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |

### C10 / Test 3 / Part 2

ID: `cambridge-10-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-90440110a270a6e2464736463898292d3169511a1dd17d4c4507f29fe7cd6811`; applicability Q11–15; display_order 1; source `PDF_050.jpg`.
- **B** = `asset-f805cdf2b0c21b094c35b04bbcc5eaa6fc2c608497f016440840e38c8b1e618e`; applicability Q16–20; display_order 2; source `PDF_051.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–15 | A | B |
| Q16 | Q16–20 | B | A |

### C10 / Test 3 / Part 3

ID: `cambridge-10-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-9959faa95a8127d30252290ae1fcbe814a24f7a1cbda4c81da8c1c5ff98684d7`; applicability Q21–25; display_order 1; source `PDF_052.jpg`.
- **B** = `asset-d0c55c333d6580420010ea5990686c84fbe33c724320f6369c7ef22e06e6ccf0`; applicability Q26–30; display_order 2; source `PDF_053.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–30 | B | A |

### C10 / Test 4 / Part 1

ID: `cambridge-10-test-04-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-0a4b4fb5a0b6c23fa59afa322210ee5f383ea62f5bbebc160a269ce7972fed6e`; applicability Q1–6; display_order 1; source `PDF_072.jpg`.
- **B** = `asset-3d7d36dfc8eec88c8b51fb644f86b9f941392da9a064e48756147ff78aecb587`; applicability Q7–10; display_order 2; source `PDF_073.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–6 | A | B |
| Q7 | Q7–10 | B | A |

### C10 / Test 4 / Part 2

ID: `cambridge-10-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-12f86ac512d13094016f84cfee30fc08681f5502c746295ba66c734c24fbdabd`; applicability Q11–15; display_order 1; source `PDF_074.jpg`.
- **B** = `asset-915557afea6f9b608bad2712712797b0b172fc5d2fc76d9d7338f3b26559b8ea`; applicability Q16–20; display_order 2; source `PDF_075.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–15 | A | B |
| Q16 | Q16–20 | B | A |

### C10 / Test 4 / Part 3

ID: `cambridge-10-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-190918a00d63c76ad5b2616be2086378973193b8450c92b230dbc827519eea1d`; applicability Q21–24; display_order 1; source `PDF_076.jpg`.
- **B** = `asset-54aa3f941213b9bd5d3f92cbe0d0e61ba19526c18c05e2ff1c1d9f04ef1ec3d1`; applicability Q30–30; display_order 2; source `PDF_077.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–30 | B | A |

### C10 / Test 4 / Part 4

ID: `cambridge-10-test-04-p4`. Видимые вопросы: **Q31–40**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-b0419e1f40c09fbb4ddd20ccd213f25ffeec6f7b30244ce880493518058868d6`; applicability Q31–33; display_order 1; source `PDF_078.jpg`.
- **B** = `asset-6f9084ffa19b01adc33211e028c9c26c6a64efb5a730be743b55e08fd9142a24`; applicability Q34–40; display_order 2; source `PDF_079.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q31 | Q31–33 | A | B |
| Q34 | Q34–40 | B | A |

### C11 / Test 1 / Part 2

ID: `cambridge-11-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-17940cca1a5ab2ae9c10153025ef730436ff498ad216cc579d73a822880cf1b1`; applicability Q11–14; display_order 1; source `Test_1_Section_2_PDF_010.jpg`.
- **B** = `asset-9d9e46ef41ebaa602b8b32e54a65a4a2e07ed9a7da879c40e6fcdc2aedab888a`; applicability Q15–20; display_order 2; source `Test_1_Section_2_PDF_011.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–20 | B | A |

### C11 / Test 2 / Part 2

ID: `cambridge-11-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-14055639b3575bf8dd0cb05d9097c85fb42c06f086bc11f0b696aa58cff9f111`; applicability Q11–16; display_order 1; source `Test_2_Section_2_PDF_033.jpg`.
- **B** = `asset-0fb33145e8919e798ae1dfcd515f726db0309ae3972d95745710878b0cebdc47`; applicability Q17–20; display_order 2; source `Test_2_Section_2_PDF_034.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–16 | A | B |
| Q17 | Q17–20 | B | A |

### C11 / Test 2 / Part 3

ID: `cambridge-11-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-97dc8338e3407f9d8e4ce7894af82d9d29089265a12c931131049b1093d46c6d`; applicability Q21–26; display_order 1; source `Test_2_Section_3_PDF_035.jpg`.
- **B** = `asset-5c320ddcb5e64709dc1780b6d7b6d5b227ac2a218a0588fd31f8fb9dee2eb0aa`; applicability Q27–30; display_order 2; source `Test_2_Section_3_PDF_036.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–26 | A | B |
| Q27 | Q27–28 | B | A |
| Q29 | Q29–30 | B | A |

### C11 / Test 3 / Part 1

ID: `cambridge-11-test-03-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-d9da3c3bd02795d47109a6eb135ed7a974bbd7731e9edfb1f431db1d38997421`; applicability Q1–6; display_order 1; source `Test_3_Section_1_PDF_055.jpg`.
- **B** = `asset-f910b9d2bd8ed6ba3ca278de0f70bce88e8910e46b723975b26d3cac16a1caed`; applicability Q7–10; display_order 2; source `Test_3_Section_1_PDF_056.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–6 | A | B |
| Q7 | Q7–10 | B | A |

### C11 / Test 3 / Part 2

ID: `cambridge-11-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-36c63fab77983baf04a4093dbcbd6ebdb68cdb699eb9d756e1c7029c1f6e17cb`; applicability Q11–15; display_order 1; source `Test_3_Section_2_PDF_057.jpg`.
- **B** = `asset-09fccdb23d339cdeb0ac740e79aa710da41fb225ecf7144290d7a05aaa35c2da`; applicability Q16–20; display_order 2; source `Test_3_Section_2_PDF_058.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–15 | A | B |
| Q16 | Q16–20 | B | A |

### C11 / Test 3 / Part 3

ID: `cambridge-11-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-4cf0b32b3eca0553fd6d0b43bd9eb2598fe4b8e4e154a086cc8580cfdd788901`; applicability Q21–26; display_order 1; source `Test_3_Section_3_PDF_059.jpg`.
- **B** = `asset-db49345a1390c77b0da9f85f44b130df4fcd62a13c4730edf7c14973242e846a`; applicability Q27–30; display_order 2; source `Test_3_Section_3_PDF_060.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–26 | A | B |
| Q27 | Q27–30 | B | A |

### C11 / Test 4 / Part 1

ID: `cambridge-11-test-04-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-05ebd8bf1dcd235a9256bfbe9e4da81d51e8c52b53415631d712467fbec32005`; applicability Q1–7; display_order 1; source `Test_4_Section_1_PDF_078.jpg`.
- **B** = `asset-c0d5fd26a3610da5bdf8fe7a48e10ea62a86f4baae916b18a706361477d16614`; applicability Q8–10; display_order 2; source `Test_4_Section_1_PDF_079.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–7 | A | B |
| Q8 | Q8–10 | B | A |

### C11 / Test 4 / Part 2

ID: `cambridge-11-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-d194da8a39c35dacc2662754550f726b3cfeb623b7c5ff72813e42205bdb4fcd`; applicability Q11–16; display_order 1; source `Test_4_Section_2_PDF_080.jpg`.
- **B** = `asset-77de1e8ffb04bd0e4aea475e10f19ac90cd9fa6e40bc7b8972300a42a524e8c2`; applicability Q17–20; display_order 2; source `Test_4_Section_2_PDF_081.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–20 | B | A |

### C11 / Test 4 / Part 3

ID: `cambridge-11-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-2d87db7c3505c752816f784d4de1d0ecb19c6847acb55f22753fb6f6ed903b3a`; applicability Q21–26; display_order 1; source `Test_4_Section_3_PDF_082.jpg`.
- **B** = `asset-b498b03cbb4b0ff35a35940108bbfc4c1efee556a40b6c5ee1fee8ada8b05878`; applicability Q27–30; display_order 2; source `Test_4_Section_3_PDF_083.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–26 | A | B |
| Q27 | Q27–30 | B | A |

### C12 / Test 5 / Part 2

ID: `cambridge-12-test-05-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-0acb08433909d93b2a16235364751e4bc845b0e660007bb8b8074b86dae0c01b`; applicability Q11–16; display_order 1; source `Test_5_Section_2_PDF_012.png`.
- **B** = `asset-eef061a71e06de556e11776c7020bd3899670ebeeef1dacfe96eb98e37676751`; applicability Q17–20; display_order 2; source `Test_5_Section_2_PDF_013.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–16 | A | B |
| Q17 | Q17–20 | B | A |

### C12 / Test 6 / Part 2

ID: `cambridge-12-test-06-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-6487a907147771e32dd9d8754b32a378c31f37d8565f2032debc72dbe0f8b184`; applicability Q11–15; display_order 1; source `Test_6_Section_2_PDF_031.png`.
- **B** = `asset-a5461751e8a900d97ea6c854277e263138b31d97a3ecc060ff1cc6970dce4c20`; applicability Q16–20; display_order 2; source `Test_6_Section_2_PDF_032.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–15 | A | B |
| Q16 | Q16–20 | B | A |

### C12 / Test 6 / Part 3

ID: `cambridge-12-test-06-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-f4f2caffd4444d0f85aea074fdbfbf703bd1a75c3ca6912e311e524f5ad7f03c`; applicability Q21–25; display_order 1; source `Test_6_Section_3_PDF_033.png`.
- **B** = `asset-ab4043b2394de70fab8378271cb9a1450e825e10719c76f012ff646a38f86fe6`; applicability Q26–30; display_order 2; source `Test_6_Section_3_PDF_034.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–30 | B | A |

### C12 / Test 7 / Part 2

ID: `cambridge-12-test-07-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-62483bef6aa79934335302a1c5766c6be0297429f89c773a08ac366dd94d5dfd`; applicability Q11–17; display_order 1; source `Test_7_Section_2_PDF_054.png`.
- **B** = `asset-361d57e11c8770ddb8ab6468f78048dd47cb01886240a6cf6ce6040562ce948f`; applicability Q18–20; display_order 2; source `Test_7_Section_2_PDF_055.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–17 | A | B |
| Q18 | Q18–20 | B | A |

### C12 / Test 7 / Part 3

ID: `cambridge-12-test-07-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-976788245acd899feb953dd7b78c462a19428da73158c73e598488c1381830a0`; applicability Q21–26; display_order 1; source `Test_7_Section_3_PDF_056.png`.
- **B** = `asset-e8cd34017ba2dee686fdeb91317f76b702ce45ac824fe2793ed80c4c03791fce`; applicability Q27–30; display_order 2; source `Test_7_Section_3_PDF_057.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–26 | A | B |
| Q27 | Q27–30 | B | A |

### C12 / Test 8 / Part 2

ID: `cambridge-12-test-08-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-81504b909e34167ccb596bfb1dc89434efc0405c1539dba6a9d4b23e4dd7eefd`; applicability Q11–14; display_order 1; source `Test_8_Section_2_PDF_075.png`.
- **B** = `asset-ef0a1e3ad794df809bcdfeafd1e03411e9fb0aea2545cdd9a7308655c42cc144`; applicability Q15–20; display_order 2; source `Test_8_Section_2_PDF_076.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–20 | B | A |

### C12 / Test 8 / Part 3

ID: `cambridge-12-test-08-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-fb8307db07b8d1dbd5a5a7ce629dceecfb525f90d6aa30003d03c2a5b2ca9df2`; applicability Q21–24; display_order 1; source `Test_8_Section_3_PDF_077.png`.
- **B** = `asset-bfc5ef86f4b028535b2205a65ca9f46991e970d24a2258f9d1029bdde3a7f16d`; applicability Q25–30; display_order 2; source `Test_8_Section_3_PDF_078.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–30 | B | A |

### C13 / Test 1 / Part 2

ID: `cambridge-13-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-9d87462fd83478dd4a152118b02f691d59d2d0347ca74fb34046db9c7fbac046`; applicability Q11–13; display_order 1; source `PDF_012.png`.
- **B** = `asset-22f23edd16341bfbbbb259333410765370071fb131d6bd68685c4fe2e1979ee0`; applicability Q12–20; display_order 2; source `PDF_013.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q14 | Q14–20 | B | A |

### C13 / Test 1 / Part 3

ID: `cambridge-13-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-c66231d5633585ce30322460490315044e81e434375e1094fc47c9f23e0c25f6`; applicability Q21–25; display_order 1; source `PDF_014.png`.
- **B** = `asset-e6b144d4a1a7f0150e051ae7f7646a06ebec42ebd563a592e7f2c9b906c0b77d`; applicability Q26–30; display_order 2; source `PDF_015.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–30 | B | A |

### C13 / Test 2 / Part 2

ID: `cambridge-13-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-9c62a25856ff2a0292417d4fc28c51e8af7c5476d13e60fe3650691ec0c71631`; applicability Q11–16; display_order 1; source `PDF_034.png`.
- **B** = `asset-e6be0feb3baf7660cfa050445efea936a9f63062adbc72b4e0a6d58b2de6d039`; applicability Q17–20; display_order 2; source `PDF_035.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–18 | B | A |
| Q19 | Q19–20 | B | A |

### C13 / Test 2 / Part 3

ID: `cambridge-13-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-a5290e603f45d54811281c2b1fd7d965b907776fe6d0ec168c104b0892c5d371`; applicability Q21–25; display_order 1; source `PDF_036.png`.
- **B** = `asset-1afa9c5940437db0ff408db2a0639f82936cd90a1f512a0b30c09cfb3e84ef75`; applicability Q26–30; display_order 2; source `PDF_037.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–30 | B | A |

### C13 / Test 3 / Part 2

ID: `cambridge-13-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-cb1fb5822901f765449afce7fe1dac1e5814d48222001fd0b732791951f51882`; applicability Q11–16; display_order 1; source `PDF_056.png`.
- **B** = `asset-518dc2e150868016ebb6a2fa07eb9639b9d949969290bc59a21c7de23cdd505d`; applicability Q17–20; display_order 2; source `PDF_057.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–18 | B | A |
| Q19 | Q19–20 | B | A |

### C13 / Test 3 / Part 3

ID: `cambridge-13-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-56fb66aaad521917bbbf1f5357c155916e1fd89a590b567c8ed1d0cdb84aefe6`; applicability Q21–24; display_order 1; source `PDF_058.png`.
- **B** = `asset-a6b2b36d1833e6b57661c703c70ff04ca3a983c678a36c6d137fc34a908cc364`; applicability Q25–30; display_order 2; source `PDF_059.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–30 | B | A |

### C13 / Test 4 / Part 2

ID: `cambridge-13-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-6566e56507265d6d1af686e11e59f4c7b00b97672e177d629034d337e34bc868`; applicability Q11–16; display_order 1; source `PDF_078.png`.
- **B** = `asset-e7417f555a68e7b7ba6e74e4899ccfa15777b0c506e3aee1d747b39d8a72d662`; applicability Q17–20; display_order 2; source `PDF_079.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–20 | B | A |

### C13 / Test 4 / Part 3

ID: `cambridge-13-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-b130f4d081ff24d7a764de2b5696101830dc07a32b4111941a56ca63a24a29a2`; applicability Q21–26; display_order 1; source `PDF_080.png`.
- **B** = `asset-96e7155e1312ec6fae9c41c42af9b87e2e93d5fe08563422d598f28cb58f4e58`; applicability Q27–30; display_order 2; source `PDF_081.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–26 | A | B |
| Q27 | Q27–28 | B | A |
| Q29 | Q29–30 | B | A |

### C14 / Test 1 / Part 2

ID: `cambridge-14-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-0c1b7dd10c41788f338bb76850fbad3bfb6babf70fd553d0fdd7ab6670e52d0a`; applicability Q11–14; display_order 1; source `Test_1_Source_PDF_011.png`.
- **B** = `asset-fd87b64a7714b849625759af802242c2a72effbbdccb297dbc07d5ff41e9a5a1`; applicability Q15–20; display_order 2; source `Test_1_Source_PDF_012.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–20 | B | A |

### C14 / Test 1 / Part 3

ID: `cambridge-14-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-f0e2b898c46488cc6180d1a6eb7b0436f4aa545715ced76dbbcfecb18d415327`; applicability Q21–25; display_order 1; source `Test_1_Source_PDF_013.png`.
- **B** = `asset-0285f980c75a6fbd269a6470c35f2f7109c9056800a5da58832379299d688dea`; applicability Q26–30; display_order 2; source `Test_1_Source_PDF_014.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–30 | B | A |

### C14 / Test 2 / Part 2

ID: `cambridge-14-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **browser verified (initial state, Exam + Review); other states component verified**.

- **A** = `asset-395be7a8ab0df31a497d69048e36a027ace0d9a94ebed9c0b3818ff43ecc13e4`; applicability Q11–15; display_order 1; source `Test_2_Source_PDF_033.png`.
- **B** = `asset-104795909c64a6f4907769817c8623a06ab48e7effc3d7e1c7bdf53f1a3d6455`; applicability Q16–20; display_order 2; source `Test_2_Source_PDF_034.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–15 | A | B |
| Q16 | Q16–20 | B | A |

### C14 / Test 2 / Part 3

ID: `cambridge-14-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-493ce740f58542574192c1bd48a99122c62242dcd1e294c06b2e8bd8b525c95f`; applicability Q21–24; display_order 1; source `Test_2_Source_PDF_035.png`.
- **B** = `asset-d7de5a858ebde4cce35dba84c5aafec9385669cdbbf6d20e2db281f706ffbd80`; applicability Q25–30; display_order 2; source `Test_2_Source_PDF_036.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–30 | B | A |

### C14 / Test 3 / Part 2

ID: `cambridge-14-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-42da346f944f4cb671f8c83b6f58d54e70042cfed40eba6074c145b04c048c21`; applicability Q11–14; display_order 1; source `Test_3_Source_PDF_054.png`.
- **B** = `asset-875134591bc0e78d96ce0c4a3cdabf8c79845be6fa80c6bd448e579ab31864b1`; applicability Q15–20; display_order 2; source `Test_3_Source_PDF_055.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–20 | B | A |

### C14 / Test 3 / Part 3

ID: `cambridge-14-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-8096835b8697593c5903550ac7a7b03c9c5e3e8d0a781b0a6a30e8282fc036b8`; applicability Q21–26; display_order 1; source `Test_3_Source_PDF_056.png`.
- **B** = `asset-2e9dc02c73258a554376ba2258f35985294b0549b86d92af077ff5263a383ff7`; applicability Q27–30; display_order 2; source `Test_3_Source_PDF_057.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–26 | A | B |
| Q27 | Q27–30 | B | A |

### C14 / Test 4 / Part 1

ID: `cambridge-14-test-04-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-7dd9ca84cc581141d70077c13802913e1a81cf17d719505ac3534376698c33ff`; applicability Q1–7; display_order 1; source `Test_4_Source_PDF_075.png`.
- **B** = `asset-1d27d9480064516d970d6e404a35d8f9934784d5c4db23681a45fd3f9098f7f9`; applicability Q8–10; display_order 2; source `Test_4_Source_PDF_076.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–7 | A | B |
| Q8 | Q8–10 | B | A |

### C14 / Test 4 / Part 2

ID: `cambridge-14-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-4a817936d4a423f1f763e522f92edb633b84b22cb3aed1ecefc311547ed5392b`; applicability Q11–16; display_order 1; source `Test_4_Source_PDF_077.png`.
- **B** = `asset-243956cc788f6318ba8ef045b8f2d0bff77c1531fc8468155e661621b463f88e`; applicability Q17–20; display_order 2; source `Test_4_Source_PDF_078.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–18 | B | A |
| Q19 | Q19–20 | B | A |

### C14 / Test 4 / Part 3

ID: `cambridge-14-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-1b3ce060d3c72f2d6a919b026690ac315d719947869130e0f7d574a14f241034`; applicability Q21–25; display_order 1; source `Test_4_Source_PDF_079.png`.
- **B** = `asset-3c4c944aa594d0b917a2ddd83c55464aa1989950792cbd3b10ac3e7d421b6e36`; applicability Q26–30; display_order 2; source `Test_4_Source_PDF_080.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–30 | B | A |

### C16 / Test 1 / Part 2

ID: `cambridge-16-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-80cb87f90c2417685326eaf3ba35c6d2d97dc4ea92f5d5532419b0c91f5e72dc`; applicability Q11–14; display_order 1; source `PDF_013.jpg`.
- **B** = `asset-db4c6c794d0ede138229f78830a1963dacf94679e6182c0ad55d498431be0208`; applicability Q12–20; display_order 2; source `PDF_014.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q15 | Q15–20 | B | A |

### C16 / Test 1 / Part 3

ID: `cambridge-16-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-9561a4ae9612238a1ae905b2fe197aec1b92efb24dde99b9fb3f8876ee73880b`; applicability Q21–24; display_order 1; source `PDF_015.jpg`.
- **B** = `asset-fb0c01a3cab74e7c0a61bdd147d9400599ca12a74b4efbd3b8ba0fe58cdd2f81`; applicability Q25–30; display_order 2; source `PDF_016.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–30 | B | A |

### C16 / Test 2 / Part 2

ID: `cambridge-16-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-7629e000d53d2bca77efa1a941cd80f964195c77823903a2fbd2db850bcba2ce`; applicability Q11–15; display_order 1; source `PDF_035.jpg`.
- **B** = `asset-c03147bfa28412a8e713147f29b934b2f2bf91647bddb7fce8c372893bc00e8e`; applicability Q16–20; display_order 2; source `PDF_036.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–15 | A | B |
| Q16 | Q16–18 | B | A |
| Q19 | Q19–20 | B | A |

### C16 / Test 2 / Part 3

ID: `cambridge-16-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-8bc97980c00685105b1e59c6f54c0d26f5f9635a0153c85f537466ce2a27c476`; applicability Q21–24; display_order 1; source `PDF_037.jpg`.
- **B** = `asset-b572d0bdb82d6b03e756cca9be3a693b7e63f6f31e4a639e8ee1aefc9df03230`; applicability Q25–30; display_order 2; source `PDF_038.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–30 | B | A |

### C16 / Test 3 / Part 2

ID: `cambridge-16-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-83e8c4a9d95829a09f9f748f1754c2832406d14af2aed39ba80fe2ae530928d3`; applicability Q11–14; display_order 1; source `PDF_058.jpg`.
- **B** = `asset-d1c282046f6e5485d47361edbb172321be9ddee3ad1f891487e29b9a1e445e7c`; applicability Q15–20; display_order 2; source `PDF_059.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–20 | B | A |

### C16 / Test 3 / Part 3

ID: `cambridge-16-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-764881c9965bc5636dc8285cf9c0e5e684f3094ab11e6b27c85981533a1ebefe`; applicability Q21–24; display_order 1; source `PDF_060.jpg`.
- **B** = `asset-d6c4a3f117c6a94a72f53c095a75b232c59d5bd11ba6730b1a91b3c95424fbe6`; applicability Q25–30; display_order 2; source `PDF_061.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–30 | B | A |

### C16 / Test 4 / Part 2

ID: `cambridge-16-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-dcb9ad31be1b62ea0f709d408e682b85744274b0625fcc970e155c3f0d66a272`; applicability Q11–14; display_order 1; source `PDF_079.jpg`.
- **B** = `asset-635b78d9974d80b4c319b1b03da2979a8abb463987a95fd8c4e601e73b5e6a1f`; applicability Q15–20; display_order 2; source `PDF_080.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–20 | B | A |

### C16 / Test 4 / Part 3

ID: `cambridge-16-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-5ea8958077bf9ce1abcdec8314374bb1bab6c168b46dbf1dbab259f1b84f6249`; applicability Q21–24; display_order 1; source `PDF_081.jpg`.
- **B** = `asset-69ab3639c4e83b7700be04c0bfb38a31edcbe920b1cadca27f19ee0cc9457dbd`; applicability Q25–30; display_order 2; source `PDF_082.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–30 | B | A |

### C17 / Test 1 / Part 2

ID: `cambridge-17-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-9f7a2bd28f0497c4fbf3eb87bb305a76fe98feaaa0a71a7566d823a2219d3671`; applicability Q11–14; display_order 1; source `Test_1_Part_2_PDF_Page_004.jpg`.
- **B** = `asset-ea57749f770979b23f342a00387e1a6747c4bf88e3c4abc139fa905087d1cdc5`; applicability Q15–20; display_order 2; source `Test_1_Part_2_PDF_Page_005.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–16 | B | A |
| Q17 | Q17–18 | B | A |
| Q19 | Q19–20 | B | A |

### C17 / Test 1 / Part 3

ID: `cambridge-17-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-6221a727605f4c32b692a1de2e18035ee2e5aa4dd5ff7c16be6366396a62b196`; applicability Q21–26; display_order 1; source `Test_1_Part_3_PDF_Page_006.jpg`.
- **B** = `asset-881ad4c66ef552591ab22aa10160a20e1194df716d3a1dac4e52075f46ab1542`; applicability Q27–30; display_order 2; source `Test_1_Part_3_PDF_Page_007.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–26 | A | B |
| Q27 | Q27–30 | B | A |

### C17 / Test 2 / Part 2

ID: `cambridge-17-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-6f16167250074f9a1203a9b7ae38ebb8b369f5059de0fdf8d0a09d82cf7e97b6`; applicability Q11–14; display_order 1; source `Test_2_Part_2_PDF_Page_025.jpg`.
- **B** = `asset-b3c98b31ca1d8fed8fe9d7c9b67429fc71b03576257e6df8b64d2c03f7fa8491`; applicability Q15–20; display_order 2; source `Test_2_Part_2_PDF_Page_026.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–20 | B | A |

### C17 / Test 2 / Part 3

ID: `cambridge-17-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-e99db5f3ad668885b92e35220805da4dd79248c7cbd4ac8ba2c03f799dc9990e`; applicability Q21–27; display_order 1; source `Test_2_Part_3_PDF_Page_027.jpg`.
- **B** = `asset-503ab8a2b5483afe3f6ccb2f3e1c734a38b73483a6c1b366490aa0afe38ce251`; applicability Q28–30; display_order 2; source `Test_2_Part_3_PDF_Page_028.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–27 | A | B |
| Q28 | Q28–30 | B | A |

### C17 / Test 3 / Part 2

ID: `cambridge-17-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-5f26ad8511f540c0b05481be33ffb182190d2579aa1a923521af3dea99f3dbbc`; applicability Q11–15; display_order 1; source `Test_3_Part_2_PDF_Page_047.jpg`.
- **B** = `asset-f7d14666fbcc34816b9bda3dfa6962c6c4587c0ce468303d70ceecc43940a932`; applicability Q16–20; display_order 2; source `Test_3_Part_2_PDF_Page_048.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–15 | A | B |
| Q16 | Q16–20 | B | A |

### C17 / Test 3 / Part 3

ID: `cambridge-17-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-80c04048d9f9a9995449ed4feb3d91a1d7d1d5a7f88872a559a50043c36426b3`; applicability Q21–24; display_order 1; source `Test_3_Part_3_PDF_Page_049.jpg`.
- **B** = `asset-c8135ec823907d076305f65c7214148be996be262cb41ca6fe04cbb09de74506`; applicability Q25–30; display_order 2; source `Test_3_Part_3_PDF_Page_050.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–30 | B | A |

### C17 / Test 4 / Part 2

ID: `cambridge-17-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-b9ff1ee656f3d3d396acab9947b0a469cede3e80d6d32a59fcbb5f5441b56544`; applicability Q11–14; display_order 1; source `Test_4_Part_2_PDF_Page_069.jpg`.
- **B** = `asset-3a0cc99f8ae28547523be4a3eea2be4e7cd231176137142753da3dddf1bef0c3`; applicability Q15–20; display_order 2; source `Test_4_Part_2_PDF_Page_070.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–20 | B | A |

### C17 / Test 4 / Part 3

ID: `cambridge-17-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-ed536e378de56457f82c7ab713e7d004a7ed7c7bfcb956cb8375e6edd6b60505`; applicability Q21–24; display_order 1; source `Test_4_Part_3_PDF_Page_071.jpg`.
- **B** = `asset-29506feec8c2e460c6cff382d1427fcff12d51f4cf203f04d944ac663ffc48d1`; applicability Q25–30; display_order 2; source `Test_4_Part_3_PDF_Page_072.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–30 | B | A |

### C18 / Test 1 / Part 2

ID: `cambridge-18-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-f2d6cd666159861923f90c3ecbf78e64cc47584564cf0b4c20eae01819bdcec4`; applicability Q11–15; display_order 1; source `Test_1_Part_2_PDF_013.png`.
- **B** = `asset-25e57e89cc1403406babc6fef91cd74ed53c67cc06e59592d0c471fca3ded51d`; applicability Q12–20; display_order 2; source `Test_1_Part_2_PDF_014.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q16 | Q16–20 | B | A |

### C18 / Test 1 / Part 3

ID: `cambridge-18-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-8084fdb63a764a7ea1b17bcc03fc15b88e3883b5f787ccca2b8b7926a9477334`; applicability Q21–26; display_order 1; source `Test_1_Part_3_PDF_015.png`.
- **B** = `asset-1bfd7e2fcd0a624a360cda4542ff59e709a40a8c99bee3070287656d65ea6eef`; applicability Q27–30; display_order 2; source `Test_1_Part_3_PDF_016.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–26 | A | B |
| Q27 | Q27–28 | B | A |
| Q29 | Q29–30 | B | A |

### C18 / Test 2 / Part 1

ID: `cambridge-18-test-02-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-e1c88aac896f4fb90c9fcf2389d9f8cf09ff8b34eb76d33b86649df089c01bde`; applicability Q1–5; display_order 1; source `Test_2_Part_1_PDF_034.png`.
- **B** = `asset-68b10200319f1b01396fc2a03ad2021de965f0b418da71c3019cae11d114754a`; applicability Q6–10; display_order 2; source `Test_2_Part_4_PDF_035.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–5 | A | B |
| Q6 | Q6–10 | B | A |

### C18 / Test 2 / Part 2

ID: `cambridge-18-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-5fd1e08534a18941fcfc180cb5350197535f2002dc31e895a084a91f52a48587`; applicability Q11–14; display_order 1; source `Test_2_Part_2_PDF_036.png`.
- **B** = `asset-59b49f2c5c251250da7bcd6e14851137e5056d63fb06510281137492fe9e68c3`; applicability Q15–20; display_order 2; source `Test_2_Part_2_PDF_037.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–20 | B | A |

### C18 / Test 2 / Part 3

ID: `cambridge-18-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-459f949de1bfcc5a833f2e11f9740f5985b2c168d88a5193f5ac231fc964cb4c`; applicability Q21–26; display_order 1; source `Test_2_Part_3_PDF_038.png`.
- **B** = `asset-b4f6399cbb4d4eefbe3de07d81f0a617d6f659fbb5c0dd26d57e3ac40bf420c7`; applicability Q27–30; display_order 2; source `Test_2_Part_3_PDF_039.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–26 | A | B |
| Q27 | Q27–30 | B | A |

### C18 / Test 3 / Part 2

ID: `cambridge-18-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-f67573c3ab53a2054a096a85ca623be7e5d59b5a52feef52a1d4870f510682f3`; applicability Q11–14; display_order 1; source `Test_3_Part_2_PDF_058.png`.
- **B** = `asset-923d946907bc1c141359eaa68a60ddc6aaec89e95c395e356680ba2b43363162`; applicability Q15–20; display_order 2; source `Test_3_Part_2_PDF_059.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–20 | B | A |

### C18 / Test 3 / Part 3

ID: `cambridge-18-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-af98851d9bd6363970f9c6efb73f40337965285c266ed220df93dd5e13eb5b7e`; applicability Q21–24; display_order 1; source `Test_3_Part_3_PDF_060.png`.
- **B** = `asset-df97a6add136d194b7c65bc46a013f62b3b83d19a9b407772b22ca4e5c7e5008`; applicability Q25–30; display_order 2; source `Test_3_Part_3_PDF_061.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–30 | B | A |

### C18 / Test 4 / Part 2

ID: `cambridge-18-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-497062bf68ba7c802e9cfc841288b928b991f53a977caad4b2165bcc0172ba8d`; applicability Q11–14; display_order 1; source `Test_4_Part_2_PDF_081.png`.
- **B** = `asset-8a6dbf1fc2c8b17e7219ea89c1b9ba82bd41426e9af397827f2bca4038a3bc1f`; applicability Q15–20; display_order 2; source `Test_4_Part_2_PDF_082.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–14 | A | B |
| Q15 | Q15–20 | B | A |

### C18 / Test 4 / Part 3

ID: `cambridge-18-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-f2fb9114261f44661b182078af54b9f2fb7a8599e14cbe53aae00b90a189797a`; applicability Q21–27; display_order 1; source `Test_4_Part_3_PDF_083.png`.
- **B** = `asset-12b916a45b019abd3e44180c524ef743ed49ad39e12dd24b3e5d5f4da50009ad`; applicability Q28–30; display_order 2; source `Test_4_Part_3_PDF_084.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–27 | A | B |
| Q28 | Q28–30 | B | A |

### C19 / Test 1 / Part 2

ID: `cambridge-19-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-73fc50e59bfdb3902862c603837ec32d0ef372c1fac03e370c8f986be5a400a4`; applicability Q11–15; display_order 1; source `Test_1_Original_Listening_PDF_Page_010.jpg`.
- **B** = `asset-82649ba5ba479dac088aae18bcd700d7af5a19a373edcfcf168431e2f550bca5`; applicability Q16–20; display_order 2; source `Test_1_Original_Listening_PDF_Page_011.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–15 | A | B |
| Q16 | Q16–20 | B | A |

### C19 / Test 1 / Part 3

ID: `cambridge-19-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-6f9d421b773f07d23e7a15f0f6895a922472be8d7f948da3ad99ee0ecb61da65`; applicability Q21–24; display_order 1; source `Test_1_Original_Listening_PDF_Page_012.jpg`.
- **B** = `asset-8ea3400aefd7ff82455df13dd8fff7625d8f3bb0a23b682b045bded5b468a6ad`; applicability Q25–30; display_order 2; source `Test_1_Original_Listening_PDF_Page_013.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–30 | B | A |

### C19 / Test 2 / Part 1

ID: `cambridge-19-test-02-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-299e453ae751d69896a7875173e5e498d3b2cf48a4f223a85ce28fa8f365a7cd`; applicability Q1–6; display_order 1; source `Test_2_Original_Listening_PDF_Page_032.jpg`.
- **B** = `asset-ac9d58bb9525d91c96eab96d750e95f904b0fffbafeaa093a3233b66432879eb`; applicability Q5–10; display_order 2; source `Test_2_Original_Listening_PDF_Page_033.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q7 | Q7–10 | B | A |

### C19 / Test 2 / Part 2

ID: `cambridge-19-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-81be6261ea9d16e367cd44540da002d2e24e96a56f7e31a2f1b0a5563d881447`; applicability Q11–16; display_order 1; source `Test_2_Original_Listening_PDF_Page_034.jpg`.
- **B** = `asset-14759f1eaa0d002cf58dc0ed1222a1eb6ea1f946b0758b5e1efea4fb538bf1b4`; applicability Q17–20; display_order 2; source `Test_2_Original_Listening_PDF_Page_035.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–18 | B | A |
| Q19 | Q19–20 | B | A |

### C19 / Test 2 / Part 3

ID: `cambridge-19-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-24ca1e7902decceec214946d8860f6bfaeb6d97130ea9a0e0a257d73192de62a`; applicability Q21–24; display_order 1; source `Test_2_Original_Listening_PDF_Page_036.jpg`.
- **B** = `asset-8e8447a8ecae480806dfac5663ab0356845ed184bcd74f728038057c2c1e71d7`; applicability Q25–30; display_order 2; source `Test_2_Original_Listening_PDF_Page_037.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–24 | A | B |
| Q25 | Q25–28 | B | A |
| Q29 | Q29–30 | B | A |

### C19 / Test 3 / Part 1

ID: `cambridge-19-test-03-p1`. Видимые вопросы: **Q1–10**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **browser verified (initial state, Exam + Review); other states component verified**.

- **A** = `asset-aee3070b476dd4d73aa3c7c3794a7a4289dc435e9e78596c9d32ac5e1b70210c`; applicability Q1–6; display_order 1; source `Test_3_Original_Listening_PDF_Page_054.jpg`.
- **B** = `asset-fc1395d4fe695adbe5c0a3ef758d1dfdcc345cb47bf120ca570defdb375b4ed4`; applicability Q7–10; display_order 2; source `Test_3_Original_Listening_PDF_Page_055.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q1 | Q1–6 | A | B |
| Q7 | Q7–10 | B | A |

### C19 / Test 3 / Part 2

ID: `cambridge-19-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-14a83d0a73ad1056c19b03b78dbc0e64d3a6aa826fdc674c3865791d61777c3a`; applicability Q11–16; display_order 1; source `Test_3_Original_Listening_PDF_Page_056.jpg`.
- **B** = `asset-eaacff16b9447f757bdd3fdd544a37dc7625787e61577e006f66545b293e10b5`; applicability Q17–20; display_order 2; source `Test_3_Original_Listening_PDF_Page_057.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–18 | B | A |
| Q19 | Q19–20 | B | A |

### C19 / Test 3 / Part 3

ID: `cambridge-19-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-6c030ba222637ca509b61b7f68572e87fc723bdae671a1163ece8bcb67f8c6bf`; applicability Q21–25; display_order 1; source `Test_3_Original_Listening_PDF_Page_058.jpg`.
- **B** = `asset-c603b260315f1d0921a8cec32999d809ce6f8522381643831e85102b44395ebe`; applicability Q26–30; display_order 2; source `Test_3_Original_Listening_PDF_Page_059.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–30 | B | A |

### C19 / Test 4 / Part 2

ID: `cambridge-19-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-e585c7ab07e377ee21e7435e053b9e42770f8605c00e0d83e23a3d51605254f0`; applicability Q11–14; display_order 1; source `Test_4_Original_Listening_PDF_Page_078.jpg`.
- **B** = `asset-e9342d1de45198900cc2af4d85095cdfb8ec876cf4f44e46e363f6a2555af1d1`; applicability Q15–20; display_order 2; source `Test_4_Original_Listening_PDF_Page_079.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–18 | B | A |
| Q19 | Q19–20 | B | A |

### C19 / Test 4 / Part 3

ID: `cambridge-19-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-9a5536f929263d00488bd14b75220f3fd0bcd782882ce21985d22d0f8ccf2afb`; applicability Q21–25; display_order 1; source `Test_4_Original_Listening_PDF_Page_080.jpg`.
- **B** = `asset-4ab104f76d32efaceef91c0a4ff3841b26d77a5e8701d02f4db22a8831c90357`; applicability Q26–30; display_order 2; source `Test_4_Original_Listening_PDF_Page_081.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |
| Q26 | Q26–30 | B | A |

### C20 / Test 1 / Part 2

ID: `cambridge-20-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-df7fe565fa233931bc24f7ba2a76b6039f690712b8e4456fc3ef8b344e1acc6a`; applicability Q11–16; display_order 1; source `Test_1_Part_2_PDF_Page_004.jpg`.
- **B** = `asset-995a7138e04e68c08b59326edeac4856033bef50bc56319774b765cac9cf37d0`; applicability Q17–20; display_order 2; source `Test_1_Part_2_PDF_Page_005.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–18 | B | A |
| Q19 | Q19–20 | B | A |

### C20 / Test 1 / Part 3

ID: `cambridge-20-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-8619a60c00c7f51c972db56fd12eb31becc9304f92d613b6150c69da2678cc0a`; applicability Q21–26; display_order 1; source `Test_1_Part_3_PDF_Page_006.jpg`.
- **B** = `asset-0669ea4692c77c8e2de21a50de23b19352a2bb23926160a68d6e6afa92dfa69e`; applicability Q27–30; display_order 2; source `Test_1_Part_3_PDF_Page_007.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–26 | A | B |
| Q27 | Q27–30 | B | A |

### C20 / Test 2 / Part 2

ID: `cambridge-20-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-a547091f1582e00720424ce0b88b864f22fc9a99d5c6f29d5667be0b39163264`; applicability Q11–16; display_order 1; source `Test_2_Part_2_PDF_Page_041.jpg`.
- **B** = `asset-7ad6139425f15820ff15eb6dd43bae90a8737f0e61b4dba7d00546832c1e00c0`; applicability Q17–20; display_order 2; source `Test_2_Part_2_PDF_Page_042.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A | B |
| Q17 | Q17–20 | B | A |

### C20 / Test 2 / Part 3

ID: `cambridge-20-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-64e48c83869d7f186f38d524031757b4402f767c322809819cf16f4b05def188`; applicability Q21–30; display_order 1; source `Test_2_Part_3_PDF_Page_043.jpg`.
- **B** = `asset-bc9a789210ada9163454424e3ad7f61c997ca6cd4946559ad426d995e36e179b`; applicability Q28–30; display_order 2; source `Test_2_Part_3_PDF_Page_044.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–25 | A | B |

### C20 / Test 3 / Part 2

ID: `cambridge-20-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B, C, D**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-c9d624c24629d35ed4c23ed746c52991fedf3843087cb1732c39e5876629e4e8`; applicability Q11–16; display_order 1; source `Test_3_Part_2_PDF_Page_078.jpg`.
- **B** = `asset-553775d0bad66c0489a6183815005dcc577f042d4aea30433d2d448d10808d6c`; applicability Q16–16; display_order 2; source `Test_3_Part_2_PDF_Page_079.jpg`.
- **C** = `asset-6af99e38d09ecdf8f73b81049173e573a18b59799a00b4dc25f931ca2eaf1ad0`; applicability Q17–19; display_order 3; source `Test_3_Part_2_PDF_Page_081.jpg`.
- **D** = `asset-fc9097eeee495a9e588bff05b9e16b927b0517935daa9ca2c4512786ba5a3d48`; applicability Q17–20; display_order 4; source `Test_3_Part_2_PDF_Page_080.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–16 | A, B | C, D |
| Q17 | Q17–20 | C, D | A, B |

### C20 / Test 3 / Part 3

ID: `cambridge-20-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-792830424c452723a1f5a37c7ac6bd7ee91d1d54371736a94c6370352322e8c4`; applicability Q21–26; display_order 1; source `Test_3_Part_3_PDF_Page_082.jpg`.
- **B** = `asset-8895aa9f3c45d24e4678c9516b579a3087937b82e32393396dcb1655496943af`; applicability Q26–30; display_order 2; source `Test_3_Part_3_PDF_Page_083.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q27 | Q27–30 | B | A |

### C20 / Test 4 / Part 2

ID: `cambridge-20-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-2c8cc99a0cbf7d9e58f01f1814e65135e10e3cb22da76d2c79175063efbe1a75`; applicability Q11–14; display_order 1; source `Test_4_Part_2_PDF_Page_115.jpg`.
- **B** = `asset-3f1e401c0d31221023a9e7f2789d49b285c21b3a0b2bfee787ad2c3e717cd67c`; applicability Q15–20; display_order 2; source `Test_4_Part_2_PDF_Page_116.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–20 | B | A |

### C20 / Test 4 / Part 3

ID: `cambridge-20-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B, C**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-7b4272a0e284dd3324e90d52948894f1128f069d557ac53f50426bc149137847`; applicability Q21–25; display_order 1; source `Test_4_Part_3_PDF_Page_117.jpg`.
- **B** = `asset-250e6e1f066a605c2bd7cdc1b051aba49591cc551f2f45129c7bc3664e522743`; applicability Q26–29; display_order 2; source `Test_4_Part_3_PDF_Page_118.jpg`.
- **C** = `asset-3f0582172052a33126d79ac06b08a1ca21f6e3a3e7c10e72eb629f2c645bab92`; applicability Q30–30; display_order 3; source `Test_4_Part_3_PDF_Page_119.jpg`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B, C |
| Q23 | Q23–24 | A | B, C |

### C21 / Test 1 / Part 2

ID: `cambridge-21-test-01-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-c3bc72a8775e5fbab11cd76c1daf97be3952f051a7930c9056afcde30adbf838`; applicability Q11–16; display_order 1; source `Test_1_Part_2_PDF_012.png`.
- **B** = `asset-7f3ddd1cb8332905ff06f7aad0c02360b9cff8325c4664304393c2865fa0ebbb`; applicability Q12–20; display_order 2; source `Test_1_Part_2_PDF_013.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q17 | Q17–20 | B | A |

### C21 / Test 1 / Part 3

ID: `cambridge-21-test-01-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-3e6132f5ae9961d5617f248e7362899a14e3917174b8000b92395ee7262cc471`; applicability Q21–24; display_order 1; source `Test_1_Part_3_PDF_014.png`.
- **B** = `asset-cbe519f5d00c025e5564b1bbd5d92d6c4a662aa019e0c11cae115e4e29b92530`; applicability Q25–30; display_order 2; source `Test_1_Part_3_PDF_015.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–30 | B | A |

### C21 / Test 2 / Part 2

ID: `cambridge-21-test-02-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-5b43306f7be2ad058a6651ddea6130c6dbcfcb41bda66f96bbe01a32b27ce695`; applicability Q11–14; display_order 1; source `Test_2_Part_2_PDF_034.png`.
- **B** = `asset-0dd7caeb3c15232610602195093ed0413e5f325d40d91b4f22c0d56c13485c3b`; applicability Q15–20; display_order 2; source `Test_2_Part_2_PDF_035.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–20 | B | A |

### C21 / Test 2 / Part 3

ID: `cambridge-21-test-02-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-4f231c209fa53a02719ddedf98c75983d9ea20ce2ba1d37d01becc3ed1f550c0`; applicability Q21–26; display_order 1; source `Test_2_Part_3_PDF_036.png`.
- **B** = `asset-74274f69f771eaf1fa66a58faf2b6e0d476f9b75dfa2ed96fba0e75bd2e6bbca`; applicability Q27–30; display_order 2; source `Test_2_Part_3_PDF_037.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–26 | A | B |
| Q27 | Q27–30 | B | A |

### C21 / Test 3 / Part 2

ID: `cambridge-21-test-03-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-739782df0aff27a81a51ee53f661cbddd70c9d2768356d9592d36bbe1ee6f7f1`; applicability Q11–14; display_order 1; source `Test_3_Part_2_PDF_056.png`.
- **B** = `asset-9f43f87b7c080f379eba3cbd7b9fc70d68ce979e754614261253cf58f23c8fa7`; applicability Q15–20; display_order 2; source `Test_3_Part_2_PDF_057.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–16 | B | A |
| Q17 | Q17–20 | B | A |

### C21 / Test 3 / Part 3

ID: `cambridge-21-test-03-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-cb4b9ba2bfdefabe224987ff6e0622a59610a1cdb2c5dda85d9d085bf917ca8c`; applicability Q21–24; display_order 1; source `Test_3_Part_3_PDF_058.png`.
- **B** = `asset-5a99e4b6ad54cc01441c29be0071a144accff961197e79cacc29d5bc0287baa7`; applicability Q25–30; display_order 2; source `Test_3_Part_3_PDF_059.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–22 | A | B |
| Q23 | Q23–24 | A | B |
| Q25 | Q25–30 | B | A |

### C21 / Test 4 / Part 2

ID: `cambridge-21-test-04-p2`. Видимые вопросы: **Q11–20**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-b384be539da831681725bf6c50d56ae2153d740a50ce4bea313a3f52625d8ddf`; applicability Q11–14; display_order 1; source `Test_4_Part_2_PDF_077.png`.
- **B** = `asset-c57ecd4dae004bd465edc472085f24679725e65cb64788ec7f0cc26065e83922`; applicability Q15–20; display_order 2; source `Test_4_Part_2_PDF_078.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q11 | Q11–12 | A | B |
| Q13 | Q13–14 | A | B |
| Q15 | Q15–20 | B | A |

### C21 / Test 4 / Part 3

ID: `cambridge-21-test-04-p3`. Видимые вопросы: **Q21–30**. Expected IDs: **A, B**. Причина: active-group scope вместо visible-Part scope. Severity: **HIGH**. Evidence: **component verified (actual WorkspaceQuestions SSR)**.

- **A** = `asset-9025ae092473b0038dc29a50ce8f5ffa6c9e9aaa1bd21589bb0448998dc283ec`; applicability Q21–23; display_order 1; source `Test_4_Part_3_PDF_079.png`.
- **B** = `asset-3d8d84c1b919ec83519619e5c7283cce7edc04f88d41c29207d1d1784e2b93b4`; applicability Q24–30; display_order 2; source `Test_4_Part_3_PDF_080.png`.

| Current | Active group | Actual IDs | Missing IDs (ranges defined above) |
|---:|---|---|---|
| Q21 | Q21–23 | A | B |
| Q24 | Q24–30 | B | A |

## 10. Machine-readable artifacts и сохранность

- [part-coverage.json](listening-visual-audit/stage1/part-coverage.json): все 288 Parts, expected/actual/missing, все 568 active states, metadata ranges, source fingerprints, 18 empty groups и filtered component reproductions. Верхний actual — initial current; status Part учитывает **все** contexts.
- [regression-findings.csv](listening-visual-audit/stage1/regression-findings.csv): только 380 конкретных проблемных состояний (157 Parts), с полными IDs/диапазонами/reproduction и evidence. Не 380 уникальных Parts.
- [regression-browser-evidence.json](listening-visual-audit/stage1/regression-browser-evidence.json): 16 mode cases, initial DOM IDs, missing, transitions, scroll observations и screenshot names.
- [audit-listening-part-coverage.mjs](../web/scripts/audit-listening-part-coverage.mjs): минимальный reproducible offline/component/headless-browser audit. Требует имеющихся web/node_modules; ничего не устанавливает. Port 3391 loopback; temp fixture отключает настоящий backend.

Исходные audit/stage1 results/index.html не переписаны. Добавлены только этот handoff, новый audit script, part-coverage.json, regression-findings.csv, browser-evidence JSON и 16 screenshots. Source SHA-256 в part-coverage.json сверены после аудита: рабочие Listening компоненты и registry не менялись. Физические изображения не декодировались повторно в массовом аудите; только выбранные browser cases загрузили свои публичные изображения.
