import Observation

@MainActor
@Observable
final class AppState {
    var selectedTab: AppTab = .today
}
