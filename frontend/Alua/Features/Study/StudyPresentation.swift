import Foundation

/// Read-only projection of the existing Stage 3 payload and pending actions.
/// No scheduling, persistence or mastery calculation belongs here.
struct StudyPresentation {
    let snapshot: StudySnapshot
    var queue: [StudyAnswer] = []
    var courseIDs: Set<String> { Set(snapshot.days.flatMap(\.ids)) }
    func processed(_ day: StudyDay) -> Int {
        let persisted = snapshot.days.first { $0.day == day.day }?.processed ?? day.processed
        return min(30, max(persisted, day.day == snapshot.day ? snapshot.processed : persisted))
    }
    var displayDay: StudyDay? {
        if !snapshot.available && !snapshot.finished && snapshot.processed == 0 && snapshot.day > 1 {
            return snapshot.days.first { $0.day == snapshot.day - 1 }
        }
        return snapshot.days.first { $0.day == snapshot.day }
    }
    var completedDays: Int { snapshot.days.filter { $0.complete || processed($0) == 30 }.count }
    var introduced: Int { Set(snapshot.book.map(\.id)).intersection(courseIDs).count }
    var retained: Int { snapshot.book.filter { $0.status == "retained" && courseIDs.contains($0.id) }.count }
    var due: Int { snapshot.review_due }
    static func words(_ cards: [StudyCard], query: String = "", filter: String = "all") -> [StudyCard] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        return cards.filter {
            (filter == "all" || $0.status == filter) &&
            (q.isEmpty || ($0.term + " " + $0.translation_ru).localizedCaseInsensitiveContains(q))
        }
    }
    static func status(_ value: String?) -> String {
        switch value {
        case "retained": "Закреплено"
        case "review_due": "Нужно повторить"
        case "hidden": "Скрыто"
        case "known_pending_review": "Ожидает подтверждения"
        default: "Впервые изучено"
        }
    }
}
