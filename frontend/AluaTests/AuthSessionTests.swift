import XCTest
@testable import Alua

@MainActor
final class AuthSessionTests: XCTestCase {
    private func profile(_ uid: String) -> UserProfile {
        UserProfile(uid: uid, email: nil, displayName: uid, role: .learner,
                    currentLevel: nil, targetIELTSBand: nil, dailyStudyMinutes: nil,
                    createdAt: .now, updatedAt: .now)
    }

    func testSelectionRestorationAndSwitch() async throws {
        let store = DeviceTokenStore(account: "test-\(UUID())")
        defer { try? store.clear() }
        let user = UserStub(value: profile("husband"))
        let enrollment = BootstrapStub(value: user.value)
        let widgets = WidgetStub()
        let session = AuthSession(tokenStore: store, enrollmentService: enrollment,
                                  userService: user, widgetSyncService: widgets)
        session.start()
        XCTAssertEqual(session.state, .needsProfileSelection)
        await session.enroll(code: "TEST-CODE")
        XCTAssertEqual(session.profile?.uid, "husband")
        XCTAssertEqual(try store.read(), "test-device-token")
        XCTAssertEqual(widgets.syncCount, 1)
        await session.enroll(code: "SECOND-CODE") // A queued second tap cannot replace the selected profile.
        XCTAssertEqual(enrollment.codes.count, 1)

        let restored = AuthSession(tokenStore: store, enrollmentService: enrollment,
                                   userService: user, widgetSyncService: widgets)
        restored.start()
        for _ in 0..<100 {
            if restored.profile != nil { break }
            await Task.yield()
        }
        XCTAssertEqual(restored.profile?.uid, "husband")
        XCTAssertEqual(enrollment.codes.count, 1) // No new bootstrap on relaunch.
        await restored.switchProfile()
        XCTAssertNil(try store.read())
        XCTAssertEqual(restored.state, .needsProfileSelection)
        XCTAssertEqual(enrollment.revokeCount, 1)
        XCTAssertGreaterThanOrEqual(widgets.clearCount, 2)
    }

    func testFailedEnrollmentRequiresCodeAndDoesNotAuthenticate() async throws {
        let store = DeviceTokenStore(account: "test-\(UUID())")
        defer { try? store.clear() }
        let user = UserStub(value: profile("wife"))
        let enrollment = BootstrapStub(value: user.value)
        enrollment.failNext = true
        let session = AuthSession(tokenStore: store, enrollmentService: enrollment,
                                  userService: user, widgetSyncService: WidgetStub())
        session.start()
        await session.enroll(code: "TEST-CODE")
        XCTAssertEqual(session.state, .needsProfileSelection)
        XCTAssertNil(try store.read())
        XCTAssertNotNil(session.selectionError)
        await session.enroll(code: "NEW-CODE")
        XCTAssertEqual(session.profile?.uid, "wife")
        let deviceID = try await session.currentDeviceID()
        XCTAssertEqual(deviceID, "test-device")
    }

}

private final class BootstrapStub: EnrollmentServiceProtocol, @unchecked Sendable {
    let value: UserProfile
    var codes: [String] = []
    var revokeCount = 0
    var failNext = false
    init(value: UserProfile) { self.value = value }
    func enroll(code: String, deviceName: String?) async throws -> DeviceEnrollmentResponse {
        codes.append(code)
        if failNext { failNext = false; throw APIError.transport }
        return DeviceEnrollmentResponse(token: "test-device-token", enrollmentID: "test-device", profile: value)
    }
    func revokeCurrentDevice() async throws { revokeCount += 1 }
    func currentDeviceID() async throws -> String { "test-device" }
}

private struct UserStub: UserServiceProtocol {
    let value: UserProfile
    func getCurrentUserProfile() async throws -> UserProfile { value }
    func updateCurrentUserProfile(_ update: UserProfileUpdate) async throws -> UserProfile { value }
}

@MainActor
private final class WidgetStub: WidgetSyncServiceProtocol {
    var syncCount = 0
    var clearCount = 0
    func sync() async { syncCount += 1 }
    func clear() { clearCount += 1 }
}
