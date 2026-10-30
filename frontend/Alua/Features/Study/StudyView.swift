import SwiftUI

struct StudyCard: Codable, Sendable, Identifiable {
    let id: String
    let term: String
    let translation_ru: String
    let definition_en: String
    let example_en: String
    let example_ru: String
    let usage_note_ru: String
    let topic_ids: [Int]
    let primary_topic_id: Int
    var status: String?
}
struct StudyDay: Codable, Sendable, Identifiable {
    let day: Int; let title: String; let ids: [String]; let processed: Int; let complete: Bool
    var id: Int { day }
}
struct StudySnapshot: Codable, Sendable {
    let version: String; let day: Int; let title: String
    var processed: Int; let available: Bool; let finished: Bool
    var cards: [StudyCard]; let review_due: Int
    let days: [StudyDay]; var book: [StudyCard]; let topics: [String: String]
}
struct StudyAnswer: Codable, Sendable {
    let learner_id: String
    let event_id: UUID; let item_id: String; let action: String
    let answer: String?; let comment: String
}
struct StudyDisk: Codable {
    var snapshot: StudySnapshot?
    var queue: [StudyAnswer] = []
    var confirmedAt: Date? = nil
}

@MainActor @Observable final class StudyStore {
    var disk: StudyDisk
    var error: String?
    var syncing = false
    let api: any APIClientProtocol
    let file: URL
    let uid: String
    let widgetSyncService: (any WidgetSyncServiceProtocol)?
    var storageReadable = true
    init(api: any APIClientProtocol, uid: String, directory: URL? = nil, widgetSyncService: (any WidgetSyncServiceProtocol)? = nil) {
        self.api = api
        self.uid = uid
        self.widgetSyncService = widgetSyncService
        let folder = directory ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        file = folder.appendingPathComponent("study-\(uid).json")
        do {
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            if FileManager.default.fileExists(atPath: file.path) {
                disk = try JSONDecoder().decode(StudyDisk.self, from: Data(contentsOf: file))
            } else { disk = StudyDisk() }
        } catch {
            disk = StudyDisk()
            storageReadable = false
            self.error = "Не удалось прочитать сохранённый урок: \(error.localizedDescription)"
        }
    }
    func save(_ value: StudyDisk) throws {
        try JSONEncoder().encode(value).write(to: file, options: .atomic)
        disk = value
        if let snapshot = value.snapshot {
            widgetSyncService?.publishStudy(learnerID: uid, snapshot: snapshot, confirmedAt: value.confirmedAt, pending: value.queue)
        }
    }
    func record(_ card: StudyCard, action: String, answer: String? = nil, comment: String = "") {
        guard storageReadable else { return }
        guard disk.queue.count < 100 else { error = "Подключитесь к сети для отправки ответов"; return }
        var next = disk
        next.queue.append(StudyAnswer(learner_id: uid, event_id: UUID(), item_id: card.id, action: action, answer: answer, comment: comment))
        if ["next", "known", "unknown", "hide"].contains(action), next.snapshot?.cards.first?.id == card.id {
            next.snapshot?.cards.removeFirst()
            next.snapshot?.processed += 1
            var saved = card
            saved.status = action == "hide" ? "hidden" : action == "known" ? "known_pending_review" : "introduced"
            if next.snapshot?.book.contains(where: { $0.id == card.id }) == false { next.snapshot?.book.append(saved) }
        }
        do { try save(next); error = nil } catch { self.error = "Ответ не сохранён: \(error.localizedDescription)" }
    }
    func sync() async {
        guard storageReadable, !syncing else { return }
        syncing = true
        defer { syncing = false }
        do {
            while let first = disk.queue.first {
                struct Ack: Decodable, Sendable { let saved: Bool }
                _ = try await api.send(APIEndpoint(path: "/api/v1/study/actions", method: .post, body: first, requiresAuthentication: true), responseType: Ack.self)
                var next = disk; next.queue.removeFirst(); try save(next)
            }
            let snapshot = try await api.send(APIEndpoint(path: "/api/v1/study/today", queryItems: [URLQueryItem(name: "learner_id", value: uid)], requiresAuthentication: true), responseType: StudySnapshot.self)
            if disk.queue.isEmpty { var next = disk; next.snapshot = snapshot; next.confirmedAt = .now; try save(next) }; error = nil
        } catch { self.error = "Нет синхронизации. Сохранено ответов: \(disk.queue.count). \(error.localizedDescription)" }
    }
}

