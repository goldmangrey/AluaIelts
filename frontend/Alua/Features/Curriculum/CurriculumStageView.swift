import SwiftUI

struct CurriculumStageView: View {
    let progress: CurriculumStageProgress
    let store: CurriculumStore
    let vocabularyStore: VocabularyStore
    let grammarStore: GrammarStore
    let learningEventService: any LearningEventServiceProtocol

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    Text(progress.stage.subtitle)
                        .font(AluaTypography.subheadline)
                        .foregroundStyle(AluaColors.accent)
                    Text(progress.stage.description).font(AluaTypography.body)
                    if let weeks = progress.stage.estimatedWeeks {
                        Label("About \(weeks) weeks", systemImage: "calendar")
                            .font(AluaTypography.caption)
                            .foregroundStyle(AluaColors.secondaryText)
                    }
                }

                ForEach(CurriculumTrack.allCases, id: \.self) { track in
                    let nodes = progress.nodes.filter { $0.node.track == track }
                    if !nodes.isEmpty {
                        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                            AluaSectionHeader(title: track.title)
                            ForEach(nodes) { nodeProgress in
                                NavigationLink {
                                    CurriculumNodeView(
                                        progress: nodeProgress,
                                        store: store,
                                        vocabularyStore: vocabularyStore,
                                        grammarStore: grammarStore,
                                        learningEventService: learningEventService
                                    )
                                } label: {
                                    CurriculumNodeRow(progress: nodeProgress)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle(progress.stage.title)
        .navigationBarTitleDisplayMode(.inline)
    }
}
