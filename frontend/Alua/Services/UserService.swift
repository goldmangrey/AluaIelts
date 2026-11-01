protocol UserServiceProtocol: Sendable {
    func getCurrentUserProfile() async throws -> UserProfile
    func register(displayName: String?) async throws -> UserProfile
    func updateCurrentUserProfile(_ update: UserProfileUpdate) async throws -> UserProfile
}

extension UserServiceProtocol {
    func register(displayName: String?) async throws -> UserProfile { throw APIError.transport }
}

private struct RegisterProfileRequest: Encodable, Sendable {
    let display_name: String?
}

final class UserService: UserServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func getCurrentUserProfile() async throws -> UserProfile {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/me", requiresAuthentication: true),
            responseType: UserProfile.self
        )
    }

    func register(displayName: String?) async throws -> UserProfile {
        try await apiClient.send(
            APIEndpoint(path: "/api/v1/auth/register", method: .post,
                        body: RegisterProfileRequest(display_name: displayName), requiresAuthentication: true),
            responseType: UserProfile.self
        )
    }

    func updateCurrentUserProfile(_ update: UserProfileUpdate) async throws -> UserProfile {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/me",
                method: .patch,
                body: update,
                requiresAuthentication: true
            ),
            responseType: UserProfile.self
        )
    }
}
