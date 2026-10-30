import SwiftUI

struct GrammarLibraryView: View {
    let store: GrammarStore
    let curriculumStore: CurriculumStore
    let learningEventService: any LearningEventServiceProtocol
    @State private var searchText = ""

    var body: some View {
        Group {
            if searchText.isEmpty {
                libraryContent
            } else if store.isSearching {
                SwiftUI.ProgressView("Ищем темы…")
            } else if store.searchResults.isEmpty {
                ContentUnavailableView.search(text: searchText)
            } else {
                List(store.searchResults) { lesson in
                    NavigationLink {
                        GrammarLessonView(
                            lessonID: lesson.id,
                            store: store,
                            learningEventService: learningEventService
                        )
                    } label: {
                        GrammarLessonRow(lesson: lesson)
                    }
                }
                .listStyle(.plain)
            }
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle("Грамматика")
        .searchable(text: $searchText, prompt: "Тема или правило")
        .onSubmit(of: .search) { Task { await store.search(searchText) } }
        .onChange(of: searchText) { _, value in
            if value.isEmpty { Task { await store.search("") } }
        }
    }

    private var libraryContent: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: AluaSpacing.lg) {
                if let node = recommendedGrammarNode {
                    VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                        AluaSectionHeader(title: "Продолжить изучение")
                        NavigationLink {
                            GrammarLessonView(
                                curriculumNodeID: node.id,
                                store: store,
                                learningEventService: learningEventService
                            )
                        } label: {
                            AluaCard {
                                HStack {
                                    VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                                        Text(node.title).font(AluaTypography.headline)
                                        Text(node.description)
                                            .font(AluaTypography.caption)
                                            .foregroundStyle(AluaColors.secondaryText)
                                    }
                                    Spacer()
                                    Image(systemName: "arrow.right.circle.fill")
                                        .foregroundStyle(AluaColors.accent)
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }

                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    AluaSectionHeader(
                        title: "По уровню",
                        subtitle: "Темы в порядке учебной программы"
                    )
                    ForEach(curriculumStore.overview?.stages ?? []) { stage in
                        NavigationLink {
                            GrammarStageView(
                                stage: stage,
                                store: store,
                                curriculumStore: curriculumStore,
                                learningEventService: learningEventService
                            )
                        } label: {
                            AluaCard {
                                HStack(spacing: AluaSpacing.md) {
                                    Image(systemName: "text.book.closed")
                                        .foregroundStyle(AluaColors.accent)
                                    VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                                        Text(stage.stage.title).font(AluaTypography.headline)
                                        Text("\(stage.nodes.filter { $0.node.track == .grammar }.count) тем · \(stage.stage.cefrTo.rawValue)")
                                            .font(AluaTypography.caption)
                                            .foregroundStyle(AluaColors.secondaryText)
                                    }
                                    Spacer()
                                    Image(systemName: "chevron.right")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(AluaColors.secondaryText)
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .padding(AluaSpacing.md)
        }
    }

    private var recommendedGrammarNode: CurriculumNode? {
        curriculumStore.overview?.recommendedNextNodes.first { $0.track == .grammar }
            ?? curriculumStore.currentFocus.flatMap { $0.track == .grammar ? $0 : nil }
    }
}

struct GrammarLessonRow: View {
    let lesson: GrammarLesson
    var status: CurriculumNodeStatus?

    var body: some View {
        VStack(alignment: .leading, spacing: AluaSpacing.xs) {
            HStack {
                Text(lesson.title).font(AluaTypography.headline)
                Spacer()
                Text(lesson.cefrLevel.rawValue)
                    .font(AluaTypography.caption.weight(.semibold))
                    .foregroundStyle(AluaColors.accent)
            }
            Text(lesson.summary)
                .font(AluaTypography.subheadline)
                .foregroundStyle(AluaColors.secondaryText)
                .lineLimit(2)
            if let status {
                Label(status.title, systemImage: status.systemImage)
                    .font(AluaTypography.caption)
                    .foregroundStyle(AluaColors.secondaryText)
            }
        }
        .padding(.vertical, AluaSpacing.xs)
    }
}
