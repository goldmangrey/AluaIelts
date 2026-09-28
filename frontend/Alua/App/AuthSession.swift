import Foundation
import Observation

@MainActor
@Observable
final class AuthSession {
    enum State: Equatable {
        case unknown
        case signedOut
        case loadingProfile
        case authenticated(UserProfile)
        case profileLoadFailed(String)
    }

    private(set) var state: State = .unknown
    private(set) var isAuthenticating = false
    var authenticationError: String?

    @ObservationIgnored private let authService: any AuthServiceProtocol
    @ObservationIgnored private let userService: any UserServiceProtocol
    @ObservationIgnored private var authHandle: AnyObject?
    @ObservationIgnored private var pendingDisplayName: String?
    @ObservationIgnored private var hasStarted = false

    init(
        authService: any AuthServiceProtocol,
        userService: any UserServiceProtocol
    ) {
        self.authService = authService
        self.userService = userService
    }

    var profile: UserProfile? {
        guard case let .authenticated(profile) = state else { return nil }
        return profile
    }

    func start() {
        guard !hasStarted else { return }
        hasStarted = true
        guard authService.isConfigured else {
            authenticationError = AuthServiceError.notConfigured.localizedDescription
            state = .signedOut
            return
        }
        authHandle = authService.observeAuthState { [weak self] identity in
            guard let self else { return }
            Task { await self.handleAuthChange(identity) }
        }
    }

    func signIn(email: String, password: String) async {
        await authenticate {
            try await authService.signIn(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                password: password
            )
        }
    }

    func signUp(displayName: String, email: String, password: String) async {
        pendingDisplayName = displayName.trimmingCharacters(in: .whitespacesAndNewlines)
        await authenticate {
            try await authService.signUp(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                password: password
            )
        }
    }

    func retryProfileLoad() async {
        guard authService.currentUser != nil else {
            state = .signedOut
            return
        }
        await loadProfile()
    }

    func updateProfile(_ update: UserProfileUpdate) async throws {
        let profile = try await userService.updateCurrentUserProfile(update)
        state = .authenticated(profile)
    }

    func signOut() {
        do {
            try authService.signOut()
            pendingDisplayName = nil
            authenticationError = nil
            state = .signedOut
        } catch {
            authenticationError = readableMessage(for: error)
        }
    }

    private func authenticate(_ operation: () async throws -> Void) async {
        isAuthenticating = true
        authenticationError = nil
        do {
            try await operation()
        } catch {
            authenticationError = readableMessage(for: error)
            pendingDisplayName = nil
        }
        isAuthenticating = false
    }

    private func handleAuthChange(_ identity: FirebaseIdentity?) async {
        guard identity != nil else {
            state = .signedOut
            return
        }
        await loadProfile()
    }

    private func loadProfile() async {
        state = .loadingProfile
        do {
            var profile = try await userService.getCurrentUserProfile()
            if let displayName = pendingDisplayName, !displayName.isEmpty {
                profile = try await userService.updateCurrentUserProfile(
                    UserProfileUpdate(
                        displayName: displayName,
                        currentLevel: profile.currentLevel,
                        targetIELTSBand: profile.targetIELTSBand,
                        dailyStudyMinutes: profile.dailyStudyMinutes
                    )
                )
                pendingDisplayName = nil
            }
            state = .authenticated(profile)
        } catch {
            state = .profileLoadFailed(readableMessage(for: error))
        }
    }

    private func readableMessage(for error: Error) -> String {
        if let localizedError = error as? LocalizedError,
           let message = localizedError.errorDescription
        {
            return message
        }
        return "Something went wrong. Please try again."
    }
}
