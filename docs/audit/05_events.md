# Фаза 5 — события и согласованность

Vocabulary review event ID задаёт клиент; повтор с тем же ID и теми же session/item/rating идемпотентен. Event и Review State записываются одной транзакцией (`vocabulary_review/repository.py:165-218`). Два устройства с разными event ID получают conflict по `review_count`, а не двойное применение (`repository.py:200-214`). Пересборщик review state из событий не найден.

AUD-05-01 (VERIFIED, S0): submit exercise состоит из независимых записей: attempt (`exercises/service.py:145-157`), learning event (176-184), mastery (185-198), session (199-211), daily plan (212-215). Падение между шагами оставляет частично применённый ответ; повтор может вернуть existing attempt, но снова пройти downstream-цепочку. Локальная идемпотентность каждого projection помогает, но общей транзакции/outbox нет.

AUD-05-02 (VERIFIED, S2): learning event repository при AlreadyExists возвращает существующее событие без сравнения payload (`learning_events/repository.py:36-54`); сравнение выполняется service, но repository сам не защищает инвариант.

AUD-05-03 (VERIFIED, S2): автоматического rebuild/reconciliation для Review State, Mastery, session progress и Daily Plan не найдено. Mastery защищён marker-транзакцией (`mastery/repository.py:57-103`), но repair path отсутствует.
