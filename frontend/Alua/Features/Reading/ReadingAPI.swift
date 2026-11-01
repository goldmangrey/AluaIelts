import CryptoKit
import Foundation

protocol ReadingAPIProtocol: Sendable {
    func send<T: Decodable & Sendable>(_ endpoint: APIEndpoint, as type: T.Type) async throws -> T
    func asset(_ asset: ReadingAsset, cached: Data?) async throws -> Data
}
struct ReadingAPI: ReadingAPIProtocol {
    let client: any APIClientProtocol
    let baseURL: URL
    let tokens: any AccessTokenProvider
    func send<T: Decodable & Sendable>(_ endpoint: APIEndpoint, as type: T.Type) async throws -> T {
        try await client.send(endpoint, responseType: type)
    }
    func asset(_ asset: ReadingAsset, cached: Data?) async throws -> Data {
        // Build from the allowed ID, never trust a path or host embedded in content.
        let url = baseURL.appending(path: "api/v1/reading/assets").appendingPathComponent(asset.id)
        let identity = try await tokens.sessionIdentifier()
        guard let token = try await tokens.accessToken(), !token.isEmpty else {
            throw APIError.unauthorized(message: "Необходимо подключить устройство.")
        }
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        if cached != nil { request.setValue("\"\(asset.sha256)\"", forHTTPHeaderField: "If-None-Match") }
        let (data, response) = try await URLSession.shared.data(for: request)
        try Task.checkCancellation()
        guard try await tokens.sessionIdentifier() == identity else { throw CancellationError() }
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        let bytes: Data
        if http.statusCode == 304, let cached { bytes = cached }
        else if http.statusCode == 200, http.mimeType == "image/png" { bytes = data }
        else if http.statusCode == 401 { throw APIError.unauthorized(message: "Необходимо подключить устройство.") }
        else { throw APIError.invalidResponse }
        guard ReadingFiles.hash(bytes) == asset.sha256 else { throw APIError.decoding }
        return bytes
    }
}
enum ReadingCoding {
    static func decoder() -> JSONDecoder {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .custom { decoder in
            let c = try decoder.singleValueContainer(), value = try c.decode(String.self)
            let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = f.date(from: value) { return date }
            f.formatOptions = [.withInternetDateTime]
            guard let date = f.date(from: value) else { throw DecodingError.dataCorruptedError(in: c, debugDescription: "Invalid server date") }
            return date
        }
        return d
    }
    static func encoder() -> JSONEncoder { let e = JSONEncoder(); e.dateEncodingStrategy = .iso8601; return e }
}
