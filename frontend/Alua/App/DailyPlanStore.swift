import Foundation
import Observation

@MainActor
@Observable
final class DailyPlanStore {
    private(set) var plan: DailyPlan?
    private(set) var isLoading = false
    var errorMessage: String?

    @ObservationIgnored private let service: any DailyPlanServiceProtocol
    @ObservationIgnored private let widgetSyncService: (any WidgetSyncServiceProtocol)?
    @ObservationIgnored private var requestGeneration = 0

    init(service: any DailyPlanServiceProtocol, widgetSyncService: (any WidgetSyncServiceProtocol)? = nil) {
        self.service = service
        self.widgetSyncService = widgetSyncService
    }

    func loadToday() async {
        await perform { try await service.getToday(timezone: TimeZone.current.identifier) }
    }

    func ensureToday() async {
        guard plan == nil, !isLoading else { return }
        await perform { try await service.ensureToday(timezone: TimeZone.current.identifier) }
    }

    func refresh() async {
        await loadToday()
    }

    func clear() {
        requestGeneration += 1
        plan = nil
        isLoading = false
        errorMessage = nil
    }

    private func perform(_ operation: () async throws -> DailyPlan) async {
        guard !isLoading else { return }
        let generation = requestGeneration
        isLoading = true
        errorMessage = nil
        do {
            let loadedPlan = try await operation()
            guard generation == requestGeneration else { return }
            plan = loadedPlan
            if let widgetSyncService { await widgetSyncService.sync() }
        } catch {
            guard generation == requestGeneration else { return }
            errorMessage = (error as? LocalizedError)?.errorDescription
                ?? "Today's study plan could not be loaded."
        }
        if generation == requestGeneration {
            isLoading = false
        }
    }
}
