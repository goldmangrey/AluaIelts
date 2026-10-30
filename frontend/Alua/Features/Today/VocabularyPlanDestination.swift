import SwiftUI

struct VocabularyPlanDestination: View {
    let itemID: String
    let curriculumNodeID: String?
    let vocabularyService: any VocabularyServiceProtocol
    let learningEventService: any LearningEventServiceProtocol

    @State private var item: VocabularyItem?
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if let item {
                VocabularyWordDetailView(
                    item: item,
                    curriculumNodeID: curriculumNodeID,
                    learningEventService: learningEventService
                )
            } else if let errorMessage {
                ContentUnavailableView {
                    Label("Word unavailable", systemImage: "character.book.closed")
                } description: {
                    Text(errorMessage)
                } actions: {
                    Button("Retry") { Task { await load() } }
                }
            } else {
                SwiftUI.ProgressView("Loading word…")
            }
        }
        .task(id: itemID) { await load() }
    }

    private func load() async {
        errorMessage = nil
        do {
            item = try await vocabularyService.getItem(id: itemID)
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription
                ?? "This vocabulary item could not be loaded."
        }
    }
}
