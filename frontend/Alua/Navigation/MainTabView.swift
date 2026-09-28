import SwiftUI

struct MainTabView: View {
    @Bindable var appState: AppState
    let authSession: AuthSession
    let dependencies: DependencyContainer

    var body: some View {
        TabView(selection: $appState.selectedTab) {
            NavigationStack {
                TodayView(
                    environment: dependencies.environment,
                    authSession: authSession
                )
            }
            .tabItem { Label(AppTab.today.title, systemImage: AppTab.today.systemImage) }
            .tag(AppTab.today)

            NavigationStack {
                LearnView()
            }
            .tabItem { Label(AppTab.learn.title, systemImage: AppTab.learn.systemImage) }
            .tag(AppTab.learn)

            NavigationStack {
                ProgressView()
            }
            .tabItem { Label(AppTab.progress.title, systemImage: AppTab.progress.systemImage) }
            .tag(AppTab.progress)

            NavigationStack {
                PartnerView()
            }
            .tabItem { Label(AppTab.partner.title, systemImage: AppTab.partner.systemImage) }
            .tag(AppTab.partner)
        }
        .tint(AluaColors.accent)
    }
}
