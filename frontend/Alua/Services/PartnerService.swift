import Foundation

protocol PartnerServiceProtocol: Sendable {
    func getStatus() async throws -> PartnerStatus
    func createInvite() async throws -> PartnerInvite
    func acceptInvite(code: String) async throws -> PartnerStatus
    func updateSharing(_ settings: PartnerSharingSettings) async throws -> PartnerStatus
    func revokeRelationship() async throws -> PartnerStatus
    func getDashboard(days: Int, timezone: String) async throws -> PartnerDashboardSnapshot
}

final class PartnerService: PartnerServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol
    init(apiClient: any APIClientProtocol) { self.apiClient = apiClient }

    func getStatus() async throws -> PartnerStatus { try await send("/api/v1/partner/status") }
    func createInvite() async throws -> PartnerInvite { try await send("/api/v1/partner/invitations", method: .post) }
    func acceptInvite(code: String) async throws -> PartnerStatus {
        try await send("/api/v1/partner/invitations/accept", method: .post, body: ["code": code])
    }
    func updateSharing(_ settings: PartnerSharingSettings) async throws -> PartnerStatus {
        try await send("/api/v1/partner/sharing", method: .patch, body: settings)
    }
    func revokeRelationship() async throws -> PartnerStatus {
        try await send("/api/v1/partner/relationship/revoke", method: .post)
    }
    func getDashboard(days: Int, timezone: String) async throws -> PartnerDashboardSnapshot {
        try await apiClient.send(APIEndpoint(path: "/api/v1/partner/dashboard", queryItems: [.init(name: "days", value: String(days)), .init(name: "timezone", value: timezone)], requiresAuthentication: true), responseType: PartnerDashboardSnapshot.self)
    }
    private func send<T: Decodable & Sendable>(_ path: String, method: HTTPMethod = .get, body: (any Encodable)? = nil) async throws -> T {
        try await apiClient.send(APIEndpoint(path: path, method: method, body: body, requiresAuthentication: true), responseType: T.self)
    }
}
