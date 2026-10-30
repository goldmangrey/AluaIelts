# Фаза 12 — тесты и качество

Результаты: `pytest -q` — exit 5, `no tests ran in 0.03s`; `ruff check app scripts` — passed; `mypy app` — passed для 118 файлов; `compileall` — passed. Xcode Debug Simulator build — succeeded. UI/unit test targets отсутствуют. `pip-audit`, vulture, radon, SwiftLint не установлены/не выполнялись.

AUD-12-01 (VERIFIED, S1): нулевое автотестовое покрытие критичных инвариантов SRS, selector, transactions, timezone, auth/partner consent и schema compatibility.

AUD-12-02 (VERIFIED, S2): Pydantic предупреждает, что поле `LexicalItem.register` затеняет атрибут BaseModel (`vocabulary_review/models.py:49-68`). Сейчас сборку не ломает, но может стать несовместимостью версии.

Первыми нужны: scheduler table tests; 20-process selector; «pack generation ≠ introduced»; two-device event conflicts; emulator test атомарности review; fault-injection на каждом шаге exercise pipeline; timezone KZ/UTC/midnight/travel; старый iOS decoder + новые optional fields/enum; auth IDOR и Partner revoke.
