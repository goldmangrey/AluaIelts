import Foundation

enum DeepLink: Hashable, Sendable, Identifiable {
    case today
    case vocabulary(String)
    case grammar(String)
    case practice(localDate: String, itemID: String)
    case review(sessionID: String)
    case studyReview
    case quickRecall(itemID: String, learnerID: String, generationID: String, expiresAt: Date)
    case partner
    var id: String {
        switch self {
        case .studyReview: "study-review"
        case let .quickRecall(item, learner, generation, _): "recall:\(learner):\(item):\(generation)"
        case .today: "today"
        case .partner: "partner"
        case let .vocabulary(id): "vocabulary:\(id)"
        case let .grammar(id): "grammar:\(id)"
        case let .practice(date, id): "practice:\(date):\(id)"
        case let .review(id): "review:\(id)"
        }
    }

    init?(url: URL) {
        guard url.scheme?.lowercased() == "alua", let host = url.host?.lowercased() else { return nil }
        let parts = url.pathComponents.filter { $0 != "/" }.map { $0.removingPercentEncoding ?? $0 }
        if host == "today", parts.isEmpty { self = .today }
        else if host == "partner", parts.isEmpty { self = .partner }
        else if host == "vocabulary", parts.count == 1, !parts[0].isEmpty { self = .vocabulary(parts[0]) }
        else if host == "grammar", parts.count == 1, !parts[0].isEmpty { self = .grammar(parts[0]) }
        else if host == "practice", parts.count == 2, !parts[0].isEmpty, !parts[1].isEmpty { self = .practice(localDate: parts[0], itemID: parts[1]) }
        else if host == "review", parts.isEmpty { self = .studyReview }
        else if host == "review", parts.count == 2, parts[0] == "item" {
            guard let query = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems,
                  query.count == 3, Set(query.map(\.name)) == ["learner", "generation", "expires"],
                  let learner = query.first(where: { $0.name == "learner" })?.value,
                  !learner.isEmpty, learner.count <= 128,
                  let generation = query.first(where: { $0.name == "generation" })?.value,
                  UUID(uuidString: generation) != nil,
                  let raw = query.first(where: { $0.name == "expires" })?.value,
                  let expiry = TimeInterval(raw), expiry.isFinite,
                  !parts[1].isEmpty, parts[1].count <= 180 else { return nil }
            self = .quickRecall(itemID: parts[1], learnerID: learner, generationID: generation,
                                expiresAt: Date(timeIntervalSince1970: expiry))
        }
        else if host == "review", parts.count == 2, parts[0] == "session", !parts[1].isEmpty { self = .review(sessionID: parts[1]) }
        else { return nil }
    }
}
