import SwiftUI

struct VocabularyTrackView: View {
    private let trackID: String?
    private let curriculumNodeID: String?
    let store: VocabularyStore
    let learningEventService: any LearningEventServiceProtocol
    @State private var didRecordOpen = false

    init(
        trackID: String,
        store: VocabularyStore,
        learningEventService: any LearningEventServiceProtocol
    ) {
        self.trackID = trackID
        curriculumNodeID = nil
        self.store = store
        self.learningEventService = learningEventService
    }

    init(
        curriculumNodeID: String,
        store: VocabularyStore,
        learningEventService: any LearningEventServiceProtocol
    ) {
        trackID = nil
        self.curriculumNodeID = curriculumNodeID
        self.store = store
        self.learningEventService = learningEventService
    }

    var body: some View {
        Group {
            if store.isLoadingTrack {
                SwiftUI.ProgressView("Loading track…")
            } else if let detail = store.currentTrack {
                List {
                    Section {
                        Text(detail.track.description)
                            .font(AluaTypography.body)
                            .foregroundStyle(AluaColors.secondaryText)
                    }
                    Section("Words and phrases") {
                        ForEach(detail.items) { item in
                            NavigationLink {
                                VocabularyWordDetailView(
                                    item: item,
                                    curriculumNodeID: curriculumNodeID,
                                    learningEventService: learningEventService
                                )
                            } label: {
                                VocabularyWordRow(item: item)
                            }
                        }
                    }
                }
                .listStyle(.insetGrouped)
                .navigationTitle(detail.track.title)
            } else {
                ContentUnavailableView {
                    Label("Track unavailable", systemImage: "character.book.closed")
                } description: {
                    Text(store.errorMessage ?? "This vocabulary track could not be loaded.")
                }
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .task(id: loadID) {
            if let trackID {
                await store.loadTrack(id: trackID)
            } else if let curriculumNodeID {
                await store.loadTrack(curriculumNodeID: curriculumNodeID)
            }
        }
        .task(id: store.currentTrack?.track.id) {
            guard let detail = store.currentTrack, !didRecordOpen else { return }
            didRecordOpen = true
            await learningEventService.recordVocabularyTrackOpened(
                id: detail.track.id,
                curriculumNodeID: curriculumNodeID
            )
        }
    }

    private var loadID: String { trackID ?? curriculumNodeID ?? "" }
}

struct VocabularyWordRow: View {
    let item: VocabularyItem

    var body: some View {
        VStack(alignment: .leading, spacing: AluaSpacing.xs) {
            HStack {
                Text(item.lemma).font(AluaTypography.headline)
                Spacer()
                Text(item.cefrLevel.rawValue)
                    .font(AluaTypography.caption.weight(.semibold))
                    .foregroundStyle(AluaColors.accent)
            }
            Text(item.translationRU)
                .font(AluaTypography.subheadline)
                .foregroundStyle(AluaColors.secondaryText)
            Text(item.partOfSpeech.title)
                .font(AluaTypography.caption)
                .foregroundStyle(AluaColors.secondaryText)
        }
        .padding(.vertical, AluaSpacing.xs)
    }
}
