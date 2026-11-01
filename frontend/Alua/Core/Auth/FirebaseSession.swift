import FirebaseCore
import FirebaseAuth
import Foundation
import UIKit

@MainActor
protocol FirebaseSessionProtocol: AnyObject {
    var uid: String? { get }
    var supportsLegacyRestore: Bool { get }
    var displayName: String? { get }
    func createUser(email: String, password: String, name: String) async throws
    func observe(_ change: @escaping @MainActor () -> Void)
    func stopObserving()
    func signIn(email: String, password: String) async throws
    func signOut() throws
    func resetPassword(email: String) async throws
}

extension FirebaseSessionProtocol {
    var supportsLegacyRestore: Bool { false }
    var displayName: String? { nil }
    func createUser(email: String, password: String, name: String) async throws { throw APIError.transport }
}

/// Auth only. The returned Firebase UID is never used as an Alua learner/cache ID.
@MainActor
final class FirebaseSession: FirebaseSessionProtocol, AccessTokenProvider {
    private let auth: Auth
    private let legacy: DeviceTokenStore
    private var listener: AuthStateDidChangeListenerHandle?
    private var generation = UUID()
    private var observedUID: String?
    private let installation: AuthInstallation
    private var isPrepared = false
    private(set) var supportsLegacyRestore = false
    var onSessionChange: (() -> Void)?
    var uid: String? { isPrepared ? auth.currentUser?.uid : nil }
    var displayName: String? { auth.currentUser?.displayName }

    func createUser(email: String, password: String, name: String) async throws {
        try prepare()
        let result = try await auth.createUser(withEmail: email, password: password)
        supportsLegacyRestore = false
        try? legacy.clear()
        let update = result.user.createProfileChangeRequest()
        update.displayName = name
        // Account creation already succeeded. A metadata outage must not repeat createUser.
        try? await update.commitChanges()
    }

    init(legacy: DeviceTokenStore, defaults: UserDefaults = .standard) {
        // Capture migration evidence BEFORE Firebase can write files in this container.
        installation = AuthInstallation(defaults: defaults)
        if FirebaseApp.app() == nil { FirebaseApp.configure() }
        auth = Auth.auth()
        self.legacy = legacy
    }

    func observe(_ change: @escaping @MainActor () -> Void) {
        stopObserving()
        listener = auth.addStateDidChangeListener { [weak self] _, _ in
            Task { @MainActor [weak self] in
                guard let self else { return }
                // The first SDK callback runs after asynchronous Keychain restoration.
                // Never expose the restored user or a bearer token before cleanup succeeds.
                do { try prepare() }
                catch { change(); return }
                if observedUID != uid {
                    observedUID = uid
                    generation = UUID()
                    onSessionChange?()
                }
                change()
            }
        }
    }

    deinit {
        if let listener { auth.removeStateDidChangeListener(listener) }
    }

    func stopObserving() {
        if let listener { auth.removeStateDidChangeListener(listener) }
        listener = nil
    }

    private func prepare() throws {
        guard !isPrepared else { return }
        guard UIApplication.shared.isProtectedDataAvailable else { throw APIError.transport }
        try installation.prepare(signOut: { try auth.signOut() }, clearLegacy: { try legacy.clear() })
        if auth.currentUser != nil { try legacy.clear() }
        isPrepared = true
        supportsLegacyRestore = auth.currentUser == nil
    }

    func signIn(email: String, password: String) async throws {
        try prepare()
        _ = try await auth.signIn(withEmail: email, password: password)
        supportsLegacyRestore = false
        try? legacy.clear()
    }

    func signOut() throws {
        supportsLegacyRestore = false
        isPrepared = false
        generation = UUID()
        onSessionChange?()
        // Attempt both even if one Keychain operation fails; report failure for retry.
        installation.requireCleanup()
        guard UIApplication.shared.isProtectedDataAvailable else { throw APIError.transport }
        try installation.prepare(signOut: { try auth.signOut() }, clearLegacy: { try legacy.clear() })
        isPrepared = true
    }

    func resetPassword(email: String) async throws {
        do { try await auth.sendPasswordReset(withEmail: email) }
        catch {
            // Account existence must not be disclosed in the reset UI.
            if (error as NSError).code != AuthErrorCode.userNotFound.rawValue { throw error }
        }
    }

    func accessToken() async throws -> String? {
        guard isPrepared else { return nil }
        guard let user = auth.currentUser else { return supportsLegacyRestore ? try legacy.read() : nil }
        let current = generation
        let token = try await user.getIDToken() // SDK refreshes expired tokens automatically.
        guard generation == current, auth.currentUser?.uid == user.uid else { throw CancellationError() }
        return token
    }

    func sessionIdentifier() async throws -> String? {
        guard isPrepared else { return nil }
        if let uid { return "firebase:\(uid):\(generation)" }
        return supportsLegacyRestore ? try legacy.read() : nil
    }

    func authenticationRejected(session: String?) async {
        guard session == (try? await sessionIdentifier()) else { return }
        try? legacy.clear()
        try? signOut()
    }

    static func message(for error: Error) -> String {
        switch (error as NSError).code {
        case AuthErrorCode.emailAlreadyInUse.rawValue:
            return "Этот email уже зарегистрирован. Войдите или восстановите пароль."
        case AuthErrorCode.weakPassword.rawValue:
            return "Пароль слишком слабый. Используйте не менее 8 символов; проверьте требования к паролю."
        case AuthErrorCode.invalidEmail.rawValue:
            return "Проверьте адрес электронной почты."
        case AuthErrorCode.networkError.rawValue:
            return "Не удалось подключиться. Проверьте интернет и попробуйте снова."
        case AuthErrorCode.tooManyRequests.rawValue:
            return "Слишком много попыток. Попробуйте немного позже."
        case AuthErrorCode.userDisabled.rawValue:
            return "Доступ к аккаунту отключён. Свяжитесь с владельцем Alua."
        default:
            return "Не удалось войти. Проверьте электронную почту и пароль."
        }
    }
}

/// A container-local marker, never a credential. Uninstall removes UserDefaults but not Keychain.
/// Cleanup stays pending across failures/restarts so a locked Keychain cannot bless an old session.
@MainActor
final class AuthInstallation {
    static let markerKey = "auth.installation.v1"
    static let pendingCleanupKey = "auth.installation.cleanupPending"
    private let defaults: UserDefaults
    private var needsCleanup: Bool

    init(defaults: UserDefaults, applicationSupport: URL = .applicationSupportDirectory) {
        self.defaults = defaults
        let marked = defaults.bool(forKey: Self.markerKey)
        // One-time migration from versions without a marker. Only container-local evidence
        // counts: Keychain credentials alone cannot distinguish an upgrade from reinstall.
        let existingContainer = defaults.object(forKey: "vocabulary.reminders.enabled") != nil
            || FileManager.default.fileExists(atPath: applicationSupport.appendingPathComponent("Reading-v1").path)
            || FileManager.default.fileExists(atPath: applicationSupport.appendingPathComponent("google-heartbeat-storage").path)
        needsCleanup = defaults.bool(forKey: Self.pendingCleanupKey) || (!marked && !existingContainer)
        if needsCleanup { defaults.set(true, forKey: Self.pendingCleanupKey) }
    }

    func requireCleanup() {
        needsCleanup = true
        defaults.set(true, forKey: Self.pendingCleanupKey)
    }

    func prepare(signOut: () throws -> Void, clearLegacy: () throws -> Void) throws {
        if needsCleanup {
            var failure: Error?
            do { try signOut() } catch { failure = error }
            do { try clearLegacy() } catch { failure = failure ?? error }
            if let failure { throw failure }
            needsCleanup = false
            defaults.removeObject(forKey: Self.pendingCleanupKey)
        }
        defaults.set(true, forKey: Self.markerKey)
    }
}
