import SwiftUI

struct GrammarStageView: View {
    let stage: CurriculumStageProgress
    let store: GrammarStore
    let curriculumStore: CurriculumStore
    let learningEventService: any LearningEventServiceProtocol

    var body: some View {
        Group {
            if store.isLoadingStage {
                SwiftUI.ProgressView("Загружаем темы…")
            } else if store.stageLessons.isEmpty {
                ContentUnavailableView {
                    Label("Темы недоступны", systemImage: "text.book.closed")
                } description: {
                    Text(store.errorMessage ?? "Не удалось загрузить этот раздел.")
                }
            } else {
                List(store.stageLessons) { lesson in
                    NavigationLink {
                        GrammarLessonView(
                            lessonID: lesson.id,
                            store: store,
                            learningEventService: learningEventService
                        )
                    } label: {
                        GrammarLessonRow(
                            lesson: lesson,
                            status: curriculumStore.node(id: lesson.curriculumNodeIDs[0])?.status
                        )
                    }
                }
                .listStyle(.insetGrouped)
            }
        }
        .navigationTitle(stage.stage.title)
        .navigationBarTitleDisplayMode(.inline)
        .task(id: stage.stage.id) { await store.loadStage(id: stage.stage.id) }
    }
}
