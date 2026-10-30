import Foundation
import WidgetKit

struct AluaWidgetEntry: TimelineEntry {
    let date: Date
    let snapshot: WidgetSnapshotEnvelope?
    var isExpired: Bool {
        guard let snapshot else { return false }
        return date >= snapshot.validUntil
    }
    var isTodayStale: Bool {
        guard let snapshot else { return false }
        if isExpired { return true }
        let formatter = DateFormatter()
        formatter.calendar = .current
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        let today = formatter.string(from: date)
        let learnerIsStale = snapshot.learner.map { $0.localDate != today } ?? false
        let partnerIsStale = snapshot.partner.map { $0.localDate != today } ?? false
        return learnerIsStale || partnerIsStale
    }
    var vocabularyCard: WidgetVocabularySnapshot? {
        guard let snapshot, let cards = snapshot.learner?.vocabularyCards, !cards.isEmpty else { return nil }
        let slot = max(0, Int(date.timeIntervalSince(snapshot.validFrom) / 3_600))
        return cards[slot % cards.count]
    }
    var grammarCard: WidgetGrammarSnapshot? {
        guard let snapshot, let cards = snapshot.learner?.grammarCards, !cards.isEmpty else { return nil }
        let slot = max(0, Int(date.timeIntervalSince(snapshot.validFrom) / 14_400))
        return cards[slot % cards.count]
    }
}

struct AluaWidgetProvider: TimelineProvider {
    private let storage = WidgetSnapshotStorage()
    func placeholder(in context: Context) -> AluaWidgetEntry { .init(date: .now, snapshot: nil) }
    func getSnapshot(in context: Context, completion: @escaping (AluaWidgetEntry) -> Void) {
        completion(.init(date: .now, snapshot: storage.read()))
    }
    func getTimeline(in context: Context, completion: @escaping (Timeline<AluaWidgetEntry>) -> Void) {
        let now = Date()
        let snapshot = storage.read()
        let horizon = min(snapshot?.validUntil ?? now.addingTimeInterval(86_400), now.addingTimeInterval(86_400))
        let midnight = Calendar.current.nextDate(after: now, matching: DateComponents(hour: 0, minute: 5), matchingPolicy: .nextTime) ?? now.addingTimeInterval(3_600)
        var entries = [AluaWidgetEntry(date: now, snapshot: snapshot)]
        var next = Calendar.current.date(byAdding: .minute, value: 30, to: now) ?? horizon
        while next <= horizon { entries.append(.init(date: next, snapshot: snapshot)); next = Calendar.current.date(byAdding: .minute, value: 30, to: next) ?? horizon.addingTimeInterval(1) }
        completion(Timeline(entries: entries, policy: .after(min(horizon, midnight))))
    }
}
