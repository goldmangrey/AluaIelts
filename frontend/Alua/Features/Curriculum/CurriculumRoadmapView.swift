import SwiftUI

struct CurriculumRoadmapView: View {
    let store: CurriculumStore
    let vocabularyStore: VocabularyStore
    let grammarStore: GrammarStore
    let learningEventService: any LearningEventServiceProtocol

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: AluaSpacing.md) {
                ForEach(store.overview?.stages ?? []) { progress in
                    NavigationLink {
                        CurriculumStageView(
                            progress: progress,
                            store: store,
                            vocabularyStore: vocabularyStore,
                            grammarStore: grammarStore,
                            learningEventService: learningEventService
                        )
                    } label: {
                        AluaCard {
                            HStack(spacing: AluaSpacing.md) {
                                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                                    Text(progress.stage.title).font(AluaTypography.headline)
                                    Text(progress.stage.subtitle)
                                        .font(AluaTypography.subheadline)
                                        .foregroundStyle(AluaColors.secondaryText)
                                }
                                Spacer()
                                stageIndicator(progress)
                                Image(systemName: "chevron.right")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(AluaColors.secondaryText)
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle("Academic Roadmap")
    }

    private func stageIndicator(_ progress: CurriculumStageProgress) -> some View {
        let completed = progress.nodes.filter { $0.status == .completed }.count
        let hasActive = progress.nodes.contains { $0.status == .active }
        let isRecommended = progress.stage.id == store.overview?.recommendedStageID
        return VStack(alignment: .trailing, spacing: AluaSpacing.xs) {
            Text("\(progress.stage.cefrFrom.rawValue)–\(progress.stage.cefrTo.rawValue)")
            if hasActive {
                Label("Current", systemImage: "play.circle.fill")
            } else if completed == progress.nodes.count {
                Label("Completed", systemImage: "checkmark.circle.fill")
            } else if isRecommended {
                Label("Recommended", systemImage: "bookmark")
            } else {
                Label("Structured", systemImage: "list.bullet")
            }
        }
        .font(AluaTypography.caption)
        .foregroundStyle(hasActive || isRecommended ? AluaColors.accent : AluaColors.secondaryText)
    }
}
