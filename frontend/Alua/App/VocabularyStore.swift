import Foundation
import Observation

@MainActor
@Observable
final class VocabularyStore {
    private(set) var tracks: [VocabularyTrackSummary] = []
    private(set) var currentTrack: VocabularyTrackDetail?
    private(set) var searchResults: [VocabularyItem] = []
    private(set) var isLoadingTracks = false
    private(set) var isLoadingTrack = false
    private(set) var isSearching = false
    var errorMessage: String?

    @ObservationIgnored private let service: any VocabularyServiceProtocol

    init(service: any VocabularyServiceProtocol) {
        self.service = service
    }

    func loadTracksIfNeeded() async {
        guard tracks.isEmpty, !isLoadingTracks else { return }
        isLoadingTracks = true
        errorMessage = nil
        defer { isLoadingTracks = false }
        do {
            tracks = try await service.listTracks()
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    func loadTrack(id: String) async {
        guard currentTrack?.track.id != id else { return }
        await loadTrack { try await service.getTrack(id: id) }
    }

    func loadTrack(curriculumNodeID: String) async {
        await loadTrack {
            guard let detail = try await service.getCurriculumNode(id: curriculumNodeID).tracks.first
            else { throw VocabularyStoreError.emptyCurriculumMapping }
            return detail
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
            searchResults = try await service.search(query: trimmed, limit: 50).items
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    func clear() {
        tracks = []
        currentTrack = nil
        searchResults = []
        errorMessage = nil
    }

    private func loadTrack(_ operation: () async throws -> VocabularyTrackDetail) async {
        isLoadingTrack = true
        errorMessage = nil
        currentTrack = nil
        defer { isLoadingTrack = false }
        do {
            currentTrack = try await operation()
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    private func readableMessage(for error: Error) -> String {
        (error as? LocalizedError)?.errorDescription ?? "Vocabulary could not be loaded."
    }
}

private enum VocabularyStoreError: LocalizedError {
    case emptyCurriculumMapping

    var errorDescription: String? { "This curriculum node has no vocabulary track." }
}
