import Foundation
import Observation

@MainActor
@Observable
final class CurriculumStore {
    private(set) var overview: UserCurriculumOverview?
    private(set) var isLoading = false
    private(set) var startingNodeID: String?
    var errorMessage: String?

    @ObservationIgnored private let service: any CurriculumServiceProtocol

    init(service: any CurriculumServiceProtocol) {
        self.service = service
    }

    var recommendedStage: CurriculumStageProgress? {
        guard let overview else { return nil }
        return overview.stages.first { $0.stage.id == overview.recommendedStageID }
    }

    var currentFocus: CurriculumNode? {
        guard let overview else { return nil }
        if let activeID = overview.activeNodeID {
            return node(id: activeID)?.node
        }
        return overview.recommendedNextNodes.first
    }

    func node(id: String) -> CurriculumNodeProgress? {
        overview?.stages.lazy.flatMap(\.nodes).first { $0.node.id == id }
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            overview = try await service.getMyCurriculum()
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    func startNode(id: String) async {
        startingNodeID = id
        errorMessage = nil
        defer { startingNodeID = nil }
        do {
            overview = try await service.startNode(id: id)
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    func clear() {
        overview = nil
        errorMessage = nil
        isLoading = false
        startingNodeID = nil
    }

    private func readableMessage(for error: Error) -> String {
        if let localizedError = error as? LocalizedError,
           let description = localizedError.errorDescription
        {
            return description
        }
        return "The curriculum could not be loaded."
    }
}
