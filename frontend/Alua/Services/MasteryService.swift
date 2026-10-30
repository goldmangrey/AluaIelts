import Foundation

protocol MasteryServiceProtocol: Sendable {
    func getMasteryStates(
        contentType: MasteryContentType?,
        dimension: MasteryDimension?,
        level: MasteryLevel?,
        limit: Int,
        offset: Int
    ) async throws -> MasteryStatesResponse
    func getContentMastery(
        contentType: MasteryContentType,
        contentID: String
    ) async throws -> ContentMasterySummary
    func getStudentModel() async throws -> StudentModelSnapshot
}

final class MasteryService: MasteryServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func getMasteryStates(
        contentType: MasteryContentType? = nil,
        dimension: MasteryDimension? = nil,
        level: MasteryLevel? = nil,
        limit: Int = 100,
        offset: Int = 0
    ) async throws -> MasteryStatesResponse {
        var queryItems = [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String(offset)),
        ]
        if let contentType {
            queryItems.append(URLQueryItem(name: "content_type", value: contentType.rawValue))
        }
        if let dimension {
            queryItems.append(URLQueryItem(name: "dimension", value: dimension.rawValue))
        }
        if let level {
            queryItems.append(URLQueryItem(name: "level", value: level.rawValue))
        }
        return try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/mastery",
                queryItems: queryItems,
                requiresAuthentication: true
            ),
            responseType: MasteryStatesResponse.self
        )
    }

    func getContentMastery(
        contentType: MasteryContentType,
        contentID: String
    ) async throws -> ContentMasterySummary {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/mastery/content/\(contentType.rawValue)/\(contentID)",
                requiresAuthentication: true
            ),
            responseType: ContentMasterySummary.self
        )
    }

    func getStudentModel() async throws -> StudentModelSnapshot {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/student-model", requiresAuthentication: true),
            responseType: StudentModelSnapshot.self
        )
    }
}
