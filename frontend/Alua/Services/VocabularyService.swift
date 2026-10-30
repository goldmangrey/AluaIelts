import Foundation

protocol VocabularyServiceProtocol: Sendable {
    func listTracks() async throws -> [VocabularyTrackSummary]
    func getTrack(id: String) async throws -> VocabularyTrackDetail
    func getItem(id: String) async throws -> VocabularyItem
    func getCurriculumNode(id: String) async throws -> CurriculumVocabularyResponse
    func search(query: String, limit: Int) async throws -> VocabularyListResponse
}

final class VocabularyService: VocabularyServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func listTracks() async throws -> [VocabularyTrackSummary] {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/vocabulary/tracks", requiresAuthentication: true),
            responseType: [VocabularyTrackSummary].self
        )
    }

    func getTrack(id: String) async throws -> VocabularyTrackDetail {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/vocabulary/tracks/\(id)", requiresAuthentication: true),
            responseType: VocabularyTrackDetail.self
        )
    }

    func getItem(id: String) async throws -> VocabularyItem {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/vocabulary/items/\(id)", requiresAuthentication: true),
            responseType: VocabularyItem.self
        )
    }

    func getCurriculumNode(id: String) async throws -> CurriculumVocabularyResponse {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/vocabulary/curriculum-nodes/\(id)",
                requiresAuthentication: true
            ),
            responseType: CurriculumVocabularyResponse.self
        )
    }

    func search(query: String, limit: Int = 50) async throws -> VocabularyListResponse {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/vocabulary",
                queryItems: [
                    URLQueryItem(name: "q", value: query),
                    URLQueryItem(name: "limit", value: String(limit)),
                ],
                requiresAuthentication: true
            ),
            responseType: VocabularyListResponse.self
        )
    }
}
