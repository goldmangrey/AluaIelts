import Foundation

protocol GrammarServiceProtocol: Sendable {
    func getLessons(
        query: String?, cefr: String?, stageID: String?, limit: Int, offset: Int
    ) async throws -> GrammarListResponse
    func search(query: String) async throws -> GrammarListResponse
    func getLesson(id: String) async throws -> GrammarLesson
    func getStage(id: String) async throws -> GrammarStageResponse
    func getLessonForCurriculumNode(id: String) async throws -> GrammarLesson
}

final class GrammarService: GrammarServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func getLessons(
        query: String? = nil,
        cefr: String? = nil,
        stageID: String? = nil,
        limit: Int = 50,
        offset: Int = 0
    ) async throws -> GrammarListResponse {
        var queryItems = [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String(offset)),
        ]
        if let query { queryItems.append(URLQueryItem(name: "q", value: query)) }
        if let cefr { queryItems.append(URLQueryItem(name: "cefr", value: cefr)) }
        if let stageID { queryItems.append(URLQueryItem(name: "stage_id", value: stageID)) }
        return try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/grammar",
                queryItems: queryItems,
                requiresAuthentication: true
            ),
            responseType: GrammarListResponse.self
        )
    }

    func search(query: String) async throws -> GrammarListResponse {
        try await getLessons(query: query, limit: 50, offset: 0)
    }

    func getLesson(id: String) async throws -> GrammarLesson {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/grammar/lessons/\(id)", requiresAuthentication: true),
            responseType: GrammarLesson.self
        )
    }

    func getStage(id: String) async throws -> GrammarStageResponse {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/grammar/stages/\(id)", requiresAuthentication: true),
            responseType: GrammarStageResponse.self
        )
    }

    func getLessonForCurriculumNode(id: String) async throws -> GrammarLesson {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/grammar/curriculum-nodes/\(id)",
                requiresAuthentication: true
            ),
            responseType: GrammarLesson.self
        )
    }
}
