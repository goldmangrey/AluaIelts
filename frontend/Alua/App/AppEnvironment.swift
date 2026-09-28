import Foundation

enum AppEnvironment: String, Sendable {
    case development
    case production

    static var current: AppEnvironment {
        #if DEBUG
        .development
        #else
        .production
        #endif
    }

    var apiBaseURL: URL {
        if let configuredValue = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String,
           !configuredValue.isEmpty,
           let configuredURL = URL(string: configuredValue)
        {
            return configuredURL
        }

        switch self {
        case .development:
            return Self.url("http://127.0.0.1:8000")
        case .production:
            return Self.url("https://api.alua.app")
        }
    }

    private static func url(_ value: String) -> URL {
        guard let url = URL(string: value) else {
            preconditionFailure("Invalid bundled API URL configuration.")
        }
        return url
    }
}
