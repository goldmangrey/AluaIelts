import Foundation
import Observation

@MainActor @Observable
final class PartnerStore {
    private(set) var status: PartnerStatus?
    private(set) var dashboard: PartnerDashboardSnapshot?
    private(set) var invite: PartnerInvite?
    var selectedPeriod: ProgressPeriodSelection = .seven
    private(set) var isLoading = false
    private(set) var isMutating = false
    var errorMessage: String?
    @ObservationIgnored private let service: any PartnerServiceProtocol
    @ObservationIgnored private let widgetSyncService: (any WidgetSyncServiceProtocol)?
    init(service: any PartnerServiceProtocol, widgetSyncService: (any WidgetSyncServiceProtocol)? = nil) { self.service = service; self.widgetSyncService = widgetSyncService }

    func loadStatus() async { guard status == nil, !isLoading else { return }; await refresh() }
    func refresh() async {
        guard !isLoading else { return }; isLoading = true; errorMessage = nil; defer { isLoading = false }
        do { status = try await service.getStatus(); if status?.monitoringLearner != nil { try await loadDashboardValue() } else { dashboard = nil }; if let widgetSyncService { await widgetSyncService.sync() } } catch { errorMessage = message(error) }
    }
    func loadDashboard() async { do { try await loadDashboardValue() } catch { errorMessage = message(error) } }
    func changePeriod(_ period: ProgressPeriodSelection) async { selectedPeriod = period; await loadDashboard() }
    func createInvite() async { await mutate { self.invite = try await self.service.createInvite() } }
    func acceptInvite(_ code: String) async { await mutate { self.status = try await self.service.acceptInvite(code: code); try await self.loadDashboardValue() } }
    func updateSharing(_ settings: PartnerSharingSettings) async { await mutate { self.status = try await self.service.updateSharing(settings); if let widgetSyncService { await widgetSyncService.sync() } } }
    func revoke() async { await mutate { self.status = try await self.service.revokeRelationship(); self.dashboard = nil; self.invite = nil; self.widgetSyncService?.clear() } }
    func clear() { status = nil; dashboard = nil; invite = nil; selectedPeriod = .seven; isLoading = false; isMutating = false; errorMessage = nil }
    private func loadDashboardValue() async throws { dashboard = try await service.getDashboard(days: selectedPeriod.rawValue, timezone: TimeZone.current.identifier) }
    private func mutate(_ work: () async throws -> Void) async { guard !isMutating else { return }; isMutating = true; errorMessage = nil; defer { isMutating = false }; do { try await work() } catch { errorMessage = message(error) } }
    private func message(_ error: Error) -> String { (error as? LocalizedError)?.errorDescription ?? "Partner action could not be completed." }
}
