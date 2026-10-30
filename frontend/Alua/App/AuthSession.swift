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

    @ObservationIgnored private let tokenStore: DeviceTokenStore
    @ObservationIgnored private let enrollmentService: any EnrollmentServiceProtocol
    @ObservationIgnored private let userService: any UserServiceProtocol
    @ObservationIgnored private let widgetSyncService: any WidgetSyncServiceProtocol
    @ObservationIgnored private var hasStarted = false

    init(
        tokenStore: DeviceTokenStore,
        enrollmentService: any EnrollmentServiceProtocol,
        userService: any UserServiceProtocol,
        widgetSyncService: any WidgetSyncServiceProtocol
    ) {
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
            guard try tokenStore.read() != nil else {
                state = .needsProfileSelection
                return
            }
            await loadProfile()
        } catch {
            state = .profileLoadFailed(readableMessage(for: error))
        }
    }

    func updateProfile(_ update: UserProfileUpdate) async throws {
        let profile = try await userService.updateCurrentUserProfile(update)
        state = .authenticated(profile)
    }

    func switchProfile() async {
        guard !isSwitchingProfile else { return }
        isSwitchingProfile = true
        defer { isSwitchingProfile = false }
        selectionError = nil
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
        state = .loadingProfile
        do {
            state = .authenticated(try await userService.getCurrentUserProfile())
        } catch APIError.unauthorized(let message) {
            widgetSyncService.clear()
            try? tokenStore.clear()
            selectionError = message
            state = .needsProfileSelection
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
