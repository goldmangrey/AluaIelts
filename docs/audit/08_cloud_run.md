# Фаза 8 — Cloud Run и backend performance

Корпус 6,4 MiB читается с локального образа лениво через cached property, а не Firestore (`vocabulary_review/lexicon_repository.py:23-39`). Firebase и OpenAI клиенты ленивые/cached. Это хорошо для cold start, хотя первый vocabulary request платит за JSONL parse/Pydantic validation.

AUD-08-01 (VERIFIED, S2): каждый dependency factory заново строит большой service graph; widgets вызывает Progress service и Vocabulary service, а `/today` выполняет полные scans. Самые тяжёлые пути: `/widgets/snapshot`, `/partner/dashboard`, `/partner/ai-analysis/*`, `/daily-plans/today`. Статическая оценка `/widgets/snapshot`: profile + relationship + full packs + full states + session reads/events + plan; partner mode добавляет progress range scans.

AUD-08-02 (VERIFIED, S2): генерация AI выполняется синхронным SDK, но route корректно переносит весь service в threadpool (`ai_progress/router.py:55-67,97-109`). Firestore sync client также вызывается через threadpool на I/O routes. Явных blocking calls непосредственно в event loop не найдено.

AUD-08-03 (HYPOTHESIS, S2): min-instances, concurrency, timeout, CPU/memory и deploy manifest в репозитории отсутствуют, поэтому cold-start/production limits нельзя подтвердить. Docker копирует только `app`, что ограничивает лишние файлы, но uv устанавливается без version pin (`Dockerfile:8`).

Пагинация есть у recent learning events (`learning_events/repository.py:61-83`), но отсутствует у review packs/states, mastery states/markers и AI messages до применения history limit на клиентском stream.
