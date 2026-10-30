import SwiftUI

struct GrammarLessonView: View {
    private let lessonID: String?
    private let curriculumNodeID: String?
    let store: GrammarStore
    let learningEventService: any LearningEventServiceProtocol
    @State private var didRecordOpen = false

    init(
        lessonID: String,
        store: GrammarStore,
        learningEventService: any LearningEventServiceProtocol
    ) {
        self.lessonID = lessonID
        curriculumNodeID = nil
        self.store = store
        self.learningEventService = learningEventService
    }

    init(
        curriculumNodeID: String,
        store: GrammarStore,
        learningEventService: any LearningEventServiceProtocol
    ) {
        lessonID = nil
        self.curriculumNodeID = curriculumNodeID
        self.store = store
        self.learningEventService = learningEventService
    }

    var body: some View {
        Group {
            if let lesson = resolvedLesson {
                lessonContent(lesson)
            } else if store.isLoadingLesson {
                SwiftUI.ProgressView("Загружаем урок…")
            } else {
                ContentUnavailableView {
                    Label("Урок недоступен", systemImage: "text.book.closed")
                } description: {
                    Text(store.errorMessage ?? "Не удалось загрузить урок. Проверьте соединение.")
                }
            }
        }
        .task(id: loadID) {
            if let lessonID {
                await store.loadLesson(id: lessonID)
            } else if let curriculumNodeID {
                await store.loadLesson(curriculumNodeID: curriculumNodeID)
            }
        }
        .task(id: resolvedLesson?.id) {
            guard let lesson = resolvedLesson, !didRecordOpen else { return }
            didRecordOpen = true
            await learningEventService.recordGrammarLessonOpened(
                id: lesson.id,
                curriculumNodeID: curriculumNodeID
            )
        }
    }

    private var resolvedLesson: GrammarLesson? {
        if let lessonID { return store.lesson(id: lessonID) }
        return store.currentLesson?.curriculumNodeIDs.contains(curriculumNodeID ?? "") == true
            ? store.currentLesson : nil
    }

    private var loadID: String { lessonID ?? curriculumNodeID ?? "" }

    private func lessonContent(_ lesson: GrammarLesson) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.xl) {
                header(lesson)
                structures(lesson)
                uses(lesson)
                examples(lesson)
                russianSupport(lesson)
                if !lesson.commonErrors.isEmpty {
                    section("Частые ошибки") {
                        ForEach(lesson.commonErrors) { error in
                            GrammarErrorCard(error: error)
                        }
                    }
                }
                if !lesson.contrasts.isEmpty { contrasts(lesson) }
                if !lesson.usageNotes.isEmpty {
                    section("Обратите внимание") {
                        AluaCard {
                            VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                                ForEach(lesson.usageNotes, id: \.self) { Text($0) }
                            }
                        }
                    }
                }
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle(lesson.title)
        .navigationBarTitleDisplayMode(.inline)
    }

    private func header(_ lesson: GrammarLesson) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Text("\(lesson.cefrLevel.rawValue) · Грамматика")
                .font(AluaTypography.caption.weight(.semibold))
                .foregroundStyle(AluaColors.accent)
            Text(lesson.title).font(AluaTypography.largeTitle)
            Text(lesson.summary).font(AluaTypography.title)
            Text(lesson.explanationEN)
                .font(AluaTypography.body)
                .foregroundStyle(AluaColors.secondaryText)
        }
    }

    private func structures(_ lesson: GrammarLesson) -> some View {
        section("Структура") {
            ForEach(lesson.structures, id: \.self) { structure in
                AluaCard {
                    VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                        Text(structure.label).font(AluaTypography.headline)
                        Text(structure.formula)
                            .font(.body.monospaced().weight(.semibold))
                            .textSelection(.enabled)
                        Text(structure.example)
                            .font(AluaTypography.body)
                            .foregroundStyle(AluaColors.secondaryText)
                    }
                }
            }
        }
    }

    private func uses(_ lesson: GrammarLesson) -> some View {
        section("Когда использовать") {
            ForEach(lesson.uses, id: \.self) { use in
                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                    Text(use.title).font(AluaTypography.headline)
                    Text(use.explanationEN).font(AluaTypography.body)
                    Text(use.example)
                        .font(AluaTypography.body.italic())
                        .foregroundStyle(AluaColors.secondaryText)
                }
            }
        }
    }

    private func examples(_ lesson: GrammarLesson) -> some View {
        section("Примеры") {
            AluaCard {
                VStack(alignment: .leading, spacing: AluaSpacing.md) {
                    ForEach(lesson.examples, id: \.self) { example in
                        VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                            Text(example.sentence).font(AluaTypography.body)
                            if let translation = example.translationRU {
                                Text(translation)
                                    .font(AluaTypography.body)
                                    .foregroundStyle(AluaColors.secondaryText)
                            }
                        }
                    }
                }
            }
        }
    }

    private func russianSupport(_ lesson: GrammarLesson) -> some View {
        section("По-русски") {
            AluaCard {
                Text(lesson.explanationRU).font(AluaTypography.body)
            }
        }
    }

    private func contrasts(_ lesson: GrammarLesson) -> some View {
        section("Сравните") {
            ForEach(lesson.contrasts) { contrast in
                AluaCard {
                    VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                        Text(contrast.title).font(AluaTypography.headline)
                        Text(contrast.explanationEN).font(AluaTypography.body)
                        ForEach(contrast.examples, id: \.self) { example in
                            Text(example.sentence)
                                .font(AluaTypography.subheadline.italic())
                        }
                        Text(contrast.explanationRU)
                            .font(AluaTypography.subheadline)
                            .foregroundStyle(AluaColors.secondaryText)
                        if let relatedID = contrast.relatedLessonID {
                            NavigationLink("Open related lesson") {
                                GrammarLessonView(
                                    lessonID: relatedID,
                                    store: store,
                                    learningEventService: learningEventService
                                )
                            }
                            .font(AluaTypography.headline)
                        }
                    }
                }
            }
        }
    }

    private func section<Content: View>(
        _ title: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: title)
            content()
        }
    }
}
