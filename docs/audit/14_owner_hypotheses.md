# Фаза 14 — гипотезы владельца

1. **LIKELY, частично подтверждена.** Debt появляется быстро и после пропусков резко растёт; «без предела» за 180 дней не доказано, так как лестница достигает больших интервалов. `scripts/srs_summary.csv`.
2. **VERIFIED/ОПРОВЕРГНУТА частично.** Again=30 мин вычисляется, но не обслуживается immutable sessions. Hard определён: минимум 12 ч (`scheduler.py:14-23`).
3. **VERIFIED.** Локальной дисковой очереди событий/offline review нет (`APIClient.swift:28-42`).
4. **ОПРОВЕРГНУТА.** Дата пака считается в явно переданном IANA timezone (`service.py:68-73`); iOS передаёт `TimeZone.current.identifier`.
5. **ОПРОВЕРГНУТА для текущей версии.** Детерминированный ID + Firestore create/read winner (`contract.py:19-26`, `repository.py:81-90`).
6. **ОПРОВЕРГНУТА.** Review event и state — одна transaction (`repository.py:178-218`). Для exercise pipeline аналогичная проблема реально есть.
7. **ОПРОВЕРГНУТА для новых optional fields; LIKELY для enum.** Swift Codable игнорирует неизвестные keys, но strict raw-value enums падают на новом case.
8. **VERIFIED/LIKELY.** Debug и Release имеют один URL; backup config не найден. Фактические cloud backups проверить нельзя.
9. **VERIFIED.** Timeout/retry/output cap есть, user/day rate и money ceiling отсутствуют.
10. **VERIFIED частично.** 71 duplicate groups и минимум 3 очевидных смешанных перевода; пустых переводов 0.
