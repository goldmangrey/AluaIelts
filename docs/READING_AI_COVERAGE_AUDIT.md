# Reading AI Coverage & Reliability Audit

2026-11-11 · актуальный локальный checkout · **READ-ONLY**. Единственный новый файл — этот отчёт. Новых AI calls, attempts, DB writes, изменений кода/config/secrets, OCR, commit/push/deploy: **0**.

## A. Executive summary

**18 книг, 72 canonical exams, 216 passages, 613 groups, 2 880 реальных вопросов, все 15 типов.** В текущем приватном каталоге разрешены **69 exams / 2 760 вопросов**; три теста исключены. Подсчитаны также их существующие canonical данные, отдельно от доступности Start.

| Класс | Все canonical вопросы | В разрешённых exams |
|---|---:|---:|
| READY | 2 323 (80,66%) | 2 283 (82,72%) |
| SOURCE_BLOCKED | 58 | 58 |
| VISUAL_REQUIRED | 90 | 90 |
| INTEGRITY_WARNING | 80 | 0 |
| CONTEXT_TOO_LARGE | 0 | 0 |
| UNKNOWN | 329 | 329 |

**READY — пригодность текущего context, не гарантия правильной генерации.** UNKNOWN здесь: runtime reason известен, но нельзя назвать отсутствующим источник только из-за guard: 273 Matching Information и 56 Headings требуют исправления/уточнения интерпретации. SOURCE_BLOCKED — измеримые противоречия типов/банков, не утверждение о качестве издательского PDF.

Основные причины: (1) ложный запрет paragraph-label options; (2) извлечение heading target только через `Paragraph`; (3) визуальные задачи без image input; (4) неполные/несогласованные banks; (5) ошибки модели при единственном реально доступном локальном provider. Дополнительно найдены UI-дубликаты.

### Метод и границы

- Загружен штатный `ReadingCatalog` со schema/runtime validation. Для каждого вопроса в памяти создан read-only adapter frozen-row shape: canonical exam/key/metadata и результат чистого `result_for(..., answers={})`; вызван настоящий `ReadingAIReview.context()`. В БД искусственные rows не создавались.
- Для каждого вопроса проверены book/test/passage/number, type/input, canonical/accepted key, passage, prompt/instructions, options, image representation, применимые critical warnings и точный runtime reason. Все 2 880 имеют key/accepted answers, passage, непустые prompt/instructions; это не доказывает полноту их смысла.
- Input types: boolean 791, single_select 1 247, text 752, multi_select 90. Options присутствуют у 2 097; их отсутствие у text/визуальных задач само по себе не дефект. Source-image representation затрагивает 286 вопросов; только 90 блокируются как visual.
- Причины runtime-блокировки: `incomplete_options=331`, `heading_context_unavailable=56`, `visual_context_unavailable=90`, `source_integrity=80`. Исключений context builder: 0. Максимум среди READY: 24 008 JSON bytes и 64 candidates при лимитах 80 000 / 160.
- Наличие полей и labels не проверяет PDF-fidelity, содержательность каждого prompt или entailment. **Canonical census не сертифицирует исторические frozen snapshots.** Они проверены только в малой QA-выборке ниже.

## B. Coverage by question type

Blocked в таблицах = всё, что сейчас не READY; включает UNKNOWN/warnings/visual, а не только SOURCE_BLOCKED.

| Question type | Total | Ready | Blocked | Primary issue |
|---|---:|---:|---:|---|
| Multiple Choice Single | 246 | 211 | 35 | 25 visual; 2 duplicate option banks; 8 warnings |
| Multiple Choice Multiple | 90 | 79 | 11 | 6 visual; 1 missing keyed option; 4 warnings |
| TRUE/FALSE/NOT GIVEN | 511 | 489 | 22 | 16 YES/NO keys with TRUE/FALSE banks; 6 warnings |
| YES/NO/NOT GIVEN | 280 | 267 | 13 | 13 warnings; NOT GIVEN permits context only |
| Matching Headings | 200 | 129 | 71 | 56 target extraction; 5 banks; 10 warnings |
| Matching Information | 277 | 0 | 277 | 273 label-only false blocks; 4 warnings |
| Matching Features | 221 | 208 | 13 | 13 warnings; relationship reasoning remains model-owned |
| Matching Sentence Endings | 90 | 71 | 19 | 12 incomplete banks; 7 warnings |
| Sentence Completion | 105 | 102 | 3 | 3 warnings; partial-inline duplication also found |
| Summary Completion | 435 | 419 | 16 | 11 input/bank inconsistencies; 5 warnings |
| Note Completion | 226 | 208 | 18 | 11 input/bank inconsistencies; 7 warnings |
| Table Completion | 101 | 101 | 0 | All context-ready, including restored image representations |
| Flow Chart Completion | 17 | 0 | 17 | 17 intentional visual limits |
| Diagram Labelling | 42 | 0 | 42 | 42 intentional visual limits |
| Short Answer | 39 | 39 | 0 | Context-ready; no deterministic entailment proof |
| **Total** | **2880** | **2323** | **557** | |

Для всех текстовых типов доступна точная source-owned anchoring: paragraph candidates до 700 символов, максимум три выбранных ID, backend рассчитывает UTF-16 offsets. Identical quotes в разных позициях имеют разные ID; повтор/overlap одного диапазона отклоняется. Для Headings/Information дополнительно проверяется paragraph label. Остальные типы не имеют детерминированного доказательства смысловой связи с key.

Type-specific ограничения: FALSE/NO запрещают `support`; NOT GIVEN разрешает только `relevant_context` и не доказывает отсутствие факта цитатой. Unordered MC получает saved group verdict/answers, перестановка не переоценивается. Inline blanks передаются с group content; shared prompts не гарантируют уникальную ассоциацию target. Diagram/essential flowchart не получает vision и честно unavailable. Table/source-image с полным восстановленным текстом не блокируется автоматически.

## C. Coverage by book

Все строки — canonical; source test numbering сохранён, включая C12 Tests 5–8.

| Cambridge | Questions | Ready | Blocked |
|---|---:|---:|---:|
| 04 | 160 | 137 | 23 |
| 05 | 160 | 134 | 26 |
| 06 | 160 | 123 | 37 |
| 07* | 160 | 94 | 66 |
| 08 | 160 | 133 | 27 |
| 09 | 160 | 109 | 51 |
| 10* | 160 | 139 | 21 |
| 11 | 160 | 135 | 25 |
| 12 | 160 | 140 | 20 |
| 13 | 160 | 142 | 18 |
| 14 | 160 | 128 | 32 |
| 15 | 160 | 127 | 33 |
| 16 | 160 | 132 | 28 |
| 17 | 160 | 133 | 27 |
| 18 | 160 | 134 | 26 |
| 19 | 160 | 140 | 20 |
| 20* | 160 | 96 | 64 |
| 21 | 160 | 147 | 13 |
| **Total** | **2880** | **2323** | **557** |

\* Исключены C07 T2, C10 T1, C20 T3 (по 40 вопросов). Critical warnings блокируют context у C07 T2 и C20 T3; C10 T1 исключён catalog policy, хотя его 40 contexts проходят текущие AI guards. READY не отменяет запрет Start.

## D. Existing QA case matrix

Доступны только **3 существующие локальные QA attempts / 2 exams (C04 T1, C05 T2)** одного разрешённого локального аккаунта. Недостаточно для репрезентативной выборки C04–21. Ни в одной нет Matching Headings: исторический AI-кейс этого типа **NOT AVAILABLE**, проверен только canonical context. Новые попытки не создавались.

В каждой строке frozen key присутствует и согласован с result; passage text есть. Взяты 3 успешных и 5 ранее unavailable случаев. Логи сопоставлены по последовательности 13 model-bearing Worker requests и 13 backend callbacks одного QA flow; не считаются распределённой production trace.

| Case | Context reason сейчас | AI called / model result | Validator / fallback | Cache / final |
|---|---|---|---|---|
| C05 T2 Q1 Completion | null | YES, CF FOUND | ACCEPT; Groq skipped → CF | found, повторно валиден |
| C05 T2 Q2 Completion, поздняя QA | null | YES, CF FOUND | ACCEPT; Groq skipped → CF | found, повторно валиден |
| C05 T2 Q3 Completion | null | YES, CF FOUND | ACCEPT; Groq skipped → CF | found, повторно валиден |
| C04 T1 Q1 FALSE | null | YES, CF ERROR | historical invalid_output; подтип UNKNOWN | legacy negative существует, **теперь bypass**; новый final не вызывался |
| C04 T1 Q2 FALSE | null | NO при старом отказе | прежний incomplete_options уже исправлен; fallback не запускался | cache отсутствует; текущая генерация NOT TESTED |
| C05 T2 Q14 FALSE, обе QA | null | YES, FOUND candidate отклонён | kind: support недопустим для FALSE; 4 сохранённых CF failure traces | legacy negatives bypass; observed unavailable |
| C05 T2 Q15 NOT GIVEN, обе QA | null | YES; одна выдача дошла до kind, другая до prose | kind: не relevant_context; другая prose (подтип UNKNOWN); CF — последний доступный | legacy negatives bypass; observed unavailable |
| C05 T2 Q4 Flow Chart | visual_context_unavailable | NO | deterministic context block; fallback не нужен | cache отсутствует; nonretryable source-unavailable |

Raw rejected provider responses не сохранялись: нельзя восстановить их полный текст, точную причину `prose` или старый C04 schema/JSON/quote subtype. Для kind логически известно, что JSON/schema/status/candidate/quote прошли предыдущие checks; это не доказательство правильности самого объяснения. Критичные trace категории не подменяются догадками.

## E. Confirmed vs suspected causes

### Ranking: 10 измеримых механизмов/ограничений

Количество ниже — affected contexts или конкретные наблюдения, **не AI failure rate**; строки могут пересекаться.

| Priority / status | Причина, место | Масштаб / тип / пример | Минимальное направление; риск |
|---|---|---|---|
| P1 CONFIRMED | Label-only guard отвергает нормальные paragraph options — BACKEND | 273 доступных Matching Information; C04 T2 Q27, key H, blocks A–I | Проверять labels против passage, не требовать text≠label; низкий риск при сохранении ID/label guards |
| P1 CONFIRMED | Heading target regex понимает только Paragraph — BACKEND | 56 Headings; **44** имеют однозначный Section X, **12** mixed/ambiguous; C04 T3 Q14 | Поддержать явный Section target; неоднозначные оставить blocked; риск неверного target при угадывании |
| P1 CONFIRMED | Неполные/дублированные реальные banks — DATA | 20 SOURCE_BLOCKED: endings 12, headings 5, single MC 2, multi MC 1; C06 T2 Q23, C19 T1 Q23 | Исправлять только доказуемую extraction/структуру; fail closed; средний риск |
| P1 CONFIRMED | Completion оформлен select/bank, key — слово/фраза — DATA/BACKEND contract | 22: summary 11 + note 11; C04 T3 Q37, C16 T1 Q21 | Развести text completion и option bank по доверенной структуре; не чинить grading/keys эвристикой; средний риск |
| P1 CONFIRMED | YES/NO key при TRUE/FALSE type/options — DATA | 16 TFNG; C09 T1 Q21 | Отдельная сверка типа/представления без подмены key; нельзя автоматически конвертировать ответы; высокий риск |
| P2 CONFIRMED, intentional | Существенный visual input отсутствует у текстового AI — BACKEND/model modality | 90: diagram 42, flowchart 17, single MC 25, multi MC 6; C05 T2 Q4 | Сохранить unavailable; текстовый fallback допустим лишь при полном trusted представлении; высокий риск ложного evidence при обходе |
| P2 CONFIRMED, policy | Critical warnings распространяются на контекст — DATA/BACKEND | 80 вопросов в уже исключённых C07 T2/C20 T3; пример C07 T2 Q1 | Оценивать применимость warning без массового отключения защиты; риск source-fidelity |
| P1 CONFIRMED category, subtype частично UNKNOWN | Модель нарушает kind/prose contract — AI PROMPT/VALIDATOR | 5 kind + 2 prose failures в 13 имеющихся model-bearing requests; C05 T2 Q14/Q15/Q16 | Явные allowed kinds из trusted verdict, короткие примеры/ограниченный prose; точную цитату/validator не ослаблять; средний риск недоказанного смысла |
| P2 CONFIRMED locally | После отсутствующего Groq key реально остаётся один CF — CONFIG/privacy | Все 13 имеющихся traces: Groq configuration_failure → CF; Gemini/OR запрещены policy | Проверить readiness существующего primary отдельно; не включать внешнюю обработку автоматически; не обещать спасение fallback при одном provider |
| P1 CONFIRMED structural | Inline saved-answer metadata + fallback Anchor дублируют Explain/card — UI | **33 question IDs / 11 groups**, из них **30 / 9** в разрешённых exams; C12 T5 Q14, C15 T4 Q21 | Render Review/card ровно один раз на qid; риск navigation/duplicate DOM IDs, не доказан wrong-neighbour ответ |

### Что уже работает и что не подтверждено

- Model abstention теперь бросает `model_abstained`, продолжает разрешённую цепочку и не включает cooldown. Invalid JSON/schema/ID/quote/paragraph тоже продолжают fallback. Когда CF — последний, исчерпание даёт controlled `retryable:true`, а не придуманное evidence.
- Context source failures возвращаются без модели и без Retry. 58 source + 329 guard/association + 90 visual = **477** недоступных contexts в разрешённой библиотеке.
- 30-day cache читает/пишет **только validated found**. Старые negative записи присутствуют у QA, но игнорируются. Frontend сохраняет только found; temporary Retry делает новый разрешённый запрос. Fingerprint v1.3 включает owner/attempt/snapshot/result/answers/qid; cache revalidation сохранена.
- Missing key / key-result mismatch fail closed до модели; в canonical census случаев нет. У исторического snapshot такие ошибки возможны: охват всех исторических attempts не доказан.
- Нынешних `key_not_grounded`, `blank_context_not_grounded`, правила 60% абзаца/1200 символов **нет**. Literal overlap не объясняет текущие canonical blocks.
- 13 коротких in-memory probes Python/TS прошли: 8 shared Unicode cases, bad ID, overlap/duplicate, wrong paragraph, NOT GIVEN kind. Длина — code points, evidence offsets — UTF-16. Backend принимает controlled unavailable для сериализации, TS model validator отклоняет его для fallback: это разные стадии, не расхождение evidence acceptance.
- **Подтверждённый предел семантики:** source-owned, но нерелевантное предложение проходит text/concepts validator в synthetic probe. Exact anchoring доказывает происхождение цитаты, не entailment; для Headings/Information дополнительно ограничен paragraph. Это риск ошибочного FOUND, не установленная причина unavailable.
- Cooldown: 429/Retry-After и transient errors, best-effort per isolate. Backend generation/context callback и Worker — по 6/min, bounded maps, single-flight; frontend dedup per owner/question. Quota/429 не надо смешивать с source failure.
- Model deadline 45s; callback proxy 4s; FastAPI HTTPX timeout 50s; frontend/proxy 55s. **SUSPECTED:** cold binding setup + callback + model deadline могут пересечь внешний budget; 50s HTTPX — timeout операций, не доказанный total deadline. В 13 traces timeout/cooldown как причина не подтверждены.
- Aggregate prose/invalid_output и общий models_unavailable скрывают часть диагностического подтипа. Причина старого C04 rejection остаётся UNKNOWN; текущая статистика всей библиотеки по моделям отсутствует.

### Structural UI coverage

Без браузерного массового прогона: настоящий `QuestionGroup` отрендерен через React SSR для **613 groups / 15 типов**. Только AssetImage/CSS заменены локальными stubs, без загрузки картинок. Для каждого Explain вызван его сохранённый click callback; проверены qid и aria-controls. **Все 2 880 qid представлены, чужих qid не обнаружено**, но HTML содержит **2 913 Explain buttons** из-за 33 повторов.

Механизм: inlineReviews выводит Review для всех questions; если inline source не содержит конкретный blank, fallback Anchor выводит второй Review/card. Повторы: Information 2, Endings 4, Sentence Completion 15, Note Completion 12. Из них три позиции относятся к исключённым exams. Это UI duplication, не исчезновение модели и не source failure.

Использованы существующие Reading/Listening/Translation QA fixtures и их прежние Chromium/WebKit результаты, описанные в `READING_AI_RELIABILITY_FIX.md`; новый browser suite не запускался, screenshots не перезаписывались. Предыдущие локальные smoke покрывали нормальные группы, поэтому найденные partial-inline cases не были ими закрыты. Отсутствие scroll/visual дефектов во всех 2 880 вопросах не заявляется.

## F. Recommended fix plan — максимум 4 централизованных изменения

1. **P1: typed AI context normalization.** `backend/app/modules/reading/ai_review.py` + узкие tests. Paragraph-label banks разрешать только при существующих labels; явные Section X сопоставлять с тем же frozen block. Ни одного предполагаемого target. Проверка: повтор census reason counts и source-owned negative fixtures. Измеримый первый потенциал — **273 + 44 = 317** снятых предмодельных блоков; 12 ambiguous headings и реальные data/visual проблемы остаются. Reading-only; риск неверного target контролируется fail-closed.
2. **P1: type-aware generation contract + diagnostics.** `web/src/features/reading/ai/prompt.ts`, `contract.ts`, `api/reading/explain/route.ts`; при необходимости backend metadata. Передавать allowed evidence kinds из trusted verdict, добавить краткие FALSE/NG examples, держать prose bounded; различать model abstention, validation subtype и transport/source failure безопасными metadata. Проверка: mocks вида «валидная цитата + неверный kind» и реальные QA acceptance gate позже. Не нормализовать support в contradiction молча; риск плохого entailment остаётся. Listening routing/validator не менять.
3. **P1: один Review/card на qid.** `web/src/features/reading/exam/question-renderer.tsx` + существующие UI tests. Развести inline metadata и fallback rows без изменения exam editing/answers; сохранить cards вне blank spans. Проверка: 613-group SSR census должен дать 2 880 уникальных buttons и один card ID на открытый qid; desktop/mobile smoke на C12 T5 и C15 T4. Риск Reading navigation/scroll, Listening не затрагивать.
4. **P2: централизованная source-readiness диагностика.** `ai_review.py`, `reading/catalog.py`/их узкие tests, UI unavailable messaging. Различать genuine bank/type mismatch, target ambiguity и intentional vision limit; для 58 inconsistent questions сформировать ограниченный список исправлений существующего текстового представления отдельным заданием. Не угадывать labels и не править keys/grading. Проверка: заранее заданные bank/type cases, historical snapshot independence и отсутствие новых provider calls при deterministic blocks. Реальное восстановление источника может требовать индивидуальной проверки и не обещается одним guard fix.

Операционный предел локальной проверки: один реальный provider. Его устранение — отдельная разрешённая настройка существующего primary, не повод менять privacy gates или инфраструктуру.

## G. Final verdict

**MIXED** — сочетание context/данных, ограничений визуального ввода, generator contract и структурного UI дефекта.

Утверждение «2–4 общих изменения исправят 70–90% наблюдаемых AI-отказов» **не доказано**. Два уверенно определённых context механизма охватывают 317/477 = **66,46% текущих предмодельных блоков разрешённой библиотеки**; даже все 56 heading extraction cases вместе с Information — 329/477 = 68,97%. Это не доля пользовательских отказов генерации и не прогноз correctness. Для остального недостаточно model traces и исторических snapshots.

Код после аудита не менялся. Следующий шаг — отдельное задание на реализацию выбранных исправлений.

