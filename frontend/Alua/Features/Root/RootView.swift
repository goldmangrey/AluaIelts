import SwiftUI

struct RootView: View {
    let appState: AppState
    let authSession: AuthSession
    let curriculumStore: CurriculumStore
    let vocabularyStore: VocabularyStore
    let grammarStore: GrammarStore
    let studentModelStore: StudentModelStore
    let dailyPlanStore: DailyPlanStore
    let progressStore: ProgressStore
    let partnerStore: PartnerStore
    let aiProgressStore: AIProgressStore
    let deepLinkRouter: DeepLinkRouter
    let vocabularyLearningStore: VocabularyLearningStore
    let dependencies: DependencyContainer
    @State private var readingStore: ReadingStore?

    var body: some View {
        Group {
            switch authSession.state {
            case .unknown, .loadingProfile:
                launchView
            case .needsProfileSelection:
                AuthView(authSession: authSession)
            case .authenticated:
                MainTabView(
                    appState: appState,
                    authSession: authSession,
                    curriculumStore: curriculumStore,
                    vocabularyStore: vocabularyStore,
                    grammarStore: grammarStore,
                    studentModelStore: studentModelStore,
                    dailyPlanStore: dailyPlanStore,
                    progressStore: progressStore,
                    partnerStore: partnerStore,
                    aiProgressStore: aiProgressStore,
                    deepLinkRouter: deepLinkRouter,
                    vocabularyLearningStore: vocabularyLearningStore,
                    dependencies: dependencies,
                    readingStore: readingStore
                )
            case let .profileLoadFailed(message):
                profileErrorView(message: message)
            }
        }
        .task(id: authSession.profile?.uid) {
            guard let uid = authSession.profile?.uid else { return }
            if readingStore?.uid != uid {
                readingStore?.deactivate()
                readingStore = ReadingStore(api: dependencies.readingAPI, uid: uid)
            }
        }
        .onChange(of: authSession.state) { _, state in
            if state == .needsProfileSelection {
                readingStore?.deactivate()
                readingStore = nil
                try? ReadingFiles.clearSynchronizedCaches()
                appState.selectedTab = .today
                _ = deepLinkRouter.consume()
                dependencies.vocabularyNotificationService.disable()
                curriculumStore.clear()
                vocabularyStore.clear()
                grammarStore.clear()
                studentModelStore.clear()
                dailyPlanStore.clear()
                progressStore.clear()
                partnerStore.clear()
                aiProgressStore.clear()
                dependencies.widgetSyncService.clear()
                vocabularyLearningStore.clear()
            }
        }
    }

    private var launchView: some View {
        VStack(spacing: AluaSpacing.md) {
            SwiftUI.ProgressView()
            Text("Открываем ваш учебник…")
                .font(AluaTypography.subheadline)
                .foregroundStyle(AluaColors.secondaryText)
        }
    }

    private func profileErrorView(message: String) -> some View {
        ContentUnavailableView {
            Label("Не удалось открыть профиль", systemImage: "person.crop.circle.badge.exclamationmark")
        } description: {
            Text(message)
        } actions: {
            Button("Попробовать снова") {
                Task { await authSession.retryProfileLoad() }
            }
            .buttonStyle(.borderedProminent)
            Button("Выйти") { Task { await authSession.switchProfile() } }
        }
    }
}
