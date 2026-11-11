# READING AI COVERAGE FIX RESULT

2026-11-11 · Stage 1 · IMPLEMENT + TARGETED QA · no commit/push/deploy.

## 1. Root causes fixed

- Matching Information: label-only banks допускаются только при уникальных, непустых, неповреждённых paragraph blocks с соответствующими labels в **frozen snapshot**. Проверяются все labels банка, canonical answer и accepted answers. Отсутствующий label, duplicate option/block label и повреждённый source остаются blocked. Guards других типов не смягчены.
- Matching Headings: добавлен полный явный `Section X`; сохранена поддержка существующих Paragraph forms. Target проверяется против уникального frozen paragraph. Mixed targets не угадываются; отдельно отмеченный Example не заменяет target.
- UI: inline review принадлежит только реально показанному blank, рядом с его rich-text/list/cell block. Непоказанный inline blank получает один fallback Anchor со своим review. Inline fields, AnswerSession и сохранение ответов не менялись.
- Generation: trusted `allowed_evidence_kinds`, exact numbered `blank_context`, строгие TRUE/YES support, FALSE/NO contradiction и NOT GIVEN relevant_context. Для paragraph/heading модели предлагаются только source-owned candidates доверенного target; backend/TS checks сохранены. Main-idea reasoning, saved-key authority и unordered grading явно указаны в prompt. Неверный kind не переписывается.
- Безопасные категории: source_blocked, model_abstained, invalid_evidence_kind, invalid_candidate, invalid_prose, provider_unavailable, deadline. Диагностика не содержит пользовательских ответов, passage, ключей или secrets. Fingerprint policy v1.4; предыдущие cache entries не удаляются, новый FOUND cache проверен.

## 2. Changed files

- `backend/app/modules/reading/ai_review.py`
- `backend/tests/test_reading_ai.py`
- `web/src/features/reading/exam/question-renderer.tsx`
- `web/src/features/reading/ai/prompt.ts`
- `web/src/features/reading/ai/contract.ts`
- `web/src/app/api/reading/explain/route.ts`
- `web/tests/reading-ai-contracts.spec.ts`
- `web/scripts/test-reading-confirmed-hotfix.mjs` — selector учитывает единственного владельца saved review.
- Этот отчёт. QA scripts/census/isolated build copies размещены в `/tmp/alua-stage1`; новых постоянных тестовых файлов не добавлено.

Существовавшие до Stage 1 изменения в рабочем дереве сохранены. Cambridge JSON/keys, catalog, grading, результаты/попытки, Listening, Translation, Orchestrator и production config не редактировались этой работой. Browser QA также создаёт обычные screenshots/results существующих runners.

## 3. Before/after coverage

Повторён метод аудита: настоящий ReadingCatalog, in-memory frozen-row adapter, штатный result_for с пустыми answers и настоящий ReadingAIReview.context для каждого qid. DB writes и model calls census: 0. До изменений baseline точно воспроизвёл аудит. В конце добавленный blank_context также включён в budget validation.

| Metric | Before | After |
|---|---:|---:|
| Allowed questions | 2760 | 2760 |
| Context READY | 2283 | 2600 |
| Context BLOCKED | 477 | 160 |
| Matching Information blocked | 273 | 0 |
| Heading target blocked | 56 | 12 |
| Duplicate Explain question IDs, all canonical | 33 | 0 |
| Duplicate Explain question IDs, allowed | 30 | 0 |

Фактический прирост **317**: 273 Information + 44 Section. Ни один прежний READY не стал BLOCKED. READY в разрешённых exams: **94,20%**, вычислено после census. Все canonical: 2323 → 2640 READY из 2880; остальные 240 blocked включают 80 source-integrity questions исключённых exams. Исключения каталога сохранены.

**READY — пригодность контекста, а не доказательство качества AI generation или entailment.** Census не сертифицирует все исторические snapshots; отрицательные frozen-source mutation fixtures проверены отдельно.

## 4. Matching Information: PASS

C04 T2 Q27 принят с исходным frozen key H. A→A принят. Удаление A из snapshot, duplicate H paragraph и duplicate option A отклоняются. Source-owned evidence из неверного paragraph не принимается. Реальная генерация этого типа — отдельный FAIL ниже.

## 5. Matching Headings: PASS

C04 T3 Q14 / Section A и Explicit Paragraph A проходят context + evidence validation. Section Z, duplicate target paragraph, mixed Section/Paragraph, несколько targets и слитная неоднозначная SectionA отклоняются. Все 12 ранее blocked ambiguous cases остались blocked. Keys и paragraph mappings не менялись.

## 6. Duplicate Explain buttons: PASS

Настоящий QuestionGroup SSR: 613 групп, 15 типов. До: 2913 controls для 2880 IDs; после: **2880 controls / 2880 unique IDs**, отдельно **2760 / 2760 allowed**. Вызваны callbacks всех controls с проверкой qid/aria-controls. При открытых карточках duplicate card IDs: 0.

Chromium desktop и WebKit mobile на production-сборке actual renderer: C12 T5 Q14, C15 T4 Q21, partial inline, summary и table. Один control/card, first-click correct qid, уникальные DOM IDs, scroll delta ≤2px. Интеграционный Reading AI browser flow дополнительно проверил настоящие frontend/backend endpoints, keyboard opening, multiple open cards, source highlight, back navigation, Retry и FOUND cache; model responses в этом regression flow — synthetic.

## 7. Type-aware prompts: PASS (contracts); live generation gate: FAIL

99 AI/Reading/Smart Translation contract tests passed. Включены неверный kind → разрешённый fallback без подмены, model abstention → fallback, privacy deny, source blocks без модели, фильтрация candidates по frozen target, auth/client-source injection и bounded diagnostics. Python/TS boolean evidence-kind matrices и shared Unicode/UTF-16 acceptance cases согласованы. Negative cache не препятствует Retry; FOUND переоткрывается без новой генерации.

## 8. Real Cloudflare AI: FAIL

Ровно **5 реальных Workers AI calls**, существующий Wrangler login/binding, текущий Gemma provider. Groq отсутствовал; Gemini/OpenRouter gates не включались. Использованы disposable local PostgreSQL QA attempts с действующими ownership/context endpoints; постоянная локальная БД и production не использовались. Четыре временных attempts за два smoke runs; все уничтожены вместе с изолированной БД. Массовых вызовов или attempts нет.

| Case | Calls | Result |
|---|---:|---|
| C04 T2 Q27 Information | 2 | Context accepted, CF called; invalid_candidate, controlled unavailable; второй вызов после ограничения предложенных candidates target-параграфом тоже отклонён |
| C04 T3 Q14 Headings | 1 | Context accepted, CF called; invalid_candidate, controlled unavailable |
| C05 T2 Q14 FALSE | 1 | Validated FOUND / contradiction, source offsets accepted, highlight visible, backend FOUND cache hit |
| C05 T2 Q15 NOT GIVEN | 1 | Validated FOUND / relevant_context, source offsets accepted, highlight visible, backend FOUND cache hit |

Точный подтип invalid_candidate в этих live traces не сохранялся; нельзя утверждать, был ли причиной ID, paragraph или prose paragraph reference. Raw rejected model responses не логировались. После последнего candidate-filter изменения live Headings повторно не вызывался: лимит 5 соблюдён. Дополнительных calls для улучшения статистики не делалось.

## 9. Evidence highlight: PASS для двух live FOUND; остальных NOT VERIFIED

FALSE/NOT GIVEN: возвращённые UTF-16 ranges сопоставлены с заново авторизованным frozen context; Show in passage открыл видимый `[data-reading-ai=true]` mark. Повторный backend запрос вернул cached:true без нового Worker/model call. Для Information/Headings FOUND отсутствует, поэтому успешная реальная подсветка этих типов не подтверждена. Structural/source-owned highlight regressions прошли с synthetic generation.

## 10. Critical regression tests

- Backend: **148 passed**, 2 browser tests отдельно deselected; Reading Exam/Submit/Results, frozen snapshot, ownership, cache, Listening AI, legacy compatibility и Hotfix 41/41 registry/source checks. После последнего backend изменения Reading AI suite отдельно: **52 passed**, 1 browser deselected.
- Reading AI real endpoint browser regression: **1 passed**, Chromium desktop + WebKit mobile, synthetic provider.
- Hotfix Exam/Finish/Results/Review browser regression: **1 passed**, после исправления устаревшего review selector.
- AI/Reading/Smart Translation contracts: **99 passed** на финальном frontend коде.
- TypeScript, полный ESLint, targeted Ruff check/format: PASS.
- Final Next.js production build (webpack) и OpenNext Cloudflare Worker bundle: PASS в изолированной копии с клонированными зависимостями. Production config/release не изменялись. Первоначальные sandbox failures из-за symlink/Turbopack/sharp и отсутствующего fixture field устранены в QA sandbox.
- Listening browser regression: **2 passed / 2 failed**. AI Retry/cache/reload — PASS в Chromium desktop и WebKit mobile. Loop/navigation test — FAIL: audio не paused после перехода к Q1 (строка 241). Повтор с renderer до Stage 1 тоже FAIL, но раньше, на loop playback state (строка 230). Поэтому точная baseline-эквивалентность pause failure не доказана; Listening-код не менялся, этот gate не объявляется зелёным.

## 11. Remaining blocked questions by reason

В разрешённых exams:

- **58 incomplete_options / source-type-bank inconsistencies**: TFNG с YES/NO keys 16; endings 12; summary 11; note 11; headings bank 5; single MC bank 2; multi MC bank 1.
- **90 visual_context_unavailable**: diagram 42; flowchart 17; single MC 25; multi MC 6.
- **12 heading_context_unavailable**: mixed/ambiguous targets.

Всего **160**. Исключённые exams не включались; дополнительно 80 canonical source_integrity blocks остались как в baseline. OCR/vision/RAG/new providers не добавлялись.

## 12. Final: BLOCKED

Context/UI fixes прошли targeted QA и дают подтверждённый прирост 317 READY без ослабления source/evidence authority. Полный live generation gate не пройден для Information/Headings; Listening browser gate также не зелёный. Нельзя объявлять Stage 1 полностью готовым для release. Лимит реального smoke исчерпан; нужны отдельная разрешённая итерация model-contract диагностики и разбор Listening audio test. Commit/push/deploy/production SSH/config changes: 0. Исходные frontend/backend процессы сохранены работающими.
