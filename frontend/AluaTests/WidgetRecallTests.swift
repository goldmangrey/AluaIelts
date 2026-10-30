import XCTest
@testable import Alua

private struct GlanceOfflineAPI: APIClientProtocol {
    func send<Response: Decodable & Sendable>(_ endpoint: APIEndpoint, responseType: Response.Type) async throws -> Response { throw APIError.transport }
}
@MainActor final class WidgetRecallTests: XCTestCase {
    private func snapshot(status: String = "review_due") -> StudySnapshot {
        let card = StudyCard(id: "src-000181", term: "causal relationship", translation_ru: "причинно-следственная связь", definition_en: "a connection", example_en: "Example.", example_ru: "Пример.", usage_note_ru: "", topic_ids: [1], primary_topic_id: 1, status: status)
        return StudySnapshot(version: "ielts1500-test", day: 1, title: "Причины", processed: 18, available: true, finished: false, cards: [], review_due: 1, days: [StudyDay(day: 1, title: "Причины", ids: [card.id], processed: 18, complete: false)], book: [card], topics: ["1": "Причины"])
    }
    private func storage() -> (WidgetSnapshotStorage, UserDefaults) {
        let name = "stage5-\(UUID())"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        return (WidgetSnapshotStorage(defaults: defaults), defaults)
    }
    func testV5CompatibilityAndConfirmedOnlyPublication() throws {
        let (storage, _) = storage()
        let service = WidgetSyncService(apiClient: GlanceOfflineAPI(), storage: storage)
        service.activateLearner("one")
        service.publishStudy(learnerID: "one", snapshot: snapshot(), confirmedAt: nil, pending: [])
        XCTAssertNil(storage.read())
        service.publishStudy(learnerID: "one", snapshot: snapshot(), confirmedAt: .now, pending: [])
        let envelope = try XCTUnwrap(storage.read())
        XCTAssertEqual(envelope.schemaVersion, 5)
        XCTAssertEqual(envelope.glance?.term, "causal relationship")
        let link = try XCTUnwrap(envelope.glance?.url(at: .now))
        XCTAssertFalse(link.absoluteString.contains("Bearer"))
        guard case let .quickRecall(item, learner, _, _) = DeepLink(url: link) else { return XCTFail("Exact route") }
        XCTAssertEqual(item, "src-000181"); XCTAssertEqual(learner, "one")
        let pending = StudyAnswer(learner_id: "one", event_id: UUID(), item_id: item, action: "hide", answer: nil, comment: "")
        service.publishStudy(learnerID: "one", snapshot: snapshot(), confirmedAt: .now, pending: [pending])
        XCTAssertNil(storage.read()?.glance?.cardID)
        XCTAssertEqual(storage.read()?.glance?.isLocal, true)
        service.activateLearner("two")
        XCTAssertNil(storage.read())
        service.publishStudy(learnerID: "one", snapshot: snapshot(), confirmedAt: .now, pending: [])
        XCTAssertNil(storage.read()) // Late load from an old learner is ignored.
        let old = Data("{\"schema_version\":5,\"generation_id\":\"old\",\"generated_at\":0,\"valid_from\":0,\"valid_until\":1,\"user_mode\":\"learner\"}".utf8)
        XCTAssertNil(try JSONDecoder().decode(WidgetSnapshotEnvelope.self, from: old).glance)
    }
    func testExactCardValidationAndNoEventOnOpening() throws {
        let s = snapshot()
        let now = Date.now
        let source = GlanceWidgetSnapshot(learnerID: "one", generationID: UUID().uuidString, confirmedAt: now, validUntil: now.addingTimeInterval(1000), cardID: s.book[0].id, term: s.book[0].term, day: 1, processed: 18, finished: false, isLocal: false)
        func resolve(_ uid: String = "one", _ state: StudySnapshot? = nil, _ expiry: Date? = nil) -> StudyCard? {
            WidgetRecallResolver.card(itemID: s.book[0].id, learnerID: "one", generationID: source.generationID, expiresAt: expiry ?? source.validUntil, activeLearner: uid, source: source, snapshot: state ?? s, pending: [], now: now)
        }
        XCTAssertEqual(resolve()?.id, s.book[0].id)
        XCTAssertNil(resolve("two"))
        XCTAssertNil(resolve("one", snapshot(status: "hidden")))
        XCTAssertNil(resolve("one", snapshot(status: "retained")))
        XCTAssertNil(resolve("one", nil, now.addingTimeInterval(-1)))
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let store = StudyStore(api: GlanceOfflineAPI(), uid: "one", directory: folder)
        try store.save(StudyDisk(snapshot: s))
        _ = resolve()
        XCTAssertTrue(store.disk.queue.isEmpty)
        XCTAssertEqual(store.disk.snapshot?.processed, 18)
        store.record(s.book[0], action: "review", answer: nil)
        XCTAssertEqual(store.disk.queue.count, 1)
        XCTAssertEqual(store.disk.snapshot?.processed, 18)
        let restored = StudyStore(api: GlanceOfflineAPI(), uid: "one", directory: folder)
        XCTAssertEqual(restored.disk.queue.first?.event_id, store.disk.queue.first?.event_id)
        XCTAssertNil(DeepLink(url: URL(string: "alua://review/item/x?learner=one&learner=two&generation=bad")!))
    }
}
