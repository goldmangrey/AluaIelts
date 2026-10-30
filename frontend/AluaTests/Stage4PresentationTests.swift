import XCTest
import SwiftUI
@testable import Alua

private struct Stage4OfflineAPI: APIClientProtocol {
    func send<Response: Decodable & Sendable>(_ endpoint: APIEndpoint, responseType: Response.Type) async throws -> Response { throw APIError.transport }
}
@MainActor final class Stage4PresentationTests: XCTestCase {
    private func card(_ n: Int, status: String? = "introduced") -> StudyCard {
        StudyCard(id: "item-\(n)", term: n == 18 ? "a wide range of" : "opportunity \(n)", translation_ru: n == 18 ? "широкий спектр" : "возможность \(n)", definition_en: "A large number of different things of the same general type.", example_en: "The city offers a wide range of cultural activities.", example_ru: "Город предлагает широкий выбор культурных мероприятий.", usage_note_ru: "Используйте с существительным во множественном числе.", topic_ids: [1, 2], primary_topic_id: 1, status: status)
    }
    private func snapshot(count: Int = 18, day: Int = 1, available: Bool = true, finished: Bool = false) -> StudySnapshot {
        let days = (1...50).map { n in StudyDay(day: n, title: "Образование и новые возможности", ids: ((n-1)*30..<n*30).map { "item-\($0)" }, processed: n < day || finished ? 30 : n == day ? count : 0, complete: n < day || finished) }
        let total = finished ? 1500 : (day - 1)*30 + count
        return StudySnapshot(version: "test", day: day, title: days[day-1].title, processed: count, available: available, finished: finished, cards: count == 30 ? [] : (count..<30).map { card((day-1)*30 + $0, status: nil) }, review_due: 8, days: days, book: (0..<total).map { card($0, status: $0 < 3 ? "retained" : $0 < 11 ? "review_due" : "introduced") }, topics: ["1": "Образование", "2": "Общество"])
    }
    private func store(_ snapshot: StudySnapshot, uid: String = "test") throws -> StudyStore {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let value = StudyStore(api: Stage4OfflineAPI(), uid: uid, directory: directory)
        try value.save(StudyDisk(snapshot: snapshot))
        addTeardownBlock { try? FileManager.default.removeItem(at: directory) }
        return value
    }
    func testExactlyThreeTabsAndHonestPresentation() {
        XCTAssertEqual(AppTab.allCases.map(\.title), ["Сегодня", "Моя книга", "Прогресс"])
        for count in [0, 10, 18, 20, 30] {
            let s = snapshot(count: count)
            let p = StudyPresentation(snapshot: s)
            XCTAssertEqual(p.processed(s.days[0]), count)
            XCTAssertEqual(p.introduced, count)
            XCTAssertLessThanOrEqual(p.retained, p.introduced)
        }
        let locked = StudyPresentation(snapshot: snapshot(count: 0, day: 2, available: false))
        XCTAssertEqual(locked.displayDay?.day, 1)
        XCTAssertEqual(locked.displayDay.map(locked.processed), 30)
        XCTAssertEqual(locked.completedDays, 1)
        let finished = StudyPresentation(snapshot: snapshot(count: 30, day: 50, available: false, finished: true))
        XCTAssertEqual(finished.completedDays, 50)
        XCTAssertEqual(finished.introduced, 1500)
        XCTAssertEqual(finished.retained, 3)
    }
    func testBookSearchFiltersAndMultitopicIdentity() {
        let cards = [card(18), card(1, status: "review_due"), card(2, status: "retained"), card(3, status: "hidden")]
        XCTAssertEqual(StudyPresentation.words(cards, query: "WIDE RANGE").map(\.id), ["item-18"])
        XCTAssertEqual(StudyPresentation.words(cards, query: "  ШИРОКИЙ  ").map(\.id), ["item-18"])
        for status in ["review_due", "retained", "hidden"] {
            XCTAssertEqual(StudyPresentation.words(cards, filter: status).count, 1)
        }
        XCTAssertEqual(Set(cards.filter { $0.topic_ids.contains(1) }.map(\.id)), Set(cards.filter { $0.topic_ids.contains(2) }.map(\.id)))
    }
    func testResume18AndAllThreeBoundariesWithoutMutatingHistory() async throws {
        let original = try store(snapshot(count: 0))
        for n in 0..<18 { original.record(card(n), action: "next") }
        let restored = StudyStore(api: Stage4OfflineAPI(), uid: original.uid, directory: original.file.deletingLastPathComponent())
        XCTAssertEqual(restored.disk.snapshot?.processed, 18)
        XCTAssertEqual(restored.disk.snapshot?.cards.first?.id, "item-18")
        for n in 18..<30 {
            restored.record(card(n), action: "next")
            if n == 19 { XCTAssertEqual(restored.disk.snapshot?.processed, 20) }
        }
        await restored.sync()
        XCTAssertEqual(restored.disk.queue.count, 30)
        XCTAssertEqual(Set(restored.disk.queue.map(\.event_id)).count, 30)
        XCTAssertEqual(restored.disk.snapshot?.book.count, 30)
        XCTAssertTrue(restored.disk.snapshot?.cards.isEmpty == true)
        let other = StudyStore(api: Stage4OfflineAPI(), uid: "other", directory: original.file.deletingLastPathComponent())
        XCTAssertNil(other.disk.snapshot)
        XCTAssertTrue(other.disk.queue.isEmpty)
    }
    func testRealViewsRenderAtSmallWidthAndAccessibilityType() async throws {
        let value = try store(snapshot())
        try await render(NavigationStack { AluaPage { Text("alua.").font(.largeTitle.bold()); StudyHome(store: value) } }, name: "today", size: CGSize(width: 390, height: 844))
        try await render(NavigationStack { AluaPage { StudyHome(store: value) } }.environment(\.dynamicTypeSize, .accessibility3), name: "today-accessibility", size: CGSize(width: 320, height: 568))
        try await render(NavigationStack { StudyLesson(store: value) }, name: "lesson", size: CGSize(width: 375, height: 812))
        try await render(NavigationStack { StudyBook(store: value) }, name: "book", size: CGSize(width: 390, height: 844))
        try await render(NavigationStack { StudyCardDetail(store: value, original: card(18)) }.environment(\.dynamicTypeSize, .accessibility3), name: "card-accessibility", size: CGSize(width: 320, height: 568))
        try await render(NavigationStack { StudyProgressView(store: value, quality: LearningQualityService(apiClient: Stage4OfflineAPI())) }, name: "progress", size: CGSize(width: 390, height: 844))
        try await render(NavigationStack { StudyReviews(store: value) }, name: "review", size: CGSize(width: 375, height: 812))
    }
    private func render<V: View>(_ view: V, name: String, size: CGSize) async throws {
        let host = UIHostingController(rootView: view.preferredColorScheme(.light).tint(AluaColors.accent))
        let window = UIWindow(frame: CGRect(origin: .zero, size: size))
        window.rootViewController = host; window.makeKeyAndVisible()
        host.view.frame = window.bounds
        try await Task.sleep(for: .milliseconds(300))
        host.view.layoutIfNeeded()
        func checkWidths(_ view: UIView) {
            if let scroll = view as? UIScrollView, scroll.bounds.width > 0 {
                XCTAssertLessThanOrEqual(scroll.contentSize.width, scroll.bounds.width + 1, "Horizontal overflow in \(name)")
            }
            view.subviews.forEach(checkWidths)
        }
        checkWidths(host.view)
        let image = UIGraphicsImageRenderer(size: size).image { _ in host.view.drawHierarchy(in: CGRect(origin: .zero, size: size), afterScreenUpdates: true) }
        let attachment = XCTAttachment(image: image); attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
        try image.pngData()?.write(to: FileManager.default.temporaryDirectory.appendingPathComponent("stage4-\(name).png"))
        window.isHidden = true
    }
}
