import Foundation
import WidgetKit

protocol WidgetSyncServiceProtocol: Sendable {
    func sync() async
    @MainActor func clear()
    @MainActor func activateLearner(_ uid: String)
    @MainActor func publishStudy(learnerID: String, snapshot: StudySnapshot, confirmedAt: Date?, pending: [StudyAnswer])
}
extension WidgetSyncServiceProtocol {
    @MainActor func activateLearner(_ uid: String) {}
    @MainActor func publishStudy(learnerID: String, snapshot: StudySnapshot, confirmedAt: Date?, pending: [StudyAnswer]) {}
}

@MainActor
final class WidgetSyncService: WidgetSyncServiceProtocol, @unchecked Sendable {
    private let apiClient: any APIClientProtocol
    private let storage: WidgetSnapshotStorage
    private var isSyncing = false
    private var generation = UUID()
    private var activeLearner: String?
    private var glance: GlanceWidgetSnapshot?
    private var legacy: WidgetSnapshotEnvelope?
    private var lastFetch = Date.distantPast
    private var lastReload = Date.distantPast
    private var reloadTask: Task<Void, Never>?
    init(apiClient: any APIClientProtocol, storage: WidgetSnapshotStorage = WidgetSnapshotStorage()) {
        self.apiClient = apiClient; self.storage = storage
        let cached = storage.read()
        self.glance = cached?.glance; self.legacy = cached
    }
    func activateLearner(_ uid: String) {
        guard activeLearner != uid else { return }
        if let saved = storage.read(), saved.glance?.learnerID == uid {
            // Preserve the tapped generation across a cold launch of the same authenticated learner.
            generation = UUID(); isSyncing = false; activeLearner = uid
            glance = saved.glance; legacy = saved
        } else { clear(); activeLearner = uid }
    }
    func sync() async {
        guard !isSyncing, Date.now.timeIntervalSince(lastFetch) >= 60 else { return }
        let startedGeneration = generation
        isSyncing = true
        defer { if generation == startedGeneration { isSyncing = false } }
        do {
            var snapshot = try await apiClient.send(
                APIEndpoint(path: "/api/v1/widgets/snapshot", queryItems: [.init(name: "timezone", value: "Asia/Almaty")], requiresAuthentication: true),
                responseType: WidgetSnapshotEnvelope.self
            )
            guard generation == startedGeneration, !Task.isCancelled else { return }
            lastFetch = .now; legacy = snapshot; snapshot.glance = glance
            if storage.activate(snapshot) { requestReload() }
        } catch { /* Keep only the last confirmed, time-limited data. */ }
    }
    func publishStudy(learnerID uid: String, snapshot: StudySnapshot, confirmedAt: Date?, pending: [StudyAnswer]) {
        guard activeLearner == uid else { return } // An old async request cannot repopulate a new profile.
        guard let confirmedAt else { return }
        let now = Date.now
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "Asia/Almaty")!
        let midnight = calendar.startOfDay(for: confirmedAt).addingTimeInterval(86_400)
        let expiry = min(confirmedAt.addingTimeInterval(86_400), midnight)
        let presentation = StudyPresentation(snapshot: snapshot)
        let day = presentation.displayDay
        // Unacknowledged answers may change due/hidden state. Show an explicitly local status instead.
        let due = pending.isEmpty ? snapshot.book.first { $0.status == "review_due" } : nil
        let candidate = GlanceWidgetSnapshot(learnerID: uid, generationID: UUID().uuidString,
            confirmedAt: confirmedAt, validUntil: expiry, cardID: due?.id, term: due?.term,
            day: day?.day ?? snapshot.day, processed: day.map(presentation.processed) ?? snapshot.processed,
            finished: snapshot.finished, isLocal: !pending.isEmpty)
        if let old = glance, old.learnerID == uid, old.cardID == candidate.cardID,
           old.term == candidate.term, old.day == candidate.day, old.processed == candidate.processed,
           old.finished == candidate.finished, old.isLocal == candidate.isLocal,
           now.timeIntervalSince(old.confirmedAt) < 300, old.isCurrent(at: now) { return }
        glance = candidate
        var envelope = legacy ?? WidgetSnapshotEnvelope(schemaVersion: 5, generationID: candidate.generationID,
            generatedAt: now, validFrom: now, validUntil: now.addingTimeInterval(86_400),
            userMode: "learner", learner: nil, partner: nil)
        envelope.glance = candidate
        if storage.activate(envelope) { requestReload() }
    }
    private func requestReload() {
        let delay = 30 - Date.now.timeIntervalSince(lastReload)
        if delay <= 0 { reload(); return }
        guard reloadTask == nil else { return }
        reloadTask = Task { [weak self] in
            do { try await Task.sleep(for: .seconds(delay)) } catch { return }
            self?.reloadTask = nil; self?.reload()
        }
    }
    private func reload() {
        lastReload = .now
        WidgetCenter.shared.reloadAllTimelines()
    }
    func clear() {
        generation = UUID(); isSyncing = false; activeLearner = nil
        glance = nil; legacy = nil; lastFetch = .distantPast
        reloadTask?.cancel(); reloadTask = nil
        storage.clear(); reload()
    }
}
