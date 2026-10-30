import Foundation

protocol ProgressServiceProtocol: Sendable {
    func getProgress(days: Int, timezone: String) async throws -> ProgressSnapshot
}

final class ProgressService: ProgressServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func getProgress(days: Int, timezone: String) async throws -> ProgressSnapshot {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/progress",
                queryItems: [
                    URLQueryItem(name: "days", value: String(days)),
                    URLQueryItem(name: "timezone", value: timezone),
                ],
                requiresAuthentication: true
            ),
            responseType: ProgressSnapshot.self
        )
    }
}
