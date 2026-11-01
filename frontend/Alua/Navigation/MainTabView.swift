import SwiftUI

struct MainTabView: View {
    @Bindable var appState: AppState
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
    @State private var studyStore: StudyStore?
    let readingStore: ReadingStore?
    @Environment(\.scenePhase) private var scenePhase
    @State private var focusedLink: DeepLink?

    var body: some View {
        TabView(selection: $appState.selectedTab) {
            NavigationStack {
                today.toolbar { settingsButton }
            }.tabItem { Label(AppTab.today.title, systemImage: AppTab.today.systemImage) }.tag(AppTab.today)
            NavigationStack {
                Group {
                    if let studyStore { StudyBook(store: studyStore) }
                    else { StudyLoading(store: nil) }
                }.toolbar { settingsButton }
            }.tabItem { Label(AppTab.book.title, systemImage: AppTab.book.systemImage) }.tag(AppTab.book)
            NavigationStack {
                PracticeView(readingStore: readingStore).toolbar { settingsButton }
            }.tabItem { Label(AppTab.practice.title, systemImage: AppTab.practice.systemImage) }.tag(AppTab.practice)
        }
        .tint(AluaColors.accent).preferredColorScheme(.light)
        .task(id: authSession.profile?.uid) {
            guard let uid = authSession.profile?.uid else { studyStore = nil; return }
            if studyStore?.uid != uid {
                dependencies.widgetSyncService.activateLearner(uid)
                studyStore = StudyStore(api: dependencies.apiClient, uid: uid, widgetSyncService: dependencies.widgetSyncService)
            }
            await studyStore?.sync()
            handlePendingDeepLink()
            await dependencies.widgetSyncService.sync()
            await curriculumStore.load()
            await studentModelStore.load()
            handlePendingDeepLink()
            while !Task.isCancelled {
                do { try await Task.sleep(for: .seconds(15)) } catch { return }
                if scenePhase == .active { await studyStore?.sync() }
            }
        }
        .onChange(of: scenePhase) { _, phase in if phase == .active { Task { await studyStore?.sync() } } }
        .onChange(of: deepLinkRouter.pending) { _, _ in handlePendingDeepLink() }
        .fullScreenCover(item: $focusedLink) { link in
            NavigationStack {
                destination(link).toolbar { ToolbarItem(placement: .topBarLeading) { AluaCloseButton { focusedLink = nil } } }
            }
        }
    }
    private var today: some View {
        TodayView(studyStore: studyStore, environment: dependencies.environment, authSession: authSession, curriculumStore: curriculumStore, vocabularyStore: vocabularyStore, grammarStore: grammarStore, studentModelStore: studentModelStore, dailyPlanStore: dailyPlanStore, vocabularyService: dependencies.vocabularyService, learningEventService: dependencies.learningEventService, exerciseService: dependencies.exerciseService, onOpenVocabulary: { appState.selectedTab = .book })
    }
    @ToolbarContentBuilder private var settingsButton: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            NavigationLink {
                SettingsView(environment: dependencies.environment, authSession: authSession, studyStore: studyStore, partnerStore: partnerStore, aiStore: aiProgressStore)
            } label: { Image(systemName: "gearshape").frame(width: 44, height: 44) }.accessibilityLabel("Настройки")
        }
    }
    private func handlePendingDeepLink() {
        guard authSession.profile != nil, studyStore != nil, let link = deepLinkRouter.consume() else { return }
        switch link {
        case .today: appState.selectedTab = .today
        case .partner, .practice, .vocabulary, .grammar, .review, .studyReview, .quickRecall: focusedLink = link
        }
    }
    @ViewBuilder private func destination(_ link: DeepLink) -> some View {
        switch link {
        case .today: today
        case .studyReview:
            if let studyStore { StudyReviews(store: studyStore, showsCloseButton: false) }
        case let .quickRecall(item, learner, generation, expiry):
            if let studyStore {
                WidgetQuickRecallView(store: studyStore, itemID: item, learnerID: learner, generationID: generation, expiresAt: expiry)
            }
        case let .vocabulary(id): VocabularyPlanDestination(itemID: id, curriculumNodeID: nil, vocabularyService: dependencies.vocabularyService, learningEventService: dependencies.learningEventService)
        case let .grammar(id): GrammarLessonView(lessonID: id, store: grammarStore, learningEventService: dependencies.learningEventService)
        case let .practice(date, itemID): DeepLinkedPracticeView(planDate: date, itemID: itemID, curriculumStore: curriculumStore, vocabularyStore: vocabularyStore, grammarStore: grammarStore, dailyPlanStore: dailyPlanStore, studentModelStore: studentModelStore, dependencies: dependencies)
        case let .review(sessionID): VocabularyReviewSessionView(sessionID: sessionID, store: vocabularyLearningStore)
        case .partner: PartnerView(store: partnerStore, aiStore: aiProgressStore)
        }
    }
}

private struct DeepLinkedPracticeView: View {
    let planDate: String; let itemID: String
    let curriculumStore: CurriculumStore; let vocabularyStore: VocabularyStore; let grammarStore: GrammarStore
    let dailyPlanStore: DailyPlanStore; let studentModelStore: StudentModelStore; let dependencies: DependencyContainer
    var body: some View {
        Group {
            if let item = dailyPlanStore.plan?.items.first(where: { $0.itemID == itemID }), dailyPlanStore.plan?.localDate == planDate {
                DailyPlanActivityView(planDate: planDate, item: item, curriculumStore: curriculumStore, vocabularyStore: vocabularyStore, grammarStore: grammarStore, dailyPlanStore: dailyPlanStore, studentModelStore: studentModelStore, vocabularyService: dependencies.vocabularyService, learningEventService: dependencies.learningEventService, exerciseService: dependencies.exerciseService)
            } else if dailyPlanStore.isLoading { SwiftUI.ProgressView("Loading activity…") }
            else if let message = dailyPlanStore.errorMessage {
                ContentUnavailableView(
                    "Activity unavailable offline",
                    systemImage: "wifi.slash",
                    description: Text("Connect to the internet and try again. \(message)")
                )
            } else { ContentUnavailableView("Activity unavailable", systemImage: "book.closed") }
        }.task { await dailyPlanStore.ensureToday() }
    }
}
