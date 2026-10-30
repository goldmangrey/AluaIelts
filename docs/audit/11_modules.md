# Фаза 11 — сложность и польза модулей

Backend LOC: exercises 1590, vocabulary_review 1436, ai_progress 1057, daily_plan 938, mastery 683, curriculum 677, partner 670, progress 665, vocabulary 581, learning_events 522, widgets 440, grammar 401, student_model 288, users 215. Тестов нет ни у одного.

AUD-11-01 (VERIFIED, S2): DI graphs копируются в routers (особенно daily plan/exercises/widgets), что затрудняет единый lifecycle/caching и тестирование. Доказательство: `exercises/router.py:44-100`, `daily_plan/router.py:30-60`, `widgets/router.py:26-41`.

AUD-11-02 (LIKELY, S2): существуют два vocabulary слоя: legacy `modules/vocabulary`/старый JSON и canonical V2 `vocabulary_review`/JSONL. Curriculum/exercises используют первый, SRS/widgets — второй; alias map частично связывает ID. Это создаёт риск расходящихся переводов/метаданных и дублированной логики.

Кандидаты на заморозку до стабилизации ежедневного цикла: AI Progress, AI Exercise generation (оставить deterministic fallback), Student Model advanced analytics, Partner analytics beyond status, сложные Progress comparisons. Не удалять пока: Auth/User, canonical Vocabulary V2, Review/Events, минимальный Daily Plan, Widget snapshot.

«Последний раз менялся» для новых модулей установить нельзя: они untracked. Неиспользуемых backend endpoints уверенно не доказано — Swift services существуют для основных модулей, но runtime telemetry отсутствует.
