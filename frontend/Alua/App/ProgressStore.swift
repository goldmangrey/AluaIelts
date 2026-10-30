import Foundation
import Observation

enum ProgressPeriodSelection: Int, CaseIterable, Identifiable {
    case seven = 7
    case thirty = 30
    case ninety = 90

    var id: Int { rawValue }
    var title: String { "\(rawValue) Days" }
}

@MainActor
@Observable
final class ProgressStore {
    private(set) var snapshot: ProgressSnapshot?
    var selectedPeriod: ProgressPeriodSelection = .seven
    private(set) var isLoading = false
    var errorMessage: String?

    @ObservationIgnored private let service: any ProgressServiceProtocol

    init(service: any ProgressServiceProtocol) {
        self.service = service
    }

    func load() async {
        guard snapshot == nil, !isLoading else { return }
        await refresh()
    }

    func refresh() async {
        guard !isLoading else { return }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            snapshot = try await service.getProgress(
                days: selectedPeriod.rawValue,
                timezone: TimeZone.current.identifier
            )
        } catch {
            errorMessage = readableMessage(for: error)
        }
    }

    func changePeriod(_ period: ProgressPeriodSelection) async {
        guard selectedPeriod != period else { return }
        selectedPeriod = period
        snapshot = nil
        await refresh()
    }

    func clear() {
        snapshot = nil
        selectedPeriod = .seven
        isLoading = false
        errorMessage = nil
    }

    private func readableMessage(for error: Error) -> String {
        if let localized = error as? LocalizedError,
           let description = localized.errorDescription
        {
            return description
        }
        return "Progress could not be loaded."
    }
}
