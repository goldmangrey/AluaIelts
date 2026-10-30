import SwiftUI

struct VocabularyLibraryView: View {
    let store: VocabularyStore
    let curriculumStore: CurriculumStore
    let learningEventService: any LearningEventServiceProtocol
    @State private var searchText = ""

    var body: some View {
        Group {
            if store.isLoadingTracks, store.tracks.isEmpty {
                SwiftUI.ProgressView("Loading vocabulary…")
            } else if !searchText.isEmpty {
                searchContent
            } else {
                trackContent
            }
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle("Vocabulary")
        .searchable(text: $searchText, prompt: "Search words and meanings")
        .onSubmit(of: .search) { Task { await store.search(searchText) } }
        .onChange(of: searchText) { _, value in
            if value.isEmpty { Task { await store.search("") } }
        }
        .task { await store.loadTracksIfNeeded() }
    }

    private var trackContent: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: AluaSpacing.lg) {
                if let recommendation = recommendedVocabularyNode,
                   let trackID = recommendation.contentRefs.first
                {
                    VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                        AluaSectionHeader(title: "Current recommendation")
                        NavigationLink {
                            VocabularyTrackView(
                                trackID: trackID,
                                store: store,
                                learningEventService: learningEventService
                            )
                        } label: {
                            AluaCard {
                                HStack {
                                    VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                                        Text(recommendation.title).font(AluaTypography.headline)
                                        Text("Part of your academic path")
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

                ForEach(stageIDs, id: \.self) { stageID in
                    let stageTracks = store.tracks.filter { $0.stageID == stageID }
                    if !stageTracks.isEmpty {
                        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                            AluaSectionHeader(
                                title: stageTitle(stageID),
                                subtitle: stageTracks.first?.cefrLevel
                            )
                            ForEach(stageTracks) { track in
                                NavigationLink {
                                    VocabularyTrackView(
                                        trackID: track.id,
                                        store: store,
                                        learningEventService: learningEventService
                                    )
                                } label: {
                                    trackRow(track)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
            }
            .padding(AluaSpacing.md)
        }
        .refreshable { await store.loadTracksIfNeeded() }
    }

    @ViewBuilder
    private var searchContent: some View {
        if store.isSearching {
            SwiftUI.ProgressView("Searching…")
        } else if store.searchResults.isEmpty {
            ContentUnavailableView.search(text: searchText)
        } else {
            List(store.searchResults) { item in
                NavigationLink {
                    VocabularyWordDetailView(
                        item: item,
                        curriculumNodeID: nil,
                        learningEventService: learningEventService
                    )
                } label: {
                    VocabularyWordRow(item: item)
                }
            }
            .listStyle(.plain)
        }
    }

    private var recommendedVocabularyNode: CurriculumNode? {
        curriculumStore.overview?.recommendedNextNodes.first { $0.track == .vocabulary }
            ?? curriculumStore.currentFocus.flatMap { $0.track == .vocabulary ? $0 : nil }
    }

    private var stageIDs: [String] {
        ["foundation_a1", "core_a2", "intermediate_b1", "upper_intermediate_b2", "ielts_academic"]
    }

    private func stageTitle(_ id: String) -> String {
        curriculumStore.overview?.stages.first { $0.stage.id == id }?.stage.title
            ?? id.replacingOccurrences(of: "_", with: " ").capitalized
    }

    private func trackRow(_ track: VocabularyTrackSummary) -> some View {
        AluaCard {
            HStack(spacing: AluaSpacing.md) {
                Image(systemName: "character.book.closed")
                    .foregroundStyle(AluaColors.accent)
                    .frame(width: 28)
                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                    Text(track.title).font(AluaTypography.headline)
                    Text("\(track.itemCount) words · \(track.cefrLevel)")
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
}
