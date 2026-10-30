import Foundation

protocol DailyPlanServiceProtocol: Sendable {
    func ensureToday(timezone: String) async throws -> DailyPlan
    func getToday(timezone: String) async throws -> DailyPlan
    func getPlan(date: String) async throws -> DailyPlan
}

final class DailyPlanService: DailyPlanServiceProtocol, Sendable {
    private struct EnsureRequest: Encodable, Sendable {
        let timezone: String
    }

    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func ensureToday(timezone: String) async throws -> DailyPlan {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/daily-plans/today",
                method: .post,
                body: EnsureRequest(timezone: timezone),
                requiresAuthentication: true
            ),
            responseType: DailyPlan.self
        )
    }

    func getToday(timezone: String) async throws -> DailyPlan {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/daily-plans/today",
                queryItems: [URLQueryItem(name: "timezone", value: timezone)],
                requiresAuthentication: true
            ),
            responseType: DailyPlan.self
        )
    }

    func getPlan(date: String) async throws -> DailyPlan {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/daily-plans/\(date)",
                requiresAuthentication: true
            ),
            responseType: DailyPlan.self
        )
    }
}
