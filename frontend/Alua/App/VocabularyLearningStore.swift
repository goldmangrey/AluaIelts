import Foundation
import Observation

@MainActor @Observable
final class VocabularyLearningStore {
    private var generation = UUID()
    private(set) var today: VocabularyLearningToday?
    private(set) var session: VocabularyReviewSession?
    private(set) var isLoading = false
    var errorMessage: String?
    @ObservationIgnored private let service: any VocabularyLearningServiceProtocol
    @ObservationIgnored private let notifications: VocabularyNotificationService
    init(service: any VocabularyLearningServiceProtocol, notifications: VocabularyNotificationService) {
        self.service = service; self.notifications = notifications
    }
    func loadToday() async {
        guard !isLoading else { return }; isLoading = true; errorMessage = nil
        let startedGeneration = generation
        do {
            let value = try await service.today(timezone: TimeZone.current.identifier)
            guard generation == startedGeneration, !Task.isCancelled else { return }
            today = value
            await notifications.scheduleDailyReminders(for: value)
        } catch { errorMessage = (error as? LocalizedError)?.errorDescription ?? "Vocabulary learning is unavailable." }
        isLoading = false
    }
    func loadSession(id: String) async {
        isLoading = true; errorMessage = nil
        do { session = try await service.session(id: id) }
        catch { errorMessage = (error as? LocalizedError)?.errorDescription ?? "Review could not be loaded." }
        isLoading = false
    }
    func submit(card: VocabularyReviewCard, rating: VocabularyReviewRating, eventID: UUID) async -> Bool {
        guard let session else { return false }
        do { _ = try await service.submit(sessionID: session.sessionID, lexicalItemID: card.lexicalItemID, rating: rating, eventID: eventID); return true }
        catch { errorMessage = "Your rating was not saved. Connect to the internet and try again."; return false }
    }
    func clearSession() { session = nil; errorMessage = nil }
    func clear() { generation = UUID(); today = nil; session = nil; isLoading = false; errorMessage = nil }
}
