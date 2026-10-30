import SwiftUI

struct CurriculumNodeView: View {
    let progress: CurriculumNodeProgress
    let store: CurriculumStore
    let vocabularyStore: VocabularyStore
    let grammarStore: GrammarStore
    let learningEventService: any LearningEventServiceProtocol

    private var currentProgress: CurriculumNodeProgress {
        store.node(id: progress.node.id) ?? progress
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    Label(currentProgress.node.track.title, systemImage: trackSymbol)
                        .font(AluaTypography.subheadline.weight(.semibold))
                        .foregroundStyle(AluaColors.accent)
                    Text(currentProgress.node.description).font(AluaTypography.body)
                    Label(
                        "\(currentProgress.node.estimatedMinutes) minutes · \(currentProgress.node.cefrLevel.rawValue)",
                        systemImage: "clock"
                    )
                    .font(AluaTypography.caption)
                    .foregroundStyle(AluaColors.secondaryText)
                }

                if !currentProgress.node.objectives.isEmpty {
                    detailSection("Objectives", values: currentProgress.node.objectives)
                }

                if !currentProgress.node.prerequisites.isEmpty {
                    detailSection("Prerequisites", values: prerequisiteTitles)
                }

                actionContent

                if let error = store.errorMessage {
                    Label(error, systemImage: "exclamationmark.circle")
                        .font(AluaTypography.subheadline)
                        .foregroundStyle(.red)
                }
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle(currentProgress.node.title)
        .navigationBarTitleDisplayMode(.inline)
    }

    @ViewBuilder
    private var actionContent: some View {
        switch currentProgress.status {
        case .available:
            PrimaryButton(
                title: store.startingNodeID == currentProgress.node.id ? "Starting…" : "Start",
                isDisabled: store.startingNodeID != nil
            ) {
                Task { await store.startNode(id: currentProgress.node.id) }
            }
        case .active:
            activeContent
        case .locked:
            AluaCard {
                Label("Complete prerequisites first", systemImage: "lock")
                    .font(AluaTypography.headline)
                    .foregroundStyle(AluaColors.secondaryText)
            }
        case .completed:
            if currentProgress.node.type == .vocabularyTrack {
                vocabularyLink(label: "Review vocabulary")
            } else if currentProgress.node.type == .grammarTopic {
                grammarLink(label: "Review grammar lesson")
            } else {
                AluaCard {
                    Label("Completed", systemImage: "checkmark.circle.fill")
                        .font(AluaTypography.headline)
                        .foregroundStyle(AluaColors.accent)
                }
            }
        }
    }

    @ViewBuilder
    private var activeContent: some View {
        if currentProgress.node.type == .vocabularyTrack {
            vocabularyLink(label: "Open vocabulary track")
        } else if currentProgress.node.type == .grammarTopic {
            grammarLink(label: "Open grammar lesson")
        } else {
            AluaCard {
                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    Label("Active", systemImage: "play.circle.fill")
                        .font(AluaTypography.headline)
                        .foregroundStyle(AluaColors.accent)
                    Text("Learning content for this track is not available yet.")
                        .foregroundStyle(AluaColors.secondaryText)
                }
            }
        }
    }

    private func vocabularyLink(label: String) -> some View {
        NavigationLink {
            VocabularyTrackView(
                curriculumNodeID: currentProgress.node.id,
                store: vocabularyStore,
                learningEventService: learningEventService
            )
        } label: {
            AluaCard {
                HStack {
                    Label(label, systemImage: "character.book.closed.fill")
                        .font(AluaTypography.headline)
                    Spacer()
                    Image(systemName: "chevron.right")
                }
                .foregroundStyle(AluaColors.accent)
            }
        }
        .buttonStyle(.plain)
    }

    private func grammarLink(label: String) -> some View {
        NavigationLink {
            GrammarLessonView(
                curriculumNodeID: currentProgress.node.id,
                store: grammarStore,
                learningEventService: learningEventService
            )
        } label: {
            AluaCard {
                HStack {
                    Label(label, systemImage: "text.book.closed.fill")
                        .font(AluaTypography.headline)
                    Spacer()
                    Image(systemName: "chevron.right")
                }
                .foregroundStyle(AluaColors.accent)
            }
        }
        .buttonStyle(.plain)
    }

    private var prerequisiteTitles: [String] {
        currentProgress.node.prerequisites.map { id in
            store.node(id: id)?.node.title ?? id
        }
    }

    private var trackSymbol: String {
        switch currentProgress.node.track {
        case .grammar: "textformat"
        case .vocabulary: "character.book.closed"
        case .mixed: "arrow.triangle.2.circlepath"
        }
    }

    private func detailSection(_ title: String, values: [String]) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: title)
            AluaCard {
                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    ForEach(values, id: \.self) { value in
                        Label(value, systemImage: "circle.fill")
                            .font(AluaTypography.subheadline)
                            .symbolRenderingMode(.hierarchical)
                    }
                }
            }
        }
    }
}
