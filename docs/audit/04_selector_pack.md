# Фаза 4 — Selector и Daily Pack

Межпроцессный тест 20/20 дал одинаковый SHA-256 (`scripts/selector_determinism.txt`). Алгоритм использует SHA-256 и полный tie-breaker digest (`selector.py:122-144`), Python `hash()` и неупорядоченные set/dict в результате не участвуют.

AUD-04-01 (VERIFIED, S1): «introduced» означает наличие ID в любом сохранённом паке, даже если пользователь его не видел (`service.py:203-204`). Это источник потери новых слов из AUD-03-01.

AUD-04-02 (VERIFIED, S2): всего 10 upgrades; до 5 выбираются ежедневно и после двух дней исчерпываются навсегда. При дефиците selector добирает только words, но `_valid_pack` требует ровно 10/20/30; пока words достаточно, это работает (`selector.py:63-68`, `service.py:379-400`).

AUD-04-03 (VERIFIED, S3): конкурентная генерация защищена детерминированным document ID и Firestore `create`; loser читает существующий pack (`contract.py:19-26`, `repository.py:81-90`). Гипотеза о дублировании при гонке опровергнута для одного content/schema version.

Дата вычисляется в переданном IANA timezone (`service.py:68-73`), timezone сохраняется (`models.py:78-84`). При поездке один и тот же local_date переиспользует первый pack; комментарий прямо фиксирует это (`service.py:361-377`). Schema 1 не мигрируется: repository молча пропускает всё не-schema-2 (`repository.py:66-77,111-123`).
