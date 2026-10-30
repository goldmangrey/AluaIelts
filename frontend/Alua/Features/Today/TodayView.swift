import SwiftUI

struct TodayView: View {
    let studyStore: StudyStore?
    let environment: AppEnvironment
    let authSession: AuthSession
    let curriculumStore: CurriculumStore
    let vocabularyStore: VocabularyStore
    let grammarStore: GrammarStore
    let studentModelStore: StudentModelStore
    let dailyPlanStore: DailyPlanStore
    let vocabularyService: any VocabularyServiceProtocol
    let learningEventService: any LearningEventServiceProtocol
    let exerciseService: any ExerciseServiceProtocol
    let onOpenVocabulary: () -> Void

    private var todayDate: String {
        var format = Date.FormatStyle().day().month(.wide)
        format.locale = Locale(identifier: "ru_RU")
        format.timeZone = TimeZone(identifier: "Asia/Almaty") ?? .current
        return Date.now.formatted(format)
    }
    var body: some View {
        AluaPage {
            VStack(alignment: .leading, spacing: 8) {
                Text("alua.").font(.largeTitle.weight(.bold)).accessibilityLabel("Alua")
                Text(todayDate)
                    .font(.subheadline).foregroundStyle(AluaColors.secondaryText)
            }
            if let studyStore {
                StudyHome(store: studyStore, onOpenBook: onOpenVocabulary)
            } else { StudyLoading(store: nil) }
            Divider()
            VStack(spacing: 0) {
                NavigationLink {
                    GrammarLibraryView(store: grammarStore, curriculumStore: curriculumStore, learningEventService: learningEventService)
                } label: { AluaRouteRow(title: "Грамматика", subtitle: "Правила, примеры и практика", symbol: "text.book.closed") }.accessibilityIdentifier("today.grammar")
                if let studyStore {
                    NavigationLink {
                        DiagnosticView(service: LearningQualityService(apiClient: studyStore.api))
                    } label: { AluaRouteRow(title: "Стартовая проверка", subtitle: "12 вопросов · можно пройти позже", symbol: "slider.horizontal.3") }.accessibilityIdentifier("today.diagnostic")
                }
                if let plan = dailyPlanStore.plan, !plan.items.isEmpty {
                    NavigationLink("Практика по учебному плану") {
                        List(plan.items) { item in
                            NavigationLink(item.title) {
                                DailyPlanActivityView(planDate: plan.localDate, item: item, curriculumStore: curriculumStore, vocabularyStore: vocabularyStore, grammarStore: grammarStore, dailyPlanStore: dailyPlanStore, studentModelStore: studentModelStore, vocabularyService: vocabularyService, learningEventService: learningEventService, exerciseService: exerciseService)
                            }
                        }.navigationTitle("Практика")
                    }.frame(minHeight: 44)
                }
            }.buttonStyle(.plain)
        }
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await studyStore?.sync() }
        .task { await dailyPlanStore.ensureToday() }
    }
}
