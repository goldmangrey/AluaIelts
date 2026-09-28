import Foundation

struct ServerErrorEnvelope: Decodable {
    let error: ServerErrorDetail
}

struct ServerErrorDetail: Decodable {
    let code: String
    let message: String
}

enum APIError: Error, LocalizedError {
    case invalidURL
    case transport
    case invalidResponse
    case unauthorized(message: String)
    case server(statusCode: Int, backendCode: String?, message: String)
    case decoding

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            "The request URL is invalid."
        case .transport:
            "The service could not be reached. Please try again."
        case .invalidResponse:
            "The server returned an invalid response."
        case let .unauthorized(message):
            message
        case let .server(_, _, message):
            message
        case .decoding:
            "The server response could not be read."
        }
    }
}
