# Фаза 7 — безопасность и приватность

Все 45 бизнес-маршрутов требуют Firebase bearer token; UID берётся из token (`core/auth.py:20-41`). Partner dashboard и AI повторно проверяют активную relationship и sharing settings (`partner/service.py:132-190`, `ai_progress/service.py:166-180`). Сырые invite codes не сохраняются, используется SHA-256 (`partner/service.py:37-45,64-79`).

AUD-07-01 (VERIFIED, S1): нет per-user/day rate limit, quota или денежного ceiling для AI. Один report может сделать два OpenAI вызова при невалидных fact refs (`ai_progress/service.py:54-67`); chat — также два (`114-148`). Есть timeout/retry/token cap, но не budget cap (`core/config.py:50-75`).

AUD-07-02 (VERIFIED, S1): account deletion и каскадное удаление user/partner/AI данных не найдены; Firebase App Check не найден. Это privacy/abuse gap до внешнего релиза.

AUD-07-03 (VERIFIED, S2): Docker base `python:3.12-slim` не закреплён digest/patch и контейнер запускается root (`backend/Dockerfile:1-18`). `.dockerignore` корректно исключает env/secrets (`backend/.dockerignore:1-13`).

Секреты: `.secrets/` и `backend/.env` присутствуют, содержимое не читалось; git их не отслеживает и история по путям пуста. Поиск значений/паттернов в истории не выполнялся, чтобы не вывести секреты. `pip-audit` не установлен; сетевой dependency audit не выполнялся. Prompt injection частично учтён явным «untrusted data» и fact-ID validator (`ai_progress/prompts.py:11-24,46-65`).
