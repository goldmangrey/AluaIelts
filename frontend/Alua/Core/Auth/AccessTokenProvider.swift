protocol AccessTokenProvider: Sendable {
    func accessToken() async throws -> String?
    /// Stable for a session even when the SDK refreshes the bearer token.
    func sessionIdentifier() async throws -> String?
    func authenticationRejected(session: String?) async
}

extension AccessTokenProvider {
    func authenticationRejected(session: String?) async {}
    func sessionIdentifier() async throws -> String? { try await accessToken() }
}
