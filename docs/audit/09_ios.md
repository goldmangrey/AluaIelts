# Фаза 9 — iOS-клиент

Simulator Debug build с Xcode 27.0 завершился `BUILD SUCCEEDED` за 14,4 с, включая `AluaWidgets`. Основные stores помечены `@MainActor`; service/API модели — `Sendable`. Тестовых targets нет.

AUD-09-01 (VERIFIED, S1): нет дисковой очереди review/learning events и offline retry. Review submit вызывается напрямую; транспортная ошибка теряет действие после закрытия UI. Поиск `queue/offline` находит только текст состояния, не persistence. `APIClient.swift:28-42` делает один запрос.

AUD-09-02 (VERIFIED, S1): APIClient не повторяет 401 с принудительным refresh и не задаёт timeout/backoff (`APIClient.swift:28-43,64-100`). Firebase `getIDToken()` обычно обновляет истёкший token, но race/revocation после создания request не обработаны.

AUD-09-03 (VERIFIED, S1): десятки wire enums используют синтезированный strict Codable; неизвестное значение ломает декодирование всего ответа, например `VocabularyLearningModels.swift:3-6`, `DailyPlanModels.swift:3-74`. Новые необязательные поля обычно безопасны, новые enum cases — нет.

AUD-09-04 (VERIFIED, S2): Debug и Release указывают на один production Cloud Run URL (`project.yml:31-36`, `AppEnvironment.swift:23-28`). Разделения dev/prod API нет.

AUD-09-05 (VERIFIED, S2): 143 грубо подсчитанных UI string literals; String Catalog/Localizable не найден. Озвучка жёстко выбирает `en-US`, fallback/availability/audio session отсутствуют (`VocabularyReviewSessionView.swift:78-79`).

Уведомления корректно используют Calendar.current и максимум 2 на текущий день, но не отменяются после завершения review; ошибки schedule проглатываются (`VocabularyNotificationService.swift:36-53,71-76`). Dynamic Type в основном наследуется от SwiftUI, но VoiceOver labels/контраст не проверялись на устройстве.
