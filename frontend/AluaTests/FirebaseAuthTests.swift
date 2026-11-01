import XCTest
@testable import Alua

@MainActor
final class FirebaseAuthTests: XCTestCase {
    private func profile(_ id: String) -> UserProfile {
        UserProfile(uid: id, email: nil, displayName: id, role: .learner,
                    currentLevel: nil, targetIELTSBand: nil, dailyStudyMinutes: nil,
                    createdAt: .now, updatedAt: .now)
    }

    func testRestoreLoginLogoutAndExistingLearnerIdentity() async throws {
        let tokens = DeviceTokenStore(account: "firebase-test-\(UUID())")
        defer { try? tokens.clear() }
        let firebase = FirebaseStub()
        let users = FirebaseUserStub(profile("old-postgres-uuid-A"))
        let session = AuthSession(tokenStore: tokens, enrollmentService: UnusedEnrollment(),
                                  userService: users, widgetSyncService: FirebaseWidgets(), firebase: firebase)
        session.start()
        XCTAssertEqual(session.state, .needsProfileSelection)
        await session.signIn(email: " a@example.org ", password: "test-only-password")
        await waitUntil { session.profile != nil }
        XCTAssertEqual(session.profile?.uid, "old-postgres-uuid-A")
        XCTAssertNotEqual(session.profile?.uid, firebase.uid)
        XCTAssertEqual(firebase.lastEmail, "a@example.org")
        XCTAssertNil(try tokens.read()) // No ID token/password in our Keychain.
        let restored = AuthSession(tokenStore: tokens, enrollmentService: UnusedEnrollment(),
                                   userService: users, widgetSyncService: FirebaseWidgets(), firebase: firebase)
        restored.start()
        await waitUntil { restored.profile != nil }
        XCTAssertEqual(restored.profile?.uid, "old-postgres-uuid-A")
        try tokens.save("leftover-legacy-token")
        firebase.supportsLegacyRestore = true
        let readsBeforeLogout = users.readCount
        await restored.switchProfile()
        await settle()
        XCTAssertEqual(users.readCount, readsBeforeLogout)
        let loggedOut = AuthSession(tokenStore: tokens, enrollmentService: UnusedEnrollment(),
                                    userService: users, widgetSyncService: FirebaseWidgets(), firebase: firebase)
        loggedOut.start()
        await settle()
        XCTAssertEqual(loggedOut.state, .needsProfileSelection)
        XCTAssertNil(try tokens.read())
        XCTAssertNil(firebase.uid)
        XCTAssertNil(restored.profile)
        XCTAssertEqual(restored.state, .needsProfileSelection)
        users.value = profile("old-postgres-uuid-B")
        await loggedOut.signIn(email: "b@example.org", password: "test-only-password")
        await waitUntil { loggedOut.profile != nil }
        XCTAssertEqual(loggedOut.profile?.uid, "old-postgres-uuid-B")
        try await loggedOut.resetPassword(email: " b@example.org ")
        XCTAssertEqual(firebase.resetEmail, "b@example.org")
    }

    func testLoadingFailuresAndUnmappedIdentity() async throws {
        let tokens = DeviceTokenStore(account: "firebase-test-\(UUID())")
        defer { try? tokens.clear() }
        let firebase = FirebaseStub()
        let users = FirebaseUserStub(profile("old-id"))
        let session = AuthSession(tokenStore: tokens, enrollmentService: UnusedEnrollment(),
                                  userService: users, widgetSyncService: FirebaseWidgets(), firebase: firebase)
        session.start()
        firebase.failure = APIError.transport
        await session.signIn(email: "a@example.org", password: "bad")
        XCTAssertEqual(session.state, .needsProfileSelection)
        XCTAssertNotNil(session.selectionError)
        XCTAssertFalse(session.isSelectingProfile)
        firebase.failure = nil
        users.failure = APIError.server(statusCode: 403, backendCode: "identity_not_allowed", message: "internal detail")
        await session.signIn(email: "a@example.org", password: "test")
        await waitUntil { session.profile != nil }
        XCTAssertEqual(session.profile?.uid, "old-id")
        XCTAssertNotNil(firebase.uid)
        XCTAssertEqual(users.registerCount, 1)
    }

    func testLateProfileResponseCannotRestoreLoggedOutUser() async throws {
        let tokens = DeviceTokenStore(account: "firebase-test-\(UUID())")
        defer { try? tokens.clear() }
        let firebase = FirebaseStub()
        firebase.uid = "firebase-A"
        let users = FirebaseUserStub(profile("old-id"))
        users.delay = true
        let session = AuthSession(tokenStore: tokens, enrollmentService: UnusedEnrollment(),
                                  userService: users, widgetSyncService: FirebaseWidgets(), firebase: firebase)
        session.start()
        await waitUntil { users.pending != nil }
        XCTAssertEqual(session.state, .loadingProfile)
        await session.switchProfile()
        users.pending?.resume(returning: users.value)
        users.pending = nil
        await settle()
        XCTAssertEqual(session.state, .needsProfileSelection)
        XCTAssertNil(session.profile)
    }

    func testEmailValidation() {
        XCTAssertTrue(AuthView.validEmail("you@example.com"))
        for value in ["", "you", "a@", "a b@example.com", "a@b"] {
            XCTAssertFalse(AuthView.validEmail(value))
        }
    }

    func testSignupProvisioningOutageAndRestore() async throws {
        let tokens = DeviceTokenStore(account: "signup-test-\(UUID())")
        defer { try? tokens.clear() }
        let firebase = FirebaseStub()
        let users = FirebaseUserStub(profile("new-postgres-id"))
        users.failure = APIError.server(statusCode: 403, backendCode: "identity_not_allowed", message: "unmapped")
        users.registrationFailure = APIError.transport
        let session = AuthSession(tokenStore: tokens, enrollmentService: UnusedEnrollment(),
                                  userService: users, widgetSyncService: FirebaseWidgets(), firebase: firebase)
        session.start()
        await session.signUp(name: "New Name", email: "new@example.org", password: "new-test-password")
        await session.signUp(name: "Duplicate", email: "another@example.org", password: "new-test-password")
        await waitUntil { if case .profileLoadFailed = session.state { return true }; return false }
        XCTAssertNil(session.profile)
        XCTAssertNotNil(firebase.uid)
        if case .profileLoadFailed = session.state {} else { XCTFail("Must expose retry") }
        XCTAssertEqual(firebase.createCount, 1)
        XCTAssertEqual(users.lastRegistrationName, "New Name")
        // Cold session restore with Firebase account already created; no second createUser.
        users.registrationFailure = nil
        let restored = AuthSession(tokenStore: tokens, enrollmentService: UnusedEnrollment(),
                                   userService: users, widgetSyncService: FirebaseWidgets(), firebase: firebase)
        restored.start()
        await waitUntil { restored.profile != nil }
        XCTAssertEqual(restored.profile?.uid, "new-postgres-id")
        XCTAssertEqual(firebase.createCount, 1)
        await restored.switchProfile()
        await restored.signIn(email: "new@example.org", password: "new-test-password")
        await waitUntil { restored.profile != nil }
        XCTAssertEqual(restored.profile?.uid, "new-postgres-id")
        XCTAssertEqual(users.registerCount, 2) // Failure + successful retry only; login uses /me.
    }

    func testRegistrationValidation() {
        XCTAssertTrue(AuthView.validRegistration(name: "Name", email: "a@example.org", password: "password8", confirmation: "password8"))
        XCTAssertFalse(AuthView.validRegistration(name: " ", email: "a@example.org", password: "password8", confirmation: "password8"))
        XCTAssertFalse(AuthView.validRegistration(name: "Name", email: "a@example.org", password: "short", confirmation: "short"))
        XCTAssertFalse(AuthView.validRegistration(name: "Name", email: "a@example.org", password: "password8", confirmation: "different"))
    }

    private func waitUntil(_ condition: () -> Bool, file: StaticString = #filePath, line: UInt = #line) async {
        let deadline = ContinuousClock.now + .seconds(2)
        while !condition(), ContinuousClock.now < deadline {
            try? await Task.sleep(for: .milliseconds(1))
        }
        XCTAssertTrue(condition(), "Timed out waiting for auth state", file: file, line: line)
    }

    private func settle() async { for _ in 0..<100 { await Task.yield() } }
}

@MainActor
private final class FirebaseStub: FirebaseSessionProtocol {
    var uid: String?
    var supportsLegacyRestore = false
    var callback: (@MainActor () -> Void)?
    var lastEmail: String?
    var resetEmail: String?
    var failure: Error?
    var displayName: String?
    var createCount = 0
    func createUser(email: String, password: String, name: String) async throws {
        createCount += 1
        if let failure { throw failure }
        displayName = name; uid = "firebase-\(email)"; callback?()
    }
    func observe(_ change: @escaping @MainActor () -> Void) { callback = change; change() }
    func stopObserving() { callback = nil }
    func signIn(email: String, password: String) async throws {
        if let failure { throw failure }
        lastEmail = email; uid = "firebase-\(email)"; callback?()
    }
    func signOut() throws { uid = nil; callback?() }
    func resetPassword(email: String) async throws { resetEmail = email }
}

private final class FirebaseUserStub: UserServiceProtocol, @unchecked Sendable {
    var value: UserProfile
    var failure: Error?
    var registerCount = 0
    var registrationFailure: Error?
    var lastRegistrationName: String?
    func register(displayName: String?) async throws -> UserProfile {
        registerCount += 1
        lastRegistrationName = displayName
        if let registrationFailure { throw registrationFailure }
        failure = nil
        return value
    }
    var delay = false
    var readCount = 0
    var pending: CheckedContinuation<UserProfile, Never>?
    init(_ value: UserProfile) { self.value = value }
    func getCurrentUserProfile() async throws -> UserProfile {
        readCount += 1
        if delay { return await withCheckedContinuation { pending = $0 } }
        if let failure { throw failure }
        return value
    }
    func updateCurrentUserProfile(_ update: UserProfileUpdate) async throws -> UserProfile { value }
}
private struct UnusedEnrollment: EnrollmentServiceProtocol {
    func enroll(code: String, deviceName: String?) async throws -> DeviceEnrollmentResponse { throw APIError.transport }
    func revokeCurrentDevice() async throws { XCTFail("Firebase logout must not revoke legacy records") }
    func currentDeviceID() async throws -> String { throw APIError.transport }
}
@MainActor
private final class FirebaseWidgets: WidgetSyncServiceProtocol {
    func sync() async {}
    func clear() {}
}

final class AuthenticatedNetworkTests: XCTestCase {
    func testRefreshedBearerKeepsSessionAndAccountChangeDiscardsResponse() async throws {
        let tokens = RotatingTokens()
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [AuthTestURLProtocol.self]
        let client = APIClient(baseURL: URL(string: "https://unit.invalid")!,
                               session: URLSession(configuration: configuration), tokenProvider: tokens)
        let endpoint = APIEndpoint(path: "/api/v1/me", requiresAuthentication: true)
        AuthTestURLProtocol.respond = { request in
            XCTAssertTrue(request.value(forHTTPHeaderField: "Authorization")?.hasPrefix("Bearer refreshed-") == true)
            return (200, Data(#"{"value":"old-learner"}"#.utf8))
        }
        defer { AuthTestURLProtocol.respond = nil }
        let result = try await client.send(endpoint, responseType: AuthTestResponse.self)
        XCTAssertEqual(result.value, "old-learner")
        AuthTestURLProtocol.respond = { _ in
            await tokens.changeAccount()
            return (200, Data(#"{"value":"old-learner"}"#.utf8))
        }
        do {
            _ = try await client.send(endpoint, responseType: AuthTestResponse.self)
            XCTFail("Old account response was accepted")
        } catch is CancellationError {} catch { XCTFail("Unexpected error: \(error)") }
    }
}
private struct AuthTestResponse: Decodable, Sendable { let value: String }
private actor RotatingTokens: AccessTokenProvider {
    var identity = "session-A"
    func accessToken() async throws -> String? { "refreshed-\(UUID())" }
    func sessionIdentifier() async throws -> String? { identity }
    func changeAccount() { identity = "session-B" }
}
private final class AuthTestURLProtocol: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var respond: (@Sendable (URLRequest) async -> (Int, Data))?
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        guard let respond = Self.respond else { return }
        Task {
            let (status, data) = await respond(request)
            let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        }
    }
    override func stopLoading() {}
}

@MainActor
final class AuthInstallationTests: XCTestCase {
    private var defaults: UserDefaults!
    private var suite: String!
    private var root: URL!

    override func setUp() async throws {
        suite = "auth-installation-tests-\(UUID())"
        defaults = UserDefaults(suiteName: suite)!
        root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    }

    override func tearDown() async throws {
        defaults.removePersistentDomain(forName: suite)
        try FileManager.default.removeItem(at: root)
    }

    func testFreshInstallAndReinstallClearOnlyCredentialsBeforeMarkingInstallation() throws {
        let tokens = DeviceTokenStore(account: "installation-test-\(UUID())")
        defer { try? tokens.clear() }
        // No credentials on fresh install; surviving Keychain credentials on reinstall.
        for reinstall in [false, true] {
            defaults.removePersistentDomain(forName: suite)
            if reinstall { try tokens.save("surviving-legacy-token") }
            var restoredFirebaseUID: String? = reinstall ? "surviving-firebase-user" : nil
            let outbox = root.appendingPathComponent("unsynced-attempt.json")
            try Data("pending-reading-attempt".utf8).write(to: outbox)
            let installation = AuthInstallation(defaults: defaults, applicationSupport: root)
            XCTAssertFalse(defaults.bool(forKey: AuthInstallation.markerKey))
            try installation.prepare(signOut: {
                // Models the first SDK listener callback after restoring Keychain.
                XCTAssertFalse(self.defaults.bool(forKey: AuthInstallation.markerKey))
                restoredFirebaseUID = nil
            }, clearLegacy: { try tokens.clear() })
            XCTAssertNil(restoredFirebaseUID)
            XCTAssertNil(try tokens.read())
            XCTAssertTrue(defaults.bool(forKey: AuthInstallation.markerKey))
            XCTAssertEqual(try Data(contentsOf: outbox), Data("pending-reading-attempt".utf8))
        }
    }

    func testOrdinaryRelaunchAndUpdatePreserveSession() throws {
        let first = AuthInstallation(defaults: defaults, applicationSupport: root)
        try first.prepare(signOut: {}, clearLegacy: {})
        for _ in 0..<2 {
            let next = AuthInstallation(defaults: defaults, applicationSupport: root)
            try next.prepare(signOut: { XCTFail("Must preserve Firebase login") },
                             clearLegacy: { XCTFail("Must preserve existing legacy login") })
        }
    }

    func testUpgradeFromVersionWithoutMarkerUsesExistingContainer() throws {
        for directory in ["Reading-v1", "google-heartbeat-storage"] {
            defaults.removePersistentDomain(forName: suite)
            let evidence = root.appendingPathComponent(directory)
            try FileManager.default.createDirectory(at: evidence, withIntermediateDirectories: true)
            let next = AuthInstallation(defaults: defaults, applicationSupport: root)
            try next.prepare(signOut: { XCTFail("Upgrade must keep login") }, clearLegacy: { XCTFail() })
            XCTAssertTrue(defaults.bool(forKey: AuthInstallation.markerKey))
            try FileManager.default.removeItem(at: evidence)
        }
        defaults.removePersistentDomain(forName: suite)
        defaults.set(false, forKey: "vocabulary.reminders.enabled")
        try AuthInstallation(defaults: defaults, applicationSupport: root)
            .prepare(signOut: { XCTFail("Existing preference, even false, proves prior install") }, clearLegacy: { XCTFail() })
    }

    func testCleanupFailureAttemptsBothStoresAndRetriesAfterRestart() throws {
        let first = AuthInstallation(defaults: defaults, applicationSupport: root)
        var legacyCleared = false
        XCTAssertThrowsError(try first.prepare(signOut: { throw APIError.transport }, clearLegacy: { legacyCleared = true }))
        XCTAssertTrue(legacyCleared)
        XCTAssertFalse(defaults.bool(forKey: AuthInstallation.markerKey))
        // Firebase may have written migration evidence since the failed cleanup.
        defaults.set(false, forKey: "vocabulary.reminders.enabled")
        let restarted = AuthInstallation(defaults: defaults, applicationSupport: root)
        var signedOut = false
        XCTAssertThrowsError(try restarted.prepare(signOut: { signedOut = true }, clearLegacy: { throw APIError.transport }))
        XCTAssertTrue(signedOut)
        XCTAssertTrue(defaults.bool(forKey: AuthInstallation.pendingCleanupKey))
        try restarted.prepare(signOut: {}, clearLegacy: {})
        XCTAssertTrue(defaults.bool(forKey: AuthInstallation.markerKey))
        XCTAssertFalse(defaults.bool(forKey: AuthInstallation.pendingCleanupKey))
    }

    func testFailedLogoutMustNotRestoreOnNextLaunch() throws {
        defaults.set(true, forKey: AuthInstallation.markerKey)
        let installation = AuthInstallation(defaults: defaults, applicationSupport: root)
        installation.requireCleanup()
        XCTAssertThrowsError(try installation.prepare(signOut: { throw APIError.transport }, clearLegacy: {}))
        let restarted = AuthInstallation(defaults: defaults, applicationSupport: root)
        var signedOut = false
        var legacyCleared = false
        try restarted.prepare(signOut: { signedOut = true }, clearLegacy: { legacyCleared = true })
        XCTAssertTrue(signedOut)
        XCTAssertTrue(legacyCleared)
    }
}
