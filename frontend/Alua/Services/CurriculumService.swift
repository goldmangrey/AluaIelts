protocol CurriculumServiceProtocol: Sendable {
    func getProgram() async throws -> CurriculumProgram
    func getMyCurriculum() async throws -> UserCurriculumOverview
    func startNode(id: String) async throws -> UserCurriculumOverview
}

final class CurriculumService: CurriculumServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func getProgram() async throws -> CurriculumProgram {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/curriculum", requiresAuthentication: true),
            responseType: CurriculumProgram.self
        )
    }

    func getMyCurriculum() async throws -> UserCurriculumOverview {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/curriculum/me", requiresAuthentication: true),
            responseType: UserCurriculumOverview.self
        )
    }

    func startNode(id: String) async throws -> UserCurriculumOverview {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/curriculum/me/nodes/\(id)/start",
                method: .post,
                requiresAuthentication: true
            ),
            responseType: UserCurriculumOverview.self
        )
    }
}
