# Фаза 6 — Firestore

AUD-06-01 (VERIFIED, S2): vocabulary `/today` читает все packs и все review states (`vocabulary_review/repository.py:66-77,111-123`), затем фильтрует в памяти. Стоимость и latency растут линейно с днями и словарём; widgets повторно вызывает этот путь (`widgets/service.py:87-109`).

AUD-06-02 (VERIFIED, S2): Mastery `count_distinct_applied_events` stream-ит все markers (`mastery/repository.py:45-53`); Daily Plan и Student Model вызывают это для сводок. Нужен агрегат count или Firestore count aggregation.

AUD-06-03 (VERIFIED, S1): `firestore.rules` и `firestore.indexes.json` в репозитории отсутствуют. Нельзя подтвердить, закрыт ли прямой доступ и развёрнуты ли индексы. Клиент не подключает FirebaseFirestore product, поэтому текущий iOS путь идёт через API, но инфраструктурная гарантия не версионируется.

Размеры текущих session/plan документов выглядят ниже 1 MiB; неограниченных массивов внутри одного review document не найдено. Events и attempts растут подколлекциями, что допустимо. Лимит batch 500 не затрагивается найденным batch из трёх операций (`ai_progress/repository.py:67-80`). Backup/export и TTL для старых conversation/event данных не найдены.
