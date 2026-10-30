import Foundation

struct Placement: Decodable, Sendable {
    struct Question: Decodable, Sendable { let id: Int; let prompt: String; let options: [String] }
    struct Result: Decodable, Sendable { let difficulty: String; let gaps: [String]; let notice: String }
    let answered: Int; let total: Int; let question: Question?; let result: Result?
}
struct GrammarTopicSummary: Decodable, Sendable {
    struct Topic: Decodable, Sendable, Identifiable {
        let topic_id: String; let title: String; let attempts: Int; let errors: Int; let weak: Bool
        var id: String { topic_id }
    }
    let topics: [Topic]
}
struct LearningQualityService: Sendable {
    let apiClient: any APIClientProtocol
    func placement() async throws -> Placement {
        try await apiClient.send(APIEndpoint(path: "/api/v1/learning-quality/diagnostic", requiresAuthentication: true), responseType: Placement.self)
    }
    func answer(id: Int, choice: Int?) async throws -> Placement {
        struct Request: Encodable { let question_id: Int; let choice: Int? }
        return try await apiClient.send(APIEndpoint(path: "/api/v1/learning-quality/diagnostic/answers", method: .post, body: Request(question_id: id, choice: choice), requiresAuthentication: true), responseType: Placement.self)
    }
    func topics() async throws -> GrammarTopicSummary {
        try await apiClient.send(APIEndpoint(path: "/api/v1/learning-quality/grammar-topics", requiresAuthentication: true), responseType: GrammarTopicSummary.self)
    }
    func action(itemID: String, action: String, eventID: UUID, type: String = "other", comment: String = "") async throws {
        struct Request: Encodable { let action: String; let event_id: UUID; let error_type: String; let comment: String }
        struct Response: Decodable, Sendable { let saved: Bool }
        _ = try await apiClient.send(APIEndpoint(path: "/api/v1/learning-quality/items/\(itemID)/actions", method: .post, body: Request(action: action, event_id: eventID, error_type: type, comment: comment), requiresAuthentication: true), responseType: Response.self)
    }
}
