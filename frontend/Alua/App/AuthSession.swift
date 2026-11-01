import Foundation
import Observation
import UIKit

@MainActor
@Observable
final class AuthSession {
    enum State: Equatable {
        case unknown
        case needsProfileSelection
        case loadingProfile
        case authenticated(UserProfile)
        case profileLoadFailed(String)
    }

    private(set) var state: State = .unknown
    private(set) var isSelectingProfile = false
    private var isSwitchingProfile = false
    var selectionError: String?
    private var isCreatingFirebaseAccount = false
    private var pendingRegistrationName: String?

    @ObservationIgnored private let tokenStore: DeviceTokenStore
    @ObservationIgnored private let enrollmentService: any EnrollmentServiceProtocol
    @ObservationIgnored private let userService: any UserServiceProtocol
    @ObservationIgnored private let widgetSyncService: any WidgetSyncServiceProtocol
    @ObservationIgnored private let firebase: (any FirebaseSessionProtocol)?
    @ObservationIgnored private var profileTask: Task<Void, Never>?
    @ObservationIgnored private var generation = UUID()
    @ObservationIgnored private var lastFirebaseUID: String?
    @ObservationIgnored private var hasStarted = false

    init(
        tokenStore: DeviceTokenStore,
        enrollmentService: any EnrollmentServiceProtocol,
        userService: any UserServiceProtocol,
        widgetSyncService: any WidgetSyncServiceProtocol,
        firebase: (any FirebaseSessionProtocol)? = nil
    ) {
        self.firebase = firebase
        self.tokenStore = tokenStore
        self.enrollmentService = enrollmentService
        self.userService = userService
        self.widgetSyncService = widgetSyncService
    }

    var profile: UserProfile? {
        guard case let .authenticated(profile) = state else { return nil }
        return profile
    }

    func start() {
        guard !hasStarted else { return }
        hasStarted = true
        if let firebase {
            firebase.observe { [weak self] in self?.firebaseChanged() }
            return
        }
        do {
            if try tokenStore.read() == nil {
                state = .needsProfileSelection
            } else {
                Task { await loadProfile() }
            }
        } catch {
            state = .profileLoadFailed(readableMessage(for: error))
        }
    }

    private func firebaseChanged() {
        guard !isCreatingFirebaseAccount, !isSwitchingProfile else { return }
        let uid = firebase?.uid
        if uid == lastFirebaseUID, profile != nil { return }
        lastFirebaseUID = uid
        generation = UUID()
        profileTask?.cancel()
        state = .needsProfileSelection
        widgetSyncService.clear()
        if uid != nil || (firebase?.supportsLegacyRestore == true && (try? tokenStore.read()) != nil) {
            profileTask = Task { await loadProfile() }
        }
    }

    func signIn(email: String, password: String) async {
        guard let firebase, state == .needsProfileSelection, !isSelectingProfile else { return }
        isSelectingProfile = true
        selectionError = nil
        defer { isSelectingProfile = false }
        do {
            try await firebase.signIn(email: email.trimmingCharacters(in: .whitespacesAndNewlines), password: password)
        } catch { selectionError = FirebaseSession.message(for: error) }
    }

    func signUp(name: String, email: String, password: String) async {
        guard let firebase, firebase.uid == nil, state == .needsProfileSelection,
              !isSelectingProfile else { return }
        isSelectingProfile = true
        isCreatingFirebaseAccount = true
        selectionError = nil
        pendingRegistrationName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        defer {
            isSelectingProfile = false
            isCreatingFirebaseAccount = false
            if firebase.uid != nil { firebaseChanged() }
        }
        do {
            try await firebase.createUser(email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                                          password: password, name: pendingRegistrationName ?? name)
        } catch {
            selectionError = FirebaseSession.message(for: error)
            if firebase.uid == nil { pendingRegistrationName = nil }
        }
    }

    func resetPassword(email: String) async throws {
        guard let firebase else { throw APIError.transport }
        try await firebase.resetPassword(email: email.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    func enroll(code: String) async {
        guard state == .needsProfileSelection, !isSelectingProfile else { return }
        isSelectingProfile = true
        selectionError = nil
        defer { isSelectingProfile = false }
        do {
            let enrollment = try await enrollmentService.enroll(
                code: code.trimmingCharacters(in: .whitespacesAndNewlines), deviceName: UIDevice.current.name
            )
            try tokenStore.save(enrollment.token)
            widgetSyncService.clear()
            state = .authenticated(enrollment.profile)
            await widgetSyncService.sync()
        } catch {
            selectionError = readableMessage(for: error) + " Если код уже использован, попросите владельца выпустить новый."
        }
    }

    func currentDeviceID() async throws -> String {
        try await enrollmentService.currentDeviceID()
    }

    func retryProfileLoad() async {
        do {
            let hasLegacyToken = try (firebase == nil || firebase?.supportsLegacyRestore == true) && (tokenStore.read() != nil)
            guard firebase?.uid != nil || hasLegacyToken else {
                state = .needsProfileSelection
                return
            }
            await loadProfile()
        } catch {
            state = .profileLoadFailed(readableMessage(for: error))
        }
    }

    func updateProfile(_ update: UserProfileUpdate) async throws {
        let current = generation
        let profile = try await userService.updateCurrentUserProfile(update)
        guard current == generation else { throw CancellationError() }
        state = .authenticated(profile)
    }

    func switchProfile() async {
        guard !isSwitchingProfile else { return }
        isSwitchingProfile = true
        defer { isSwitchingProfile = false }
        selectionError = nil
        pendingRegistrationName = nil
        generation = UUID()
        profileTask?.cancel()
        if let firebase {
            do {
                try firebase.signOut()
                // Also clear injected/legacy stores; never revoke server records or delete outbox.
                try tokenStore.clear()
                lastFirebaseUID = nil
                widgetSyncService.clear()
                state = .needsProfileSelection
            } catch { selectionError = "Не удалось выйти. Попробуйте ещё раз." }
            return
        }
        do {
            do { try await enrollmentService.revokeCurrentDevice() }
            catch APIError.unauthorized { /* Already revoked remotely. */ }
            widgetSyncService.clear()
            try tokenStore.clear()
            state = .needsProfileSelection
        } catch {
            selectionError = readableMessage(for: error)
        }
    }

    private func loadProfile() async {
        let current = generation
        state = .loadingProfile
        var completingRegistration = false
        do {
            let value: UserProfile
            do {
                value = try await userService.getCurrentUserProfile()
            } catch APIError.server(let status, let code, _) where
                        status == 403 && code == "identity_not_allowed" && firebase?.uid != nil {
                guard current == generation, !Task.isCancelled else { return }
                // Also completes a signup whose Firebase step succeeded before an outage/restart.
                completingRegistration = true
                value = try await userService.register(displayName: pendingRegistrationName ?? firebase?.displayName)
            }
            guard current == generation, !Task.isCancelled else { return }
            pendingRegistrationName = nil
            state = .authenticated(value)
        } catch APIError.unauthorized {
            guard current == generation else { return }
            try? firebase?.signOut()
            widgetSyncService.clear()
            try? tokenStore.clear()
            selectionError = "Сессия завершилась. Войдите снова."
            state = .needsProfileSelection
        } catch {
            guard current == generation, !Task.isCancelled else { return }
            // Keep the Firebase session and pending name; retry/login repeats only provisioning.
            state = .profileLoadFailed(completingRegistration
                ? "Аккаунт создан, но пока не удалось подготовить ваш профиль. Проверьте соединение и попробуйте снова."
                : "Не удалось загрузить профиль. Проверьте соединение и попробуйте снова.")
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
