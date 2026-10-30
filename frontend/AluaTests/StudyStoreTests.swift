import XCTest
@testable import Alua

private struct OfflineStudyAPI: APIClientProtocol {
    func send<Response: Decodable & Sendable>(_ endpoint: APIEndpoint, responseType: Response.Type) async throws -> Response {
        throw APIError.transport
    }
}
@MainActor final class StudyStoreTests: XCTestCase {
    func testOfflineQueueAndResumeAreDurableAndLearnerScoped() async throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let api = OfflineStudyAPI()
        let store = StudyStore(api: api, uid: "one", directory: folder)
        let cards = (0..<30).map { n in
            StudyCard(id: "card-\(n)", term: "term-\(n)", translation_ru: "значение-\(n)", definition_en: "meaning", example_en: "Example.", example_ru: "Пример.", usage_note_ru: "", topic_ids: [1], primary_topic_id: 1)
        }
        try store.save(StudyDisk(snapshot: StudySnapshot(version: "test", day: 1, title: "Test", processed: 0, available: true, finished: false, cards: cards, review_due: 0, days: [], book: [], topics: [:])))
        for card in cards.prefix(10) { store.record(card, action: "next") }
        let ids = store.disk.queue.map(\.event_id)
        await store.sync()
        XCTAssertEqual(store.disk.queue.count, 10)
        let restarted = StudyStore(api: api, uid: "one", directory: folder)
        XCTAssertEqual(restarted.disk.snapshot?.processed, 10)
        XCTAssertEqual(restarted.disk.snapshot?.cards.first?.id, "card-10")
        XCTAssertEqual(restarted.disk.queue.map(\.event_id), ids)
        let other = StudyStore(api: api, uid: "two", directory: folder)
        XCTAssertNil(other.disk.snapshot)
        XCTAssertTrue(other.disk.queue.isEmpty)
    }
}

private actor ReplayStudyAPI: APIClientProtocol {
    var received: [UUID] = []
    var fail = true
    let snapshot: StudySnapshot
    init(snapshot: StudySnapshot) { self.snapshot = snapshot }
    func send<Response: Decodable & Sendable>(_ endpoint: APIEndpoint, responseType: Response.Type) async throws -> Response {
        if endpoint.path.hasSuffix("actions"), let body = endpoint.body {
            let answer = try JSONDecoder().decode(StudyAnswer.self, from: JSONEncoder().encode(body))
            received.append(answer.event_id)
            if fail { fail = false; throw APIError.transport }
            return try JSONDecoder().decode(Response.self, from: Data("{\"saved\":true}".utf8))
        }
        return try JSONDecoder().decode(Response.self, from: JSONEncoder().encode(snapshot))
    }
}
extension StudyStoreTests {
    func testRetryUsesOriginalEventIDAfterLostAcknowledgement() async throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let card = StudyCard(id: "one", term: "one", translation_ru: "один", definition_en: "number", example_en: "One.", example_ru: "Один.", usage_note_ru: "", topic_ids: [1], primary_topic_id: 1)
        let snapshot = StudySnapshot(version: "test", day: 1, title: "Test", processed: 1, available: true, finished: false, cards: [], review_due: 0, days: [], book: [card], topics: [:])
        let api = ReplayStudyAPI(snapshot: snapshot)
        let store = StudyStore(api: api, uid: "one", directory: folder)
        store.record(card, action: "next")
        let id = try XCTUnwrap(store.disk.queue.first?.event_id)
        await store.sync()
        XCTAssertEqual(store.disk.queue.count, 1)
        let restored = StudyStore(api: api, uid: "one", directory: folder)
        await restored.sync()
        XCTAssertTrue(restored.disk.queue.isEmpty)
        let received = await api.received
        XCTAssertEqual(received, [id, id])
    }
}
