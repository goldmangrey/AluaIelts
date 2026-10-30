import SwiftUI

struct DailyPlanActivityView: View {
    let planDate: String
    let item: DailyPlanItem
    let curriculumStore: CurriculumStore
    let vocabularyStore: VocabularyStore
    let grammarStore: GrammarStore
    let dailyPlanStore: DailyPlanStore
    let studentModelStore: StudentModelStore
    let vocabularyService: any VocabularyServiceProtocol
    let learningEventService: any LearningEventServiceProtocol
    let exerciseService: any ExerciseServiceProtocol

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                    Text(item.kind.title).font(AluaTypography.caption).foregroundStyle(AluaColors.accent)
                    Text(item.title).font(AluaTypography.largeTitle)
                    Text("~\(item.estimatedMinutes) мин").foregroundStyle(AluaColors.secondaryText)
                }
                AluaCard {
                    VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                        Text("Почему эта тема").font(AluaTypography.headline)
                        Text(item.reason.userFacingTitle).foregroundStyle(AluaColors.secondaryText)
                    }
                }
                NavigationLink { contentDestination } label: {
                    AluaCard { Label(contentLabel, systemImage: "book.closed").font(AluaTypography.headline) }
                }.buttonStyle(.plain)
                NavigationLink {
                    ExerciseSessionView(
                        planDate: planDate,
                        item: item,
                        service: exerciseService,
                        dailyPlanStore: dailyPlanStore,
                        studentModelStore: studentModelStore
                    )
                } label: {
                    AluaCard {
                        HStack {
                            Label(
                                item.state == .completed
                                    ? "Повторить практику" : "Перейти к практике",
                                systemImage: "pencil.and.list.clipboard"
                            )
                                .font(AluaTypography.headline)
                            Spacer(); Image(systemName: "chevron.right")
                        }.foregroundStyle(AluaColors.accent)
                    }
                }.buttonStyle(.plain)
                if item.state == .completed {
                    Label("Задание завершено", systemImage: "checkmark.circle.fill")
                        .foregroundStyle(AluaColors.accent)
                }
            }.padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle("Занятие")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var contentLabel: String {
        switch item.kind {
        case .grammarFocus: "Open Lesson"
        case .grammarReview: "Review Lesson"
        case .vocabularyLearning: "Open Word"
        case .vocabularyReview: "Review Word"
        case .reinforcement: "Open Curriculum Topic"
        }
    }

    @ViewBuilder private var contentDestination: some View {
        switch item.contentType {
        case .grammarLesson:
            GrammarLessonView(lessonID: item.contentID, store: grammarStore, learningEventService: learningEventService)
        case .vocabularyItem:
            VocabularyPlanDestination(itemID: item.contentID, curriculumNodeID: item.curriculumNodeID, vocabularyService: vocabularyService, learningEventService: learningEventService)
        case .curriculumNode:
            if let progress = curriculumStore.node(id: item.contentID) {
                CurriculumNodeView(progress: progress, store: curriculumStore, vocabularyStore: vocabularyStore, grammarStore: grammarStore, learningEventService: learningEventService)
            } else { ContentUnavailableView("Learning path unavailable", systemImage: "book.closed") }
        }
    }
}
