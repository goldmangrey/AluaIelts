import Foundation
import Observation

@MainActor
@Observable
final class StudentModelStore {
    private(set) var snapshot: StudentModelSnapshot?
    private(set) var isLoading = false
    var errorMessage: String?

    @ObservationIgnored private let service: any MasteryServiceProtocol

    init(service: any MasteryServiceProtocol) {
        self.service = service
    }

    func load() async {
        guard snapshot == nil else { return }
        await refresh()
    }

    func refresh() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            snapshot = try await service.getStudentModel()
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    func clear() {
        snapshot = nil
        isLoading = false
        errorMessage = nil
    }

    private func readableMessage(for error: Error) -> String {
        if let localized = error as? LocalizedError,
           let description = localized.errorDescription
        {
            return description
        }
        return "Your learning profile could not be loaded."
    }
}
