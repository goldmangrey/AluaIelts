import Foundation
import Observation

@MainActor @Observable
final class AIProgressStore {
    private(set) var report: AIProgressReportResponse?
    private(set) var conversation: AIProgressChatConversation?
    private(set) var messages: [AIProgressChatMessage] = []
    private(set) var suggestedFollowups: [String] = []
    private(set) var isGeneratingReport = false
    private(set) var isSendingMessage = false
    private(set) var isAvailable = true
    var errorMessage: String?
    @ObservationIgnored private let service: any AIProgressServiceProtocol

    init(service: any AIProgressServiceProtocol) { self.service = service }

    func generateReport(days: Int) async {
        guard !isGeneratingReport, isAvailable else { return }
        isGeneratingReport = true; errorMessage = nil
        defer { isGeneratingReport = false }
        do {
            report = try await service.generateReport(days: days, timezone: TimeZone.current.identifier, language: language)
        } catch { handle(error) }
    }

    func startConversation(days: Int) async {
        guard !isSendingMessage, isAvailable else { return }
        isSendingMessage = true; errorMessage = nil
        defer { isSendingMessage = false }
        do {
            let response = try await service.createConversation(days: days, timezone: TimeZone.current.identifier, language: language)
            conversation = response.conversation; messages = response.messages; suggestedFollowups = []
        } catch { handle(error) }
    }

    func loadConversation() async {
        guard let id = conversation?.conversationID, !isSendingMessage else { return }
        do {
            let response = try await service.getConversation(id: id)
            conversation = response.conversation; messages = response.messages
        } catch { handle(error) }
    }

    func sendMessage(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let id = conversation?.conversationID, !trimmed.isEmpty, !isSendingMessage, isAvailable else { return }
        isSendingMessage = true; errorMessage = nil
        defer { isSendingMessage = false }
        do {
            let response = try await service.sendMessage(conversationID: id, message: trimmed)
            messages.append(AIProgressChatMessage(messageID: UUID().uuidString, role: "user", content: trimmed, createdAt: Date(), supportingFactIDs: []))
            messages.append(response.message)
            suggestedFollowups = Array(response.answer.suggestedFollowups.prefix(3))
        } catch { handle(error) }
    }

    func permissionChanged(isAllowed: Bool) {
        isAvailable = isAllowed
        if !isAllowed { report = nil; conversation = nil; messages = []; suggestedFollowups = [] }
    }

    func clear() {
        report = nil; conversation = nil; messages = []; suggestedFollowups = []
        isGeneratingReport = false; isSendingMessage = false; isAvailable = true; errorMessage = nil
    }

    private var language: AIProgressLanguage {
        Locale.current.language.languageCode?.identifier == "ru" ? .ru : .en
    }
    private func handle(_ error: Error) {
        if case let APIError.server(_, code, _) = error,
           code == "partner_ai_analysis_not_allowed" || code == "partner_not_authorized" {
            isAvailable = false
            errorMessage = "AI analysis is no longer available."
        } else if case APIError.unauthorized = error {
            isAvailable = false
            errorMessage = "AI analysis is no longer available."
        } else {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? "AI analysis is temporarily unavailable. Your progress dashboard is still available."
        }
    }
}
