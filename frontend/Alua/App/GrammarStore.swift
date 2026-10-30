import Foundation
import Observation

@MainActor
@Observable
final class GrammarStore {
    private(set) var currentLesson: GrammarLesson?
    private(set) var stageLessons: [GrammarLesson] = []
    private(set) var searchResults: [GrammarLesson] = []
    private(set) var isLoadingLesson = false
    private(set) var isLoadingStage = false
    private(set) var isSearching = false
    var errorMessage: String?

    @ObservationIgnored private let service: any GrammarServiceProtocol
    @ObservationIgnored private var lessonCache: [String: GrammarLesson] = [:]

    init(service: any GrammarServiceProtocol) {
        self.service = service
    }

    func lesson(id: String) -> GrammarLesson? { lessonCache[id] }

    func loadLesson(id: String) async {
        if let cached = lessonCache[id] {
            currentLesson = cached
            return
        }
        await loadLesson { try await service.getLesson(id: id) }
    }

    func loadLesson(curriculumNodeID: String) async {
        await loadLesson { try await service.getLessonForCurriculumNode(id: curriculumNodeID) }
    }

    func loadStage(id: String) async {
        isLoadingStage = true
        errorMessage = nil
        defer { isLoadingStage = false }
        do {
            let response = try await service.getStage(id: id)
            stageLessons = response.lessons
            cache(response.lessons)
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    func search(_ query: String) async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            searchResults = []
            return
        }
        isSearching = true
        errorMessage = nil
        defer { isSearching = false }
        do {
            searchResults = try await service.search(query: trimmed).items
            cache(searchResults)
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    func clear() {
        currentLesson = nil
        stageLessons = []
        searchResults = []
        lessonCache = [:]
        errorMessage = nil
    }

    private func loadLesson(_ operation: () async throws -> GrammarLesson) async {
        isLoadingLesson = true
        errorMessage = nil
        defer { isLoadingLesson = false }
        do {
            let lesson = try await operation()
            currentLesson = lesson
            lessonCache[lesson.id] = lesson
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    private func cache(_ lessons: [GrammarLesson]) {
        for lesson in lessons { lessonCache[lesson.id] = lesson }
    }

    private func readableMessage(for error: Error) -> String {
        (error as? LocalizedError)?.errorDescription ?? "Grammar content could not be loaded."
    }
}
