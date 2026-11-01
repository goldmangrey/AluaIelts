import Foundation
import SwiftUI
import XCTest
@testable import Alua

struct ReadingOfflineAPI: ReadingAPIProtocol {
    func send<T: Decodable & Sendable>(_ endpoint: APIEndpoint, as type: T.Type) async throws -> T { throw APIError.transport }
    func asset(_ asset: ReadingAsset, cached: Data?) async throws -> Data { throw APIError.transport }
}
struct ReadingTestTokens: AccessTokenProvider {
    let token: String
    func accessToken() async throws -> String? { token }
}

@MainActor final class ReadingTests: XCTestCase {
    var root: URL!
    override func setUpWithError() throws {
        root = FileManager.default.temporaryDirectory.appendingPathComponent("reading-tests-\(UUID())")
    }
    override func tearDownWithError() throws { try? FileManager.default.removeItem(at: root) }
    static var repository: URL { URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent() }
    func realExam(_ eid: String = "cambridge-18-test-01") throws -> ReadingExam {
        let parts = eid.split(separator: "-")
        let file = Self.repository.appendingPathComponent("backend/app/content/reading_v1/exams/cambridge_\(parts[1])/test_\(parts[3]).json")
        return try ReadingCoding.decoder().decode(ReadingExam.self, from: Data(contentsOf: file))
    }
    func attempt(_ exam: ReadingExam, mode: ReadingMode = .passage_practice, remaining: Int = 3600) throws -> ReadingAttempt {
        let payload: [String: Any] = [
            "id": UUID().uuidString, "exam_id": exam.id, "dataset_version": exam.dataset_version,
            "content_hash": String(repeating: "a", count: 64), "content_revision": String(repeating: "b", count: 64),
            "mode": mode.rawValue, "status": "in_progress", "version": 0,
            "started_at": "2026-11-01T00:00:00.000000+00:00", "server_now": "2026-11-01T00:00:00.000000+00:00",
            "deadline_at": mode == .full_exam ? "2026-11-01T01:00:00+00:00" : NSNull(),
            "remaining_seconds": mode == .full_exam ? remaining : NSNull(), "elapsed_seconds": 0,
            "content_status": "needs_review", "not_fully_proofread": true,
            "timing_status": mode == .full_exam ? "server_deadline_enforced" : "untimed_practice",
            "answers": [:], "state": ["current_passage": 1,"annotations":[],"crossed_options":[],"checked_question_ids":[],"reported_active_seconds":[:]]
        ]
        var result = try ReadingCoding.decoder().decode(ReadingAttempt.self, from: JSONSerialization.data(withJSONObject: payload))
        result.exam = exam
        return result
    }
    func seeded(_ api: any ReadingAPIProtocol, server: ReadingAttempt, uid: String = "learner-a") throws -> ReadingStore {
        let exam = try XCTUnwrap(server.exam)
        var disk = ReadingDisk()
        disk.records[server.id] = ReadingRecord(server: server, exam: exam, answers: [:], state: server.state!)
        try ReadingFiles(uid: uid, root: root).save(disk)
        return ReadingStore(api: api, uid: uid, root: root, monitorNetwork: false, automaticallySync: false)
    }
    func testAllAllowedRealExamsDecodeAndHaveConcreteRenderers() throws {
        let catalog = try JSONSerialization.jsonObject(with: Data(contentsOf: Self.repository.appendingPathComponent("docs/ALUA_READING_STAGE2_CATALOG.json"))) as! [String: Any]
        let ids = catalog["enabled"] as! [String]
        XCTAssertEqual(ids.count, 63)
        var seen = Set<ReadingQuestionType>(); var positions = 0
        for eid in ids {
            let exam = try realExam(eid)
            XCTAssertEqual(exam.passages.count, 3, eid); XCTAssertEqual(exam.questions.count, 40, eid)
            for p in exam.passages {
                XCTAssertFalse(p.content.isEmpty, p.id)
                for g in p.question_groups {
                    XCTAssertFalse(g.instructions.isEmpty, g.id)
                    XCTAssertTrue(["structured_text", "source_image_with_inputs"].contains(g.representation), g.id)
                    if g.usesImage || g.type == .diagram_labelling { XCTAssertFalse(g.assets.isEmpty, g.id) }
                    for a in g.assets {
                        // Find by ID within the authoritative manifest's asset filenames.
                        let parts = eid.split(separator: "-")
                        let sourceURL = Self.repository.appendingPathComponent("backend/app/content/reading_v1/exams/cambridge_\(parts[1])/test_\(parts[3]).json")
                        let source = try JSONSerialization.jsonObject(with: Data(contentsOf: sourceURL)) as! [String: Any]
                        let rawAssets = (source["passages"] as! [[String: Any]]).flatMap { ($0["question_groups"] as! [[String: Any]]).flatMap { $0["assets"] as! [[String: Any]] } }
                        let relative = try XCTUnwrap(rawAssets.first { $0["id"] as? String == a.id }?["path"] as? String)
                        let path = Self.repository.appendingPathComponent("backend/app/content/reading_v1/" + relative)
                        XCTAssertTrue(FileManager.default.fileExists(atPath: path.path), a.id)
                        XCTAssertEqual(ReadingFiles.hash(try Data(contentsOf: path)), a.sha256)
                    }
                    for block in g.content_blocks {
                        switch block.type {
                        case .table:
                            let columns = try XCTUnwrap(block.columns, g.id)
                            XCTAssertTrue((block.rows ?? []).allSatisfy { $0.count == columns.count }, g.id)
                        case .image: XCTAssertTrue(g.assets.contains { $0.id == block.asset_id }, g.id)
                        case .rich_text: XCTAssertNotNil(block.segments, g.id)
                        case .list: XCTAssertNotNil(block.items, g.id)
                        case .heading: XCTAssertNotNil(block.text, g.id)
                        }
                    }
                    for q in g.questions {
                        seen.insert(q.type); positions += 1
                        XCTAssertFalse(q.prompt.isEmpty, q.id)
                        let renderable = q.answer_input_type == .text || !g.options(for: q).isEmpty || (g.usesImage && !g.assets.isEmpty)
                        XCTAssertTrue(renderable, "\(eid) / \(q.id): missing supported answer control")
                    }
                }
            }
        }
        XCTAssertEqual(positions, 2520); XCTAssertEqual(seen, Set(ReadingQuestionType.allCases))
        XCTAssertEqual(try realExam("cambridge-12-test-05").source_test_number, 5)
    }
    func testUnicodeCodepointsAreNotUTF16OrGraphemes() throws {
        let text = "A 🧑🏽‍💻 cafe\u{301} — ‘quote’ 🇰🇿"
        for quote in ["🧑🏽‍💻", "e\u{301}", "‘quote’", "🇰🇿"] {
            let range = (text as NSString).range(of: quote)
            let cp = try XCTUnwrap(ReadingTextRange.codepoints(range, in: text))
            XCTAssertEqual(cp.quote, quote)
            XCTAssertEqual(ReadingTextRange.utf16(start: cp.start, end: cp.end, quote: quote, in: text), range)
        }
        XCTAssertNil(ReadingTextRange.codepoints(NSRange(location: 3, length: 1), in: text))
        XCTAssertNil(ReadingTextRange.utf16(start: 0, end: 4, quote: "wrong", in: text))
    }
    func testOfflineAnswersFirstAndFortiethResumeWithDurableUUIDsAndState() async throws {
        let exam = try realExam(), server = try attempt(exam)
        let s = try seeded(ReadingOfflineAPI(), server: server)
        let opened1 = await s.open(server.id); XCTAssertTrue(opened1)
        s.edit(exam.questions.first!.id, answer: "first")
        s.edit(exam.questions.last!.id, answer: "fortieth")
        s.edit(exam.questions.first!.id, answer: "new first")
        s.selectQuestion(exam.questions.last!)
        s.updateUI { $0.passageAnchors[exam.passages[0].id] = "anchor-7"; $0.bookmarks.insert(exam.questions[0].id); $0.detent = "large" }
        s.setPreferences(theme: .sepia, size: 24)
        let events = s.active!.queue.map(\.id)
        await s.sync()
        let r = ReadingStore(api: ReadingOfflineAPI(), uid: "learner-a", root: root, monitorNetwork: false, automaticallySync: false)
        let opened2 = await r.open(server.id); XCTAssertTrue(opened2)
        XCTAssertEqual(r.active?.answers[exam.questions.first!.id], "new first")
        XCTAssertEqual(r.active?.answers[exam.questions.last!.id], "fortieth")
        XCTAssertEqual(r.active?.queue.map(\.id), events)
        XCTAssertEqual(r.active?.ui.questionID, exam.questions.last?.id)
        XCTAssertEqual(r.active?.ui.detent, "large"); XCTAssertEqual(r.preferences.theme, .sepia)
        let other = ReadingStore(api: ReadingOfflineAPI(), uid: "learner-b", root: root, monitorNetwork: false)
        XCTAssertTrue(other.disk.records.isEmpty)
        s.deactivate(); XCTAssertNil(s.active)
        try ReadingFiles.clearSynchronizedCaches(root: root)
        let sameLearner = ReadingStore(api: ReadingOfflineAPI(), uid: "learner-a", root: root, monitorNetwork: false, automaticallySync: false)
        XCTAssertFalse(sameLearner.disk.records.isEmpty)
        let differentLearner = ReadingStore(api: ReadingOfflineAPI(), uid: "learner-b", root: root, monitorNetwork: false)
        XCTAssertTrue(differentLearner.disk.records.isEmpty)
        try ReadingFiles.clearAll(root: root)
        XCTAssertFalse(FileManager.default.fileExists(atPath: root.path))
    }
    func testLostAcknowledgementReplaysExactPayloadAndDoesNotOverwriteNewerLocalAnswer() async throws {
        let exam = try realExam(); let server = try attempt(exam)
        let api = ReadingReplayAPI(server: server, loseFirstAck: true)
        let s = try seeded(api, server: server)
        let opened3 = await s.open(server.id); XCTAssertTrue(opened3)
        let qid = exam.questions[0].id
        s.edit(qid, answer: "old")
        await s.sync()
        let first = try XCTUnwrap(s.active?.queue.first)
        XCTAssertEqual(first.expectedVersion, 0)
        s.edit(qid, answer: "latest")
        await s.sync()
        XCTAssertTrue(s.active!.queue.isEmpty)
        XCTAssertEqual(s.active?.answers[qid], "latest")
        XCTAssertEqual(s.active?.server.answers?[qid], "latest")
        let bodies = await api.received
        XCTAssertGreaterThanOrEqual(bodies.count, 3)
        XCTAssertEqual(bodies[0], bodies[1])
    }
    func testVersionConflictIsPausedUntilExplicitResolution() async throws {
        let exam = try realExam(); let original = try attempt(exam)
        let api = ReadingReplayAPI(server: original)
        let s = try seeded(api, server: original)
        let opened4 = await s.open(original.id); XCTAssertTrue(opened4)
        let qid = exam.questions[0].id
        await api.externalAnswer(qid, "other device")
        s.edit(qid, answer: "local unsent")
        await s.refresh() // Reconnect must not rebase this unsent event onto the newer version.
        await s.sync()
        XCTAssertTrue(s.active?.conflict == true)
        XCTAssertEqual(s.active?.answers[qid], "local unsent")
        XCTAssertEqual(s.active?.server.answers?[qid], "other device")
        let count = await api.received.count
        await s.sync()
        let countAfterRetry = await api.received.count; XCTAssertEqual(countAfterRetry, count)
        s.resolveConflict(keepLocal: true)
        await s.sync()
        XCTAssertEqual(s.active?.server.answers?[qid], "local unsent")
        XCTAssertFalse(s.active!.unaccepted.isEmpty)
    }
    func testColdRestartDoesNotInventFullExamTimeAndTerminalKeepsUnacceptedAnswers() async throws {
        let exam = try realExam(), initial = try attempt(exam, mode: .full_exam, remaining: 1)
        let api = ReadingReplayAPI(server: initial)
        let s = try seeded(api, server: initial)
        XCTAssertNil(s.remainingSeconds)
        let opened5 = await s.open(initial.id); XCTAssertTrue(opened5); XCTAssertNotNil(s.remainingSeconds)
        s.edit(exam.questions[0].id, answer: "offline")
        await api.expire()
        await s.sync()
        XCTAssertEqual(s.active?.server.status, "expired")
        XCTAssertEqual(s.active?.excludedLocalAnswers[exam.questions[0].id], "offline")
        XCTAssertFalse(s.active!.unaccepted.isEmpty)
        XCTAssertFalse(s.canEdit)
    }
    func testRenderingAtSmallWidthAndAccessibility() async throws {
        let exam = try realExam(), initial = try attempt(exam)
        let s = try seeded(ReadingOfflineAPI(), server: initial)
        _ = await s.open(initial.id)
        let view = NavigationStack { ReadingQuestionPanel(store: s, expanded: true, onExpand: {}) }
            .environment(\.dynamicTypeSize, .accessibility2)
        let host = UIHostingController(rootView: view)
        host.view.frame = CGRect(x: 0, y: 0, width: 320, height: 568)
        host.view.layoutIfNeeded()
        XCTAssertFalse(host.view.bounds.isEmpty)
        let passage = UIHostingController(rootView: ReadingPassageView(store: s, passage: exam.passages[0]))
        passage.view.frame = host.view.frame; passage.view.layoutIfNeeded()
        XCTAssertFalse(passage.view.bounds.isEmpty)
    }
    func testHighlightPersistsAcrossFontChangesAndRestart() async throws {
        var exam = try realExam()
        let text = "A 🧑🏽‍💻 cafe\u{301} — ‘quote’ 🇰🇿"
        exam.passages[0].content[1].text = text
        let initial = try attempt(exam)
        let s = try seeded(ReadingOfflineAPI(), server: initial)
        _ = await s.open(initial.id)
        let range = (text as NSString).range(of: "🧑🏽‍💻 cafe\u{301}")
        s.highlight(passage: exam.passages[0], block: 1, range: range, color: "yellow")
        s.setPreferences(theme: .sepia, size: 27)
        let restored = ReadingStore(api: ReadingOfflineAPI(), uid: "learner-a", root: root, monitorNetwork: false, automaticallySync: false)
        _ = await restored.open(initial.id)
        let annotation = try XCTUnwrap(restored.active?.state.annotations.first)
        XCTAssertEqual(annotation.content_hash, initial.content_hash)
        XCTAssertEqual(ReadingTextRange.utf16(start: annotation.start, end: annotation.end, quote: annotation.quote, in: text), range)
        restored.highlight(passage: exam.passages[0], block: 1, range: range, color: nil)
        XCTAssertTrue(restored.active!.state.annotations.isEmpty)
    }
    func testUnreadableDiskIsPreservedInsteadOfOverwritten() throws {
        let files = ReadingFiles(uid: "learner-a", root: root)
        try FileManager.default.createDirectory(at: files.directory, withIntermediateDirectories: true)
        let bad = Data("interrupted old format".utf8)
        try bad.write(to: files.directory.appendingPathComponent("attempts.json"))
        let s = ReadingStore(api: ReadingOfflineAPI(), uid: "learner-a", root: root, monitorNetwork: false)
        XCTAssertTrue(s.diskError)
        s.setPreferences(theme: .sepia)
        let backups = try FileManager.default.contentsOfDirectory(at: files.directory, includingPropertiesForKeys: nil).filter { $0.lastPathComponent.hasPrefix("unreadable-") }
        XCTAssertEqual(backups.count, 1)
        XCTAssertEqual(try Data(contentsOf: backups[0]), bad)
        XCTAssertEqual(try files.load().preferences.theme, .sepia)
    }
    func testRealLocalBackendEndToEnd() async throws {
        let file = URL(fileURLWithPath: "/tmp/alua-reading-stage3-contract.json")
        guard let data = try? Data(contentsOf: file) else { throw XCTSkip("Run frontend/scripts/check_reading.py for isolated PostgreSQL + HTTP integration") }
        let config = try JSONSerialization.jsonObject(with: data) as! [String: String]
        let base = URL(string: config["base_url"]!)!
        let tokens = ReadingTestTokens(token: config["token"]!)
        let api = ReadingAPI(client: APIClient(baseURL: base, tokenProvider: tokens), baseURL: base, tokens: tokens)
        let s = ReadingStore(api: api, uid: config["learner"]!, root: root, monitorNetwork: false, automaticallySync: false)
        await s.loadLibrary()
        XCTAssertEqual(s.books.first?.book_number, 21)
        XCTAssertEqual(s.books.reduce(0) { $0 + $1.available.count }, 63)
        XCTAssertEqual(s.books.first { $0.book_number == 12 }?.available.map(\.source_test_number), [5,6,7,8])
        let opened6 = await s.start(exam: "cambridge-18-test-01", mode: .full_exam, passage: nil); XCTAssertTrue(opened6)
        let fullID = try XCTUnwrap(s.activeID)
        let exam = try XCTUnwrap(s.active?.exam)
        XCTAssertEqual(exam.questions.count, 40)
        s.edit(exam.questions[0].id, answer: "lettuces")
        s.edit(exam.questions[39].id, answer: "unanswered example")
        await s.sync()
        XCTAssertEqual(s.active?.server.answers?[exam.questions[0].id], "lettuces")
        s.submit(); s.submit()
        XCTAssertEqual(s.active?.queue.filter { $0.kind == .submit }.count, 1)
        await s.sync()
        XCTAssertEqual(s.active?.result?.raw_score, 1)
        XCTAssertEqual(s.active?.result?.total_questions, 40)
        XCTAssertNil(s.active?.result?.estimated_band)
        let restarted = ReadingStore(api: api, uid: config["learner"]!, root: root, monitorNetwork: false, automaticallySync: false)
        let opened7 = await restarted.open(fullID); XCTAssertTrue(opened7)
        XCTAssertEqual(restarted.active?.result?.positions.count, 40)
        XCTAssertFalse(restarted.canEdit)
        let opened8 = await s.start(exam: "cambridge-08-test-01", mode: .passage_practice, passage: 1); XCTAssertTrue(opened8)
        let image = try XCTUnwrap(s.active?.exam.assets.first)
        XCTAssertNotNil(s.files.asset(image))
        let bytes = try await api.asset(image, cached: s.files.asset(image))
        XCTAssertEqual(ReadingFiles.hash(bytes), image.sha256) // authenticated 304 path
        let qid = s.active!.exam.questions[0].id
        s.edit(qid, answer: "test"); await s.sync(); s.check([qid]); await s.sync()
        XCTAssertTrue(s.active!.state.checked_question_ids.contains(qid))
        XCTAssertFalse(s.active!.checked!.positions.isEmpty)
        let second = s.active!.exam.questions[1].id
        s.check([second]); await s.sync()
        XCTAssertTrue(s.active!.checkedPositions.contains { $0.question_id == qid })
        XCTAssertTrue(s.active!.checkedPositions.contains { $0.question_id == second })
        let before = s.active!.answers[qid]; s.edit(qid, answer: "changed")
        XCTAssertEqual(s.active!.answers[qid], before)
        s.submit(); await s.sync()
        XCTAssertNil(s.active?.result?.estimated_band)
        XCTAssertEqual(s.active?.result?.per_passage.count, 1)
    }
}

private actor ReadingReplayAPI: ReadingAPIProtocol {
    var server: ReadingAttempt
    var received: [Data] = []
    var replies: [UUID: ReadingAttempt] = [:]
    var loseFirstAck: Bool
    init(server: ReadingAttempt, loseFirstAck: Bool = false) { self.server = server; self.loseFirstAck = loseFirstAck }
    func externalAnswer(_ qid: String, _ value: String) { server.version += 1; server.answers?[qid] = value }
    func expire() { server.status = "expired"; server.remaining_seconds = 0; server.version += 1 }
    func send<T: Decodable & Sendable>(_ endpoint: APIEndpoint, as type: T.Type) async throws -> T {
        if let body = endpoint.body {
            let encoder = ReadingCoding.encoder(); encoder.outputFormatting = .sortedKeys
            let data = try encoder.encode(body); received.append(data)
            let event = try ReadingCoding.decoder().decode(ReadingMutationBody.self, from: data)
            if let replay = replies[event.event_id] { return try decode(replay, as: type) }
            if server.terminal { var reply = server; reply.mutation_applied = false; return try decode(reply, as: type) }
            guard event.expected_version == server.version else { throw APIError.server(statusCode: 409, backendCode: "reading_version_conflict", message: "Conflict") }
            if let answer = event.answer { server.answers?[endpoint.path.components(separatedBy: "/").last!] = answer }
            if let answers = event.answers { server.answers?.merge(answers) { _, new in new } }
            if let p = event.current_passage { server.state?.current_passage = p }
            if let a = event.annotations { server.state?.annotations = a }
            server.version += 1; replies[event.event_id] = server
            if loseFirstAck { loseFirstAck = false; throw APIError.transport }
        }
        return try decode(server, as: type)
    }
    private func decode<T: Decodable>(_ value: ReadingAttempt, as type: T.Type) throws -> T {
        try ReadingCoding.decoder().decode(T.self, from: ReadingCoding.encoder().encode(value))
    }
    func asset(_ asset: ReadingAsset, cached: Data?) async throws -> Data { throw APIError.transport }
}
