# Фаза 0 — разведка

Аудит выполнен 2026-10-28 по текущему рабочему дереву. Оно содержит крупный незакоммиченный набор изменений; исходники не изменялись. В проекте 126 Python- и 103 Swift-файла, суммарно 19 611 строк Python/Swift. История содержит только два коммита (оба 2026-09-28), поэтому churn и «последний раз менялся» неинформативны.

Точки входа: `backend/app/main.py:16-62`, `frontend/Alua/App/AluaApp.swift`, bundle виджетов `frontend/AluaWidgets/AluaWidgetsBundle.swift`. Python 3.12/FastAPI/Pydantic/Firebase Admin/OpenAI зафиксированы в `backend/pyproject.toml:1-28`; iOS 17 и Firebase iOS 12.11.0 — в `frontend/project.yml:1-13`.

Найдено 47 HTTP-маршрутов: 45 требуют `get_current_user`, публичны только `/` и `/api/v1/health`. UID в защищённых обработчиках берётся из проверенного токена (`backend/app/core/auth.py:20-41`). Основные коллекции: `users`, `dailyPlans`, `learningEvents`, `masteryStates`, `masteryAppliedEvents`, `exerciseSessions`, `vocabularyDailyPacks`, `vocabularyReviewStates`, `vocabularyReviewSessions`, `vocabularyReviewEvents`, `partnerRelationships`, `partnerInvites`, `aiConversations`.

CI, `firestore.rules`, `firestore.indexes.json`, конфигурация backup/export и runbook не найдены. TODO/FIXME/HACK в Python/Swift не найдены. `.secrets/` и `backend/.env` существуют, но содержимое не читалось; они не отслеживаются git и история по этим путям пуста. `backend/.env.example` отслеживается как шаблон.

AUD-00-01 (VERIFIED, S2): практически вся новая функциональность не находится в git-истории, что делает аудит регрессий и откат ненадёжными. Доказательство: `git status --short` показывает десятки `??`; `git log` — два коммита.

AUD-00-02 (VERIFIED, S2): отсутствует CI и инфраструктурная конфигурация Firestore. Воспроизведение: `rg --files -g '*.github/**' -g '*firestore*'` находит только Python-обёртку клиента.
