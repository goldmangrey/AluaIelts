import Foundation

protocol ExerciseServiceProtocol: Sendable {
    func createSession(date: String, dailyPlanItemID: String) async throws -> ExerciseSession
    func getSession(id: String) async throws -> ExerciseSession
    func submitChoiceAnswer(sessionID: String, exerciseID: String, attemptID: UUID, optionID: String) async throws -> ExerciseAttemptResult
    func submitUnknown(sessionID: String, exerciseID: String, attemptID: UUID) async throws -> ExerciseAttemptResult
    func submitTextAnswer(sessionID: String, exerciseID: String, attemptID: UUID, answer: String) async throws -> ExerciseAttemptResult
}

final class ExerciseService: ExerciseServiceProtocol, Sendable {
    private struct CreateRequest: Encodable {
        let localDate: String; let dailyPlanItemID: String
        enum CodingKeys: String, CodingKey { case localDate = "local_date"; case dailyPlanItemID = "daily_plan_item_id" }
    }
    private struct AttemptRequest: Encodable {
        let attemptID: UUID
        let selectedOptionID: String?
        let textAnswer: String?
        let clientOccurredAt: Date
        enum CodingKeys: String, CodingKey {
            case attemptID = "attempt_id"
            case selectedOptionID = "selected_option_id"
            case textAnswer = "text_answer"
            case clientOccurredAt = "client_occurred_at"
        }
    }
    private let apiClient: any APIClientProtocol
    init(apiClient: any APIClientProtocol) { self.apiClient = apiClient }

    func createSession(date: String, dailyPlanItemID: String) async throws -> ExerciseSession {
        try await apiClient.send(APIEndpoint(path: "/api/v1/exercise-sessions", method: .post, body: CreateRequest(localDate: date, dailyPlanItemID: dailyPlanItemID), requiresAuthentication: true), responseType: ExerciseSession.self)
    }
    func getSession(id: String) async throws -> ExerciseSession {
        try await apiClient.send(APIEndpoint(path: "/api/v1/exercise-sessions/\(id)", requiresAuthentication: true), responseType: ExerciseSession.self)
    }
    func submitChoiceAnswer(sessionID: String, exerciseID: String, attemptID: UUID, optionID: String) async throws -> ExerciseAttemptResult {
        try await submit(sessionID: sessionID, exerciseID: exerciseID, attemptID: attemptID, optionID: optionID, text: nil)
    }
    func submitTextAnswer(sessionID: String, exerciseID: String, attemptID: UUID, answer: String) async throws -> ExerciseAttemptResult {
        try await submit(sessionID: sessionID, exerciseID: exerciseID, attemptID: attemptID, optionID: nil, text: answer)
    }
    func submitUnknown(sessionID: String, exerciseID: String, attemptID: UUID) async throws -> ExerciseAttemptResult {
        struct UnknownRequest: Encodable { let attempt_id: UUID; let unknown = true }
        return try await apiClient.send(APIEndpoint(path: "/api/v1/exercise-sessions/\(sessionID)/exercises/\(exerciseID)/attempts", method: .post, body: UnknownRequest(attempt_id: attemptID), requiresAuthentication: true), responseType: ExerciseAttemptResult.self)
    }
    private func submit(sessionID: String, exerciseID: String, attemptID: UUID, optionID: String?, text: String?) async throws -> ExerciseAttemptResult {
        try await apiClient.send(APIEndpoint(path: "/api/v1/exercise-sessions/\(sessionID)/exercises/\(exerciseID)/attempts", method: .post, body: AttemptRequest(attemptID: attemptID, selectedOptionID: optionID, textAnswer: text, clientOccurredAt: Date()), requiresAuthentication: true), responseType: ExerciseAttemptResult.self)
    }
}
