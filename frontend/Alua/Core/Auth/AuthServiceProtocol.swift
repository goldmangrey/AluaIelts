import Foundation

struct FirebaseIdentity: Sendable, Equatable {
    let uid: String
    let email: String?
    let displayName: String?
}

@MainActor
protocol AuthServiceProtocol: AccessTokenProvider {
    var currentUser: FirebaseIdentity? { get }
    var isConfigured: Bool { get }

    @discardableResult
    func observeAuthState(_ handler: @escaping @MainActor (FirebaseIdentity?) -> Void) -> AnyObject?
    func stopObserving(_ handle: AnyObject)
    func signIn(email: String, password: String) async throws
    func signUp(email: String, password: String) async throws
    func signOut() throws
}

enum AuthServiceError: Error, LocalizedError {
    case notConfigured
    case invalidCredentials
    case invalidEmail
    case emailAlreadyInUse
    case weakPassword
    case networkUnavailable
    case tooManyRequests
    case unknown

    var errorDescription: String? {
        switch self {
        case .notConfigured:
            "Firebase is not configured for this build."
        case .invalidCredentials:
            "The email or password is incorrect."
        case .invalidEmail:
            "Enter a valid email address."
        case .emailAlreadyInUse:
            "An account already exists for this email."
        case .weakPassword:
            "Use a password with at least 6 characters."
        case .networkUnavailable:
            "Check your connection and try again."
        case .tooManyRequests:
            "Too many attempts. Please try again later."
        case .unknown:
            "Authentication could not be completed."
        }
    }
}
