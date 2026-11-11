# ALUA — STAGE 2: FINAL READING AI LIVE GATE + LISTENING REGRESSION

2026-11-11 · локальный checkout · без commit/push/deploy/production SSH.

## 1. Точная причина invalid_candidate

На третьем реальном вызове C04 T2 Q27 воспроизведён **`invalid_candidate / prose_reference`**. В TS-валидаторе эта проверка идёт после candidate lookup, allowed-set check, kind, точных source offsets, overlap/order и target paragraph. Следовательно, в этом отказе **ID, evidence и target прошли проверки**; отказ возник на буквенной ссылке в одном из текстовых полей на абзац, отсутствующий среди выбранных evidence anchors.

Это конфликт генерации prose с действующим evidence contract, а не подтверждённое рассогласование IDs. Prompt требовал объяснить неверный ответ, но не оговаривал, что сравнение также не должно называть букву нецитируемого абзаца. Добавлено явное правило: конкретную букву разрешено упоминать только для выбранного evidence; при обсуждении другого варианта писать «выбранный абзац» и объяснять смысловое несоответствие.

Ни буквы, ни raw model response не логировались; поэтому нельзя достоверно назвать конкретную букву, поле или объявить, что это обязательно был label пользовательского ответа. Исторический подтип Stage 1 для Headings восстановить нельзя: rejected responses не сохранены. В Stage 2 Headings дал FOUND.

Добавлена bounded диагностика: `unknown_candidate_id`, `candidate_outside_allowed_set`, `wrong_paragraph`, `duplicate_or_overlap`, `source_quote_mismatch`, `prose_reference`, другие фиксированные schema/kind/prose/status причины. Произвольные exception messages не выводятся. Passage, пользовательские ответы, ключи, IDs и secrets в диагностике отсутствуют.

Согласованность IDs проверена:

- Python `public_candidates` детерминированно создаёт source-owned IDs; backend revalidation заново строит их из frozen blocks.
- Worker не меняет ID; одна `allowedReadingCandidates` теперь определяет и предложенный модели набор, и TS allowed-set validation.
- Модель возвращает исходный candidate_id; callback fingerprint и backend source/paragraph validation сохранены.
- Проверка TS offsets дополнительно отклоняет `end` за пределами source text. Acceptance guards не ослаблены; prose не исправляется постфактум.

## 2. Information live FOUND: PASS с ограничением

Выполнены два вызова C04 T2 Q27: первый — validated FOUND, точная подсветка и backend cache hit; повторный диагностический — controlled unavailable с `prose_reference`. Это **не два успешных вызова** и не доказательство стабильности генерации.

Уточнение prompt внесено после диагностического отказа и проверено mocks. Live с финальным prompt **NOT VERIFIED**, поскольку общий лимит уже исчерпан.

## 3. Headings live FOUND: PASS

Один вызов C04 T3 Q14: context принят, реальный Cloudflare/Gemma вызван, валидаторы приняли FOUND. Show in passage открыл evidence, повтор вернулся из backend FOUND cache. Этот вызов предшествовал финальному уточнению prose-инструкции.

## 4. Evidence highlight/cache: PASS для обоих полученных FOUND

Для Information и Headings возвращённые UTF-16 ranges сверены с заново авторизованным frozen source. Show in passage открыл видимый `data-reading-ai=true` mark; повторный backend запрос дал cached:true без нового Worker/model call. Повреждённые IDs, неправильный target, overlap и нецитируемые prose references продолжают отклоняться.

**Всего Stage 2: 3 реальных Cloudflare AI calls** — два FOUND и один безопасный отказ. Groq отсутствовал; Gemini/OpenRouter privacy gates не включались. Использованы три disposable local QA attempts в изолированной PostgreSQL, уничтоженные после smoke. Постоянная локальная БД и production не изменялись.

Первый smoke runner получил ENOTEMPTY при удалении временной UI-копии уже после успешных FOUND/highlight/cache assertions. Это инфраструктурный teardown failure; runner исправлен ожиданием завершения Next и повторным удалением. Дополнительный вызов ради этого не делался.

## 5. Listening regression: исправлен + устранены две ошибки теста

Подтверждён реальный дефект **Review lifecycle**, Player не менялся:

1. Обычная позиция Part 1 сохраняется, запускается временный AI loop из Q12 / Part 2.
2. Пользователь переходит к Q1.
3. Baseline `focus()` менял только current question. `moment` оставался активным; audio продолжало Part 2 loop.
4. Review теперь при смене вопроса снимает только временный moment. Существующий Player.finishMoment останавливает clip и восстанавливает исходную запись/позицию.

Сценарий идентичен на baseline-снимке `review.tsx` в начале Stage 2 и финальном коде; использованы те же финальные tests, WAV, viewport и browser engines. Baseline: **2 FAIL** восстановления AI clip и **2 PASS** обычных позиций Part 1–4. Финал: все эти проверки PASS в Chromium desktop и WebKit mobile.

Отдельно исправлены ошибки длинного browser-теста:

- Мгновенный подсчёт playing audio попадал в нормальную pause/seek фазу перезапуска loop. Теперь ожидается resumed playback через expect.poll; проверки циклических seek и единственного активного audio сохранены.
- После возврата к ранее открытому Q2 тест безусловно нажимал Explain, закрывая сохранённую карточку. Теперь он открывает её только при aria-expanded!=true, учитывая существующее multi-open поведение.

Обычная навигация Part 1–4 не переключает audio source и не сбрасывает время; явное Listen to Part восстанавливает отдельную позицию каждого Part. Это проверено до и после исправления. Player/audio-progress не редактировались.

## 6. Изменённые файлы

- `web/src/features/reading/ai/contract.ts` — общая allowed-set функция, безопасные подтипы, разделённые guards, строгая граница end.
- `web/src/app/api/reading/explain/route.ts` — общая candidate selection и bounded diagnostic detail.
- `web/src/features/reading/ai/prompt.ts` — правило prose paragraph references.
- `web/tests/reading-ai-contracts.spec.ts` — negative subtype/allowed-set/offset/prose mocks и допустимые формулировки обоих matching modes.
- `web/src/features/listening/review.tsx` — сброс только временного moment при смене вопроса.
- `web/tests/listening-review.spec.ts` — исправление test races/state assumption и два focused regression cases.
- Этот отчёт. Существующие browser runners также обновили свои обычные QA screenshots.

Backend implementation, Cambridge JSON/Answer Keys, grading, frozen snapshots, Smart Translation, Player, privacy gates и production config не менялись. Исходные frontend/backend процессы продолжают работать. Coverage census не запускался.

## 7. Короткие целевые тесты

| Проверка | Результат |
|---|---|
| Reading mocks до первого live | 38 PASS |
| Reading contracts на финальном prompt/code | **39 PASS** |
| Backend Reading AI без browser | **52 PASS**, 1 browser deselected |
| Python/TS probe: deterministic IDs и uncited prose rejection / safe prose, оба matching modes | PASS |
| Baseline: одинаковые focused Listening scenarios, Chromium + WebKit | **2 FAIL / 2 PASS** |
| Финальный Listening: прежний loop flow, Retry, focused clip restore, Part 1–4 positions, оба engines | **8 PASS** |
| TypeScript | PASS |
| Полный ESLint | PASS |
| Live | 3 calls: Information FOUND + Headings FOUND + Information prose_reference |

Перепроверка общего coverage audit, production builds/deploy, массовые AI calls не проводились в Stage 2.

## 8. Final: BLOCKED

Точная воспроизведённая причина Reading определена, prompt исправлен без ослабления evidence validation. Listening gate исправлен и подтверждён одинаковыми baseline/current scenarios. Но последняя реальная генерация Information отклонена, а финальное уточнение prompt после этого не прошло live verification. Поэтому **READY FOR DEPLOY не объявляется**. Осталась одна узкая задача: проверить финальный prompt реальным вызовом в отдельно разрешённом следующем smoke budget. Production Reading AI не включать.
