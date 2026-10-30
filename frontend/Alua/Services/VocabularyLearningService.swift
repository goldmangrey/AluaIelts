import Foundation

protocol VocabularyLearningServiceProtocol: Sendable {
    func today(timezone: String) async throws -> VocabularyLearningToday
    func session(id: String) async throws -> VocabularyReviewSession
    func submit(sessionID: String, lexicalItemID: String, rating: VocabularyReviewRating, eventID: UUID) async throws -> SubmitVocabularyReviewResult
}

final class VocabularyLearningService: VocabularyLearningServiceProtocol, Sendable {
    private struct ResponseRequest: Encodable {
        let eventID: UUID; let lexicalItemID: String; let rating: VocabularyReviewRating
        enum CodingKeys: String, CodingKey { case eventID = "event_id"; case lexicalItemID = "lexical_item_id"; case rating }
    }
    private let apiClient: any APIClientProtocol
    init(apiClient: any APIClientProtocol) { self.apiClient = apiClient }
    func today(timezone: String) async throws -> VocabularyLearningToday {
        try await apiClient.send(APIEndpoint(path: "/api/v1/vocabulary-learning/today", queryItems: [.init(name: "timezone", value: timezone)], requiresAuthentication: true), responseType: VocabularyLearningToday.self)
    }
    func session(id: String) async throws -> VocabularyReviewSession {
        try await apiClient.send(APIEndpoint(path: "/api/v1/vocabulary-learning/review-sessions/\(id)", requiresAuthentication: true), responseType: VocabularyReviewSession.self)
    }
    func submit(sessionID: String, lexicalItemID: String, rating: VocabularyReviewRating, eventID: UUID) async throws -> SubmitVocabularyReviewResult {
        try await apiClient.send(APIEndpoint(path: "/api/v1/vocabulary-learning/review-sessions/\(sessionID)/responses", method: .post, body: ResponseRequest(eventID: eventID, lexicalItemID: lexicalItemID, rating: rating), requiresAuthentication: true), responseType: SubmitVocabularyReviewResult.self)
    }
}
