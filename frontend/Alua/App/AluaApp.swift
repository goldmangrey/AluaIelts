import SwiftUI

@main
struct AluaApp: App {
    @State private var appState: AppState
    @State private var authSession: AuthSession
    private let dependencies: DependencyContainer

    @MainActor
    init() {
        let dependencies = DependencyContainer.live()
        self.dependencies = dependencies
        _appState = State(initialValue: AppState())
        _authSession = State(
            initialValue: AuthSession(
                authService: dependencies.authService,
                userService: dependencies.userService
            )
        )
    }

    var body: some Scene {
        WindowGroup {
            RootView(
                appState: appState,
                authSession: authSession,
                dependencies: dependencies
            )
            .task { authSession.start() }
        }
    }
}
