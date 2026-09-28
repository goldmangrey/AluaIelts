protocol APIClientProtocol: Sendable {
    func send<Response: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        responseType: Response.Type
    ) async throws -> Response
}
