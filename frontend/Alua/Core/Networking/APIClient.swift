import Foundation

final class APIClient: APIClientProtocol, @unchecked Sendable {
    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    private let tokenProvider: any AccessTokenProvider

    init(
        baseURL: URL,
        session: URLSession = .shared,
        decoder: JSONDecoder = APIClient.makeDecoder(),
        encoder: JSONEncoder = JSONEncoder(),
        tokenProvider: any AccessTokenProvider
    ) {
        self.baseURL = baseURL
        self.session = session
        self.decoder = decoder
        self.encoder = encoder
        self.tokenProvider = tokenProvider
    }

    func send<Response: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        responseType: Response.Type
    ) async throws -> Response {
        let request = try await makeRequest(for: endpoint)
        let data: Data
        let response: URLResponse

        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.transport
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200 ... 299).contains(httpResponse.statusCode) else {
            throw makeServerError(statusCode: httpResponse.statusCode, data: data)
        }

        do {
            return try decoder.decode(responseType, from: data)
        } catch {
            throw APIError.decoding
        }
    }

    private func makeRequest(for endpoint: APIEndpoint) async throws -> URLRequest {
        let cleanPath = endpoint.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let endpointURL = baseURL.appending(path: cleanPath)
        guard var components = URLComponents(url: endpointURL, resolvingAgainstBaseURL: false) else {
            throw APIError.invalidURL
        }
        if !endpoint.queryItems.isEmpty {
            components.queryItems = endpoint.queryItems
        }
        guard let url = components.url else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        endpoint.headers.forEach { request.setValue($0.value, forHTTPHeaderField: $0.key) }
        if let body = endpoint.body {
            request.httpBody = try encoder.encode(body)
            if request.value(forHTTPHeaderField: "Content-Type") == nil {
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            }
        }
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if endpoint.requiresAuthentication {
            guard let token = try await tokenProvider.accessToken(), !token.isEmpty else {
                throw APIError.unauthorized(message: "Please sign in to continue.")
            }
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    private func makeServerError(statusCode: Int, data: Data) -> APIError {
        let backendError = try? decoder.decode(ServerErrorEnvelope.self, from: data).error
        let message = backendError?.message ?? "The server could not complete the request."
        if statusCode == 401 {
            return .unauthorized(message: message)
        }
        return .server(
            statusCode: statusCode,
            backendCode: backendError?.code,
            message: message
        )
    }

    private static func makeDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}
