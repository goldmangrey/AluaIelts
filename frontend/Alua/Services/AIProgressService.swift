import Foundation

protocol AIProgressServiceProtocol: Sendable {
    func generateReport(days: Int, timezone: String, language: AIProgressLanguage) async throws -> AIProgressReportResponse
    func createConversation(days: Int, timezone: String, language: AIProgressLanguage) async throws -> AIProgressConversationResponse
    func getConversation(id: String) async throws -> AIProgressConversationResponse
    func sendMessage(conversationID: String, message: String) async throws -> AIProgressChatResponse
}

final class AIProgressService: AIProgressServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol
    init(apiClient: any APIClientProtocol) { self.apiClient = apiClient }

    func generateReport(days: Int, timezone: String, language: AIProgressLanguage) async throws -> AIProgressReportResponse {
        try await send("/api/v1/partner/ai-analysis/report", body: PeriodRequest(days: days, timezone: timezone, language: language))
    }
    func createConversation(days: Int, timezone: String, language: AIProgressLanguage) async throws -> AIProgressConversationResponse {
        try await send("/api/v1/partner/ai-analysis/conversations", body: PeriodRequest(days: days, timezone: timezone, language: language))
    }
    func getConversation(id: String) async throws -> AIProgressConversationResponse {
        try await apiClient.send(APIEndpoint(path: "/api/v1/partner/ai-analysis/conversations/\(id)", requiresAuthentication: true), responseType: AIProgressConversationResponse.self)
    }
    func sendMessage(conversationID: String, message: String) async throws -> AIProgressChatResponse {
        try await send("/api/v1/partner/ai-analysis/conversations/\(conversationID)/messages", body: MessageRequest(message: message))
    }
    private func send<T: Decodable & Sendable>(_ path: String, body: some Encodable) async throws -> T {
        try await apiClient.send(APIEndpoint(path: path, method: .post, body: body, requiresAuthentication: true), responseType: T.self)
    }
}

private struct PeriodRequest: Encodable {
    let days: Int
    let timezone: String
    let language: AIProgressLanguage
}
private struct MessageRequest: Encodable { let message: String }
