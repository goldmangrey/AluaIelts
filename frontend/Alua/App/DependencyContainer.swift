import Foundation

struct DependencyContainer {
    let environment: AppEnvironment
    let apiClient: any APIClientProtocol
    var firebaseSession: FirebaseSession? = nil
    let tokenStore: DeviceTokenStore
    let enrollmentService: any EnrollmentServiceProtocol
    let userService: any UserServiceProtocol
    let curriculumService: any CurriculumServiceProtocol
    let vocabularyService: any VocabularyServiceProtocol
    let grammarService: any GrammarServiceProtocol
    let learningEventService: any LearningEventServiceProtocol
    let masteryService: any MasteryServiceProtocol
    let dailyPlanService: any DailyPlanServiceProtocol
    let exerciseService: any ExerciseServiceProtocol
    let progressService: any ProgressServiceProtocol
    let partnerService: any PartnerServiceProtocol
    let aiProgressService: any AIProgressServiceProtocol
    let widgetSyncService: any WidgetSyncServiceProtocol
    let vocabularyLearningService: any VocabularyLearningServiceProtocol
    let vocabularyNotificationService: VocabularyNotificationService

    var readingAPI: ReadingAPI {
        ReadingAPI(client: apiClient, baseURL: environment.apiBaseURL, tokens: (firebaseSession as (any AccessTokenProvider)?) ?? tokenStore)
    }

    @MainActor
    static func live(environment: AppEnvironment = .current) -> DependencyContainer {
        let tokenStore = DeviceTokenStore()
        let firebase = FirebaseSession(legacy: tokenStore)
        let apiClient = APIClient(
            baseURL: environment.apiBaseURL,
            tokenProvider: firebase
        )
        firebase.onSessionChange = { [weak apiClient] in apiClient?.cancelAuthenticatedRequests() }
        let vocabularyNotifications = VocabularyNotificationService()
        return DependencyContainer(
            environment: environment,
            apiClient: apiClient,
            firebaseSession: firebase,
            tokenStore: tokenStore,
            enrollmentService: EnrollmentService(apiClient: apiClient),
            userService: UserService(apiClient: apiClient),
            curriculumService: CurriculumService(apiClient: apiClient),
            vocabularyService: VocabularyService(apiClient: apiClient),
            grammarService: GrammarService(apiClient: apiClient),
            learningEventService: LearningEventService(apiClient: apiClient),
            masteryService: MasteryService(apiClient: apiClient),
            dailyPlanService: DailyPlanService(apiClient: apiClient),
            exerciseService: ExerciseService(apiClient: apiClient),
            progressService: ProgressService(apiClient: apiClient),
            partnerService: PartnerService(apiClient: apiClient),
            aiProgressService: AIProgressService(apiClient: apiClient),
            widgetSyncService: WidgetSyncService(apiClient: apiClient),
            vocabularyLearningService: VocabularyLearningService(apiClient: apiClient),
            vocabularyNotificationService: vocabularyNotifications
        )
    }
}
