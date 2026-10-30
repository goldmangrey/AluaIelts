import Foundation

/// Optional v5 extension. The old learner/partner payloads and keys remain intact.
struct GlanceWidgetSnapshot: Codable, Sendable, Equatable {
    let learnerID: String
    let generationID: String
    let confirmedAt: Date
    let validUntil: Date
    let cardID: String?
    let term: String?
    let day: Int
    let processed: Int
    let finished: Bool
    let isLocal: Bool

    func isCurrent(at date: Date) -> Bool {
        !learnerID.isEmpty && (1...50).contains(day) && (0...30).contains(processed)
        && confirmedAt <= date.addingTimeInterval(300) && date < validUntil
        && date.timeIntervalSince(confirmedAt) < 86_400
    }
    func url(at date: Date) -> URL? {
        guard isCurrent(at: date) else { return URL(string: "alua://review") }
        guard let cardID, term?.isEmpty == false, !isLocal else { return URL(string: "alua://today") }
        var components = URLComponents()
        components.scheme = "alua"; components.host = "review"; components.path = "/item/\(cardID)"
        components.queryItems = [
            .init(name: "learner", value: learnerID),
            .init(name: "generation", value: generationID),
            .init(name: "expires", value: String(Int(validUntil.timeIntervalSince1970)))
        ]
        return components.url
    }
}
