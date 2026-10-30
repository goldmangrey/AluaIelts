# Фаза 13 — эксплуатация

Есть structured logging и безопасный общий 500 response (`main.py:35-54`), но request/correlation ID middleware не найден. Crashlytics, metrics/tracing, dashboards и alerts не найдены.

AUD-13-01 (VERIFIED, S1): Debug/Release используют один API URL; отдельные Firebase project files/configs не найдены (`project.yml:31-36`). Риск смешения dev/prod данных подтверждён конфигурацией клиента, но backend project deployment проверить нельзя.

AUD-13-02 (VERIFIED, S2): CI/CD, rollback manifest, migration process, Firestore backup/export, runbook и диагностический экран версии/последней sync/offline queue отсутствуют.

AUD-13-03 (VERIFIED, S2): миграции ad hoc: Daily Plan имеет `_migrate`, а Vocabulary repository просто скрывает старые schema docs (`vocabulary_review/repository.py:66-77,111-123`). Нет реестра миграций и dry-run/reconciliation.

Документация ограничена README/local setup/lexicon sources; production operations не документированы. До релиза нужны versioned IaC/deploy config, отдельные projects, scheduled export с restore drill, correlation IDs и минимум error-rate/latency/OpenAI-spend alerts.
