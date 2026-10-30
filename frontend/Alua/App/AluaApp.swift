import SwiftUI

@main
struct AluaApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @State private var appState: AppState
    @State private var authSession: AuthSession
    @State private var curriculumStore: CurriculumStore
    @State private var vocabularyStore: VocabularyStore
    @State private var grammarStore: GrammarStore
    @State private var studentModelStore: StudentModelStore
    @State private var dailyPlanStore: DailyPlanStore
    @State private var progressStore: ProgressStore
    @State private var partnerStore: PartnerStore
    @State private var aiProgressStore: AIProgressStore
    @State private var deepLinkRouter: DeepLinkRouter
    @State private var vocabularyLearningStore: VocabularyLearningStore
    private let dependencies: DependencyContainer

    @MainActor
    init() {
        let dependencies = DependencyContainer.live()
        self.dependencies = dependencies
        _appState = State(initialValue: AppState())
        _authSession = State(
            initialValue: AuthSession(
                tokenStore: dependencies.tokenStore,
                enrollmentService: dependencies.enrollmentService,
                userService: dependencies.userService,
                widgetSyncService: dependencies.widgetSyncService
            )
        )
        _curriculumStore = State(
            initialValue: CurriculumStore(service: dependencies.curriculumService)
        )
        _vocabularyStore = State(
            initialValue: VocabularyStore(service: dependencies.vocabularyService)
        )
        _grammarStore = State(
            initialValue: GrammarStore(service: dependencies.grammarService)
        )
        _studentModelStore = State(
            initialValue: StudentModelStore(service: dependencies.masteryService)
        )
        _dailyPlanStore = State(
            initialValue: DailyPlanStore(service: dependencies.dailyPlanService, widgetSyncService: dependencies.widgetSyncService)
        )
        _progressStore = State(
            initialValue: ProgressStore(service: dependencies.progressService)
        )
        _partnerStore = State(
            initialValue: PartnerStore(service: dependencies.partnerService, widgetSyncService: dependencies.widgetSyncService)
        )
        _aiProgressStore = State(
            initialValue: AIProgressStore(service: dependencies.aiProgressService)
        )
        let deepLinkRouter = DeepLinkRouter()
        _deepLinkRouter = State(initialValue: deepLinkRouter)
        _vocabularyLearningStore = State(initialValue: VocabularyLearningStore(service: dependencies.vocabularyLearningService, notifications: dependencies.vocabularyNotificationService))
        dependencies.vocabularyNotificationService.configureRouteHandler { url in deepLinkRouter.receive(url) }
    }

    var body: some Scene {
        WindowGroup {
            RootView(
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
                dependencies: dependencies
            )
            .task { authSession.start() }
            .onChange(of: authSession.state) { _, state in
                if state == .needsProfileSelection { resetLearnerStores() }
            }
            .onOpenURL { deepLinkRouter.receive($0) }
            .onChange(of: scenePhase) { _, phase in
                if phase == .active, authSession.profile != nil {
                    Task { await dependencies.widgetSyncService.sync() }
                }
            }
        }
    }
    @MainActor
    private func resetLearnerStores() {
        // New instances prevent old asynchronous loads from repopulating the next profile's UI.
        vocabularyLearningStore.clear()
        dependencies.widgetSyncService.clear()
        dependencies.vocabularyNotificationService.disable()
        appState.selectedTab = .today
        _ = deepLinkRouter.consume()
        curriculumStore = CurriculumStore(service: dependencies.curriculumService)
        vocabularyStore = VocabularyStore(service: dependencies.vocabularyService)
        grammarStore = GrammarStore(service: dependencies.grammarService)
        studentModelStore = StudentModelStore(service: dependencies.masteryService)
        dailyPlanStore = DailyPlanStore(service: dependencies.dailyPlanService, widgetSyncService: dependencies.widgetSyncService)
        progressStore = ProgressStore(service: dependencies.progressService)
        partnerStore = PartnerStore(service: dependencies.partnerService, widgetSyncService: dependencies.widgetSyncService)
        aiProgressStore = AIProgressStore(service: dependencies.aiProgressService)
        vocabularyLearningStore = VocabularyLearningStore(service: dependencies.vocabularyLearningService, notifications: dependencies.vocabularyNotificationService)
    }

}
