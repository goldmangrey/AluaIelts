import CryptoKit
import Foundation

enum ReadingTheme: String, Codable, CaseIterable, Sendable { case light, sepia, dark }
struct ReadingPreferences: Codable, Sendable { var theme: ReadingTheme = .light; var fontSize: Double = 19 }
struct ReadingUIState: Codable, Equatable, Sendable {
    var currentPassage = 1; var questionID: String?; var passageAnchors: [String: String] = [:]
    var questionAnchors: [String: String] = [:]; var detent = "compact"; var bookmarks: Set<String> = []
}
struct ReadingEvent: Codable, Identifiable, Sendable {
    enum Kind: String, Codable, Sendable { case answer, batch, state, check, submit }
    var id = UUID(); var kind: Kind; var expectedVersion: Int?
    var questionID: String?; var answer: String?; var answers: [String: String]?
    var state: ReadingAttemptState?; var questionIDs: [String]?
    var body: ReadingMutationBody {
        ReadingMutationBody(event_id: id, expected_version: expectedVersion ?? 0,
                            answer: answer, answers: answers,
                            current_passage: state?.current_passage, annotations: state?.annotations,
                            crossed_options: state?.crossed_options, question_ids: questionIDs)
    }
    func endpoint(attempt: String) -> APIEndpoint {
        let root = "api/v1/reading/attempts/\(attempt)"
        let path: String; let method: HTTPMethod
        switch kind {
        case .answer: path = root + "/answers/" + (questionID ?? ""); method = .put
        case .batch: path = root + "/sync"; method = .post
        case .state: path = root + "/state"; method = .patch
        case .check: path = root + "/check"; method = .post
        case .submit: path = root + "/submit"; method = .post
        }
        return APIEndpoint(path: path, method: method, body: body, requiresAuthentication: true)
    }
}
struct ReadingRecord: Codable, Identifiable, Sendable {
    var server: ReadingAttempt; var exam: ReadingExam
    var answers: [String: String]; var state: ReadingAttemptState
    var queue: [ReadingEvent] = []; var unaccepted: [ReadingEvent] = []
    var ui = ReadingUIState(); var result: ReadingResult?; var checked: ReadingResult?
    var conflict = false
    var checkedAnswers: [String: ReadingPositionResult]? = nil
    var checkedPositions: [ReadingPositionResult] {
        checkedAnswers.map { $0.values.sorted { $0.number < $1.number } } ?? checked?.positions ?? []
    }
    var id: String { server.id }
    var unanswered: Int { exam.questions.filter { answers[$0.id, default: ""].trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }.count }
    var excludedLocalAnswers: [String: String] {
        guard server.terminal else { return [:] }
        return answers.filter { $0.value != (server.answers?[$0.key] ?? "") }
    }
}
struct ReadingDisk: Codable, Sendable {
    var books: [ReadingBook] = []; var history: [ReadingAttempt] = []
    var records: [String: ReadingRecord] = [:]; var pendingStart: ReadingStart?
    var preferences = ReadingPreferences()
}
struct ReadingFiles: Sendable {
    let directory: URL
    static var root: URL {
        URL.applicationSupportDirectory.appendingPathComponent("Reading-v1", isDirectory: true)
    }
    init(uid: String, root: URL = ReadingFiles.root) {
        directory = root.appendingPathComponent(Self.hash(Data(uid.utf8)), isDirectory: true)
    }
    static func hash(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    func load() throws -> ReadingDisk {
        let file = directory.appendingPathComponent("attempts.json")
        guard FileManager.default.fileExists(atPath: file.path) else { return ReadingDisk() }
        return try ReadingCoding.decoder().decode(ReadingDisk.self, from: Data(contentsOf: file))
    }
    func preserveUnreadableStore() throws {
        let source = directory.appendingPathComponent("attempts.json")
        if FileManager.default.fileExists(atPath: source.path) {
            try FileManager.default.moveItem(at: source, to: directory.appendingPathComponent("unreadable-\(UUID().uuidString).json"))
        }
    }
    func save(_ disk: ReadingDisk) throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try ReadingCoding.encoder().encode(disk).write(to: directory.appendingPathComponent("attempts.json"), options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
    }
    func assetURL(_ a: ReadingAsset) -> URL { directory.appendingPathComponent("assets/\(a.sha256).png") }
    func asset(_ a: ReadingAsset) -> Data? {
        guard let data = try? Data(contentsOf: assetURL(a)), Self.hash(data) == a.sha256 else { return nil }
        return data
    }
    func saveAsset(_ data: Data, asset: ReadingAsset) throws {
        guard Self.hash(data) == asset.sha256 else { throw APIError.decoding }
        try FileManager.default.createDirectory(at: directory.appendingPathComponent("assets"), withIntermediateDirectories: true)
        try data.write(to: assetURL(asset), options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
    }
    static func clearSynchronizedCaches(root: URL = root) throws {
        guard FileManager.default.fileExists(atPath: root.path) else { return }
        for folder in try FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil) {
            let file = folder.appendingPathComponent("attempts.json")
            // Unreadable data and unacknowledged work must survive logout. The UID-hashed
            // directory can only be reopened after that same learner authenticates again.
            guard let bytes = try? Data(contentsOf: file), let disk = try? ReadingCoding.decoder().decode(ReadingDisk.self, from: bytes) else { continue }
            let unsent = disk.pendingStart != nil || disk.records.values.contains { !$0.queue.isEmpty || !$0.unaccepted.isEmpty }
            if !unsent { try FileManager.default.removeItem(at: folder) }
        }
    }
    static func clearAll(root: URL = root) throws {
        if FileManager.default.fileExists(atPath: root.path) { try FileManager.default.removeItem(at: root) }
    }
}

/// Codepoints are Unicode scalars, NOT Swift extended grapheme clusters or UTF-16 units.
enum ReadingTextRange {
    static func codepoints(_ range: NSRange, in text: String) -> (start: Int, end: Int, quote: String)? {
        guard range.location != NSNotFound, range.length > 0 else { return nil }
        var utf16 = 0; var boundaries: [Int: Int] = [0: 0]
        for (index, scalar) in text.unicodeScalars.enumerated() {
            utf16 += scalar.value > 0xFFFF ? 2 : 1
            boundaries[utf16] = index + 1
        }
        guard let start = boundaries[range.location], let end = boundaries[NSMaxRange(range)] else { return nil }
        return (start, end, (text as NSString).substring(with: range))
    }
    static func utf16(start: Int, end: Int, quote: String, in text: String) -> NSRange? {
        let scalars = Array(text.unicodeScalars)
        guard start >= 0, start < end, end <= scalars.count else { return nil }
        let lower = text.unicodeScalars.index(text.unicodeScalars.startIndex, offsetBy: start)
        let upper = text.unicodeScalars.index(text.unicodeScalars.startIndex, offsetBy: end)
        guard String(text.unicodeScalars[lower..<upper]) == quote else { return nil }
        let offset = scalars.prefix(start).reduce(0) { $0 + ($1.value > 0xFFFF ? 2 : 1) }
        let length = scalars[start..<end].reduce(0) { $0 + ($1.value > 0xFFFF ? 2 : 1) }
        return NSRange(location: offset, length: length)
    }
}
