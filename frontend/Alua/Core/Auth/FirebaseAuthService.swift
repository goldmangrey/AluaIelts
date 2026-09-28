import FirebaseAuth
import Foundation

@MainActor
final class FirebaseAuthService: AuthServiceProtocol {
    private let auth: Auth?
    let isConfigured: Bool

    init() {
        isConfigured = FirebaseBootstrap.configureIfAvailable()
        auth = isConfigured ? Auth.auth() : nil
    }

    var currentUser: FirebaseIdentity? {
        auth?.currentUser.map(Self.identity(from:))
    }

    func observeAuthState(
        _ handler: @escaping @MainActor (FirebaseIdentity?) -> Void
    ) -> AnyObject? {
        guard let auth else {
            handler(nil)
            return nil
        }
        return auth.addStateDidChangeListener { _, user in
            Task { @MainActor in
                handler(user.map(Self.identity(from:)))
            }
        } as AnyObject
    }

    func stopObserving(_ handle: AnyObject) {
        guard let auth, let listener = handle as? NSObjectProtocol else { return }
        auth.removeStateDidChangeListener(listener)
    }

    func signIn(email: String, password: String) async throws {
        guard let auth else { throw AuthServiceError.notConfigured }
        do {
            try await auth.signIn(withEmail: email, password: password)
        } catch {
            throw Self.map(error)
        }
    }

    func signUp(email: String, password: String) async throws {
        guard let auth else { throw AuthServiceError.notConfigured }
        do {
            try await auth.createUser(withEmail: email, password: password)
        } catch {
            throw Self.map(error)
        }
    }

    func signOut() throws {
        guard let auth else { throw AuthServiceError.notConfigured }
        do {
            try auth.signOut()
        } catch {
            throw AuthServiceError.unknown
        }
    }

    func accessToken() async throws -> String? {
        guard let auth else { throw AuthServiceError.notConfigured }
        guard let user = auth.currentUser else { return nil }
        do {
            return try await user.getIDToken()
        } catch {
            throw Self.map(error)
        }
    }

    private static func identity(from user: User) -> FirebaseIdentity {
        FirebaseIdentity(uid: user.uid, email: user.email, displayName: user.displayName)
    }

    private static func map(_ error: Error) -> AuthServiceError {
        guard let code = AuthErrorCode(rawValue: (error as NSError).code) else {
            return .unknown
        }
        switch code {
        case .invalidCredential, .wrongPassword, .userNotFound:
            return .invalidCredentials
        case .invalidEmail:
            return .invalidEmail
        case .emailAlreadyInUse:
            return .emailAlreadyInUse
        case .weakPassword:
            return .weakPassword
        case .networkError:
            return .networkUnavailable
        case .tooManyRequests:
            return .tooManyRequests
        default:
            return .unknown
        }
    }
}
