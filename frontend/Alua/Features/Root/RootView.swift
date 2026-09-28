import SwiftUI

struct RootView: View {
    let appState: AppState
    let authSession: AuthSession
    let dependencies: DependencyContainer

    var body: some View {
        Group {
            switch authSession.state {
            case .unknown, .loadingProfile:
                launchView
            case .signedOut:
                AuthView(authSession: authSession)
            case .authenticated:
                MainTabView(
                    appState: appState,
                    authSession: authSession,
                    dependencies: dependencies
                )
            case let .profileLoadFailed(message):
                profileErrorView(message: message)
            }
        }
    }

    private var launchView: some View {
        VStack(spacing: AluaSpacing.md) {
            SwiftUI.ProgressView()
            Text("Loading your profile…")
                .font(AluaTypography.subheadline)
                .foregroundStyle(AluaColors.secondaryText)
        }
    }

    private func profileErrorView(message: String) -> some View {
        ContentUnavailableView {
            Label("Unable to load profile", systemImage: "person.crop.circle.badge.exclamationmark")
        } description: {
            Text(message)
        } actions: {
            Button("Retry") {
                Task { await authSession.retryProfileLoad() }
            }
            .buttonStyle(.borderedProminent)
            Button("Sign Out") { authSession.signOut() }
        }
    }
}
