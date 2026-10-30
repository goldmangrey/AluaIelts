import Foundation

struct WidgetSnapshotStorage: @unchecked Sendable {
    private let defaults: UserDefaults?
    init(defaults: UserDefaults? = UserDefaults(suiteName: AppGroup.identifier)) { self.defaults = defaults }

    func read() -> WidgetSnapshotEnvelope? {
        guard let data = defaults?.data(forKey: WidgetStorageKey.activeGeneration),
              let value = try? Self.decoder.decode(WidgetSnapshotEnvelope.self, from: data),
              value.isSupported,
              Self.hasCurrentContract(value),
              Date().timeIntervalSince(value.generatedAt) < 86_400 else { return nil }
        return value
    }
    @discardableResult func activate(_ snapshot: WidgetSnapshotEnvelope) -> Bool {
        guard snapshot.isSupported, let data = try? Self.encoder.encode(snapshot), let defaults else { return false }
        defaults.set(data, forKey: WidgetStorageKey.nextGeneration)
        guard let staged = defaults.data(forKey: WidgetStorageKey.nextGeneration),
              let verified = try? Self.decoder.decode(WidgetSnapshotEnvelope.self, from: staged),
              verified.generationID == snapshot.generationID, verified.isSupported else { return false }
        defaults.set(staged, forKey: WidgetStorageKey.activeGeneration)
        defaults.set(snapshot.generatedAt, forKey: WidgetStorageKey.lastUpdated)
        defaults.removeObject(forKey: WidgetStorageKey.nextGeneration)
        return true
    }
    func clear() {
        defaults?.removeObject(forKey: WidgetStorageKey.activeGeneration)
        defaults?.removeObject(forKey: WidgetStorageKey.nextGeneration)
        defaults?.removeObject(forKey: WidgetStorageKey.lastUpdated)
    }
    private static let encoder: JSONEncoder = { let value = JSONEncoder(); value.dateEncodingStrategy = .iso8601; return value }()
    private static let decoder: JSONDecoder = { let value = JSONDecoder(); value.dateDecodingStrategy = .iso8601; return value }()
    private static let localDay: DateFormatter = {
        let value = DateFormatter()
        value.calendar = .current
        value.locale = Locale(identifier: "en_US_POSIX")
        value.dateFormat = "yyyy-MM-dd"
        value.timeZone = TimeZone(identifier: "Asia/Almaty")
        return value
    }()
    private static func hasCurrentContract(_ value: WidgetSnapshotEnvelope) -> Bool {
        if value.glance?.isCurrent(at: Date()) == true { return true }
        guard let learner = value.learner else { return value.partner != nil }
        return !learner.packID.isEmpty
            && !learner.contentVersion.isEmpty
            && learner.packSchemaVersion == 2
            && learner.localDate == localDay.string(from: Date())
    }
}
