import Foundation
import UIKit
import UserNotifications

@MainActor
final class VocabularyNotificationService: NSObject, UNUserNotificationCenterDelegate, @unchecked Sendable {
    enum AuthorizationState { case unknown, enabled, denied }
    private var generation = UUID()
    private let center = UNUserNotificationCenter.current()
    private let defaults = UserDefaults.standard
    private let preferenceKey = "vocabulary.reminders.enabled"
    private var routeHandler: (@MainActor @Sendable (URL) -> Void)?
    var remindersEnabled: Bool { defaults.bool(forKey: preferenceKey) }

    override init() { super.init(); center.delegate = self }
    func configureRouteHandler(_ handler: @escaping @MainActor @Sendable (URL) -> Void) { routeHandler = handler }
    func authorizationState() async -> AuthorizationState {
        let settings = await center.notificationSettings()
        switch settings.authorizationStatus {
        case .authorized, .provisional, .ephemeral: return .enabled
        case .denied: return .denied
        default: return .unknown
        }
    }
    func enable() async -> Bool {
        do {
            let granted = try await center.requestAuthorization(options: [.alert, .sound])
            defaults.set(granted, forKey: preferenceKey)
            return granted
        } catch { defaults.set(false, forKey: preferenceKey); return false }
    }
    func disable() {
        generation = UUID()
        defaults.set(false, forKey: preferenceKey)
        center.removeAllPendingNotificationRequests()
        center.removeAllDeliveredNotifications()
    }
    func openSettings() { Task { @MainActor in UIApplication.shared.open(URL(string: UIApplication.openSettingsURLString)!) } }

    func scheduleDailyReminders(for today: VocabularyLearningToday) async {
        guard remindersEnabled else { return }
        let scheduledGeneration = generation
        let obsolete = await center.pendingNotificationRequests()
            .map(\.identifier)
            .filter { $0.hasPrefix("vocab-") }
        guard remindersEnabled, generation == scheduledGeneration, !Task.isCancelled else { return }
        center.removePendingNotificationRequests(withIdentifiers: obsolete)
        let calendar = Calendar.current
        guard let day = Self.dayFormatter.date(from: today.localDate) else { return }
        let middayID = "vocab-midday-\(today.localDate)"
        let eveningID = "vocab-evening-\(today.localDate)"
        let weeklyID = "vocab-weekly-\(today.localDate)"
        let term = today.currentRecall?.lexicalItem.term.uppercased()
        await add(identifier: middayID, date: calendar.date(bySettingHour: 14, minute: 0, second: 0, of: day), title: term ?? "Vocabulary review", body: term == nil ? "Время повторить английские слова" : "Что значит? Время быстрого повторения.", sessionID: today.middaySession.sessionID, generation: scheduledGeneration)
        if calendar.component(.weekday, from: day) == 1 {
            await add(identifier: weeklyID, date: calendar.date(bySettingHour: 20, minute: 0, second: 0, of: day), title: "Weekly vocabulary review", body: "Время вспомнить слова этой недели.", sessionID: today.eveningSession.sessionID, generation: scheduledGeneration)
        } else {
            await add(identifier: eveningID, date: calendar.date(bySettingHour: 20, minute: 0, second: 0, of: day), title: term ?? "Evening review", body: term == nil ? "Время повторить английские слова" : "Что значит? Вечернее повторение.", sessionID: today.eveningSession.sessionID, generation: scheduledGeneration)
        }
    }

    #if DEBUG
    func scheduleDebugTest(today: VocabularyLearningToday?) async -> Bool {
        let scheduledGeneration = generation
        guard await authorizationState() == .enabled, generation == scheduledGeneration else { return false }
        let sessionID = today?.currentRecall?.sessionID ?? today?.middaySession.sessionID
        guard let sessionID else { return false }
        let content = UNMutableNotificationContent()
        content.title = today?.currentRecall?.lexicalItem.term.uppercased() ?? "Vocabulary test"
        content.body = "Что значит? Нажмите для быстрого повторения."
        content.sound = .default
        content.userInfo = ["route": "alua://review/session/\(sessionID)"]
        let identifier = "vocab-debug-test-\(scheduledGeneration)"
        do {
            try await center.add(UNNotificationRequest(identifier: identifier, content: content, trigger: UNTimeIntervalNotificationTrigger(timeInterval: 10, repeats: false)))
            guard generation == scheduledGeneration else {
                center.removePendingNotificationRequests(withIdentifiers: [identifier])
                center.removeDeliveredNotifications(withIdentifiers: [identifier])
                return false
            }
            return true
        }
        catch { return false }
    }
    #endif

    private func add(identifier: String, date: Date?, title: String, body: String, sessionID: String, generation scheduledGeneration: UUID) async {
        guard remindersEnabled, generation == scheduledGeneration, !Task.isCancelled, let date, date > Date() else { return }
        let identifier = "\(identifier)-\(scheduledGeneration)"
        let content = UNMutableNotificationContent(); content.title = title; content.body = body
        content.sound = .default; content.userInfo = ["route": "alua://review/session/\(sessionID)"]
        let components = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute], from: date)
        try? await center.add(UNNotificationRequest(identifier: identifier, content: content, trigger: UNCalendarNotificationTrigger(dateMatching: components, repeats: false)))
        if generation != scheduledGeneration {
            center.removePendingNotificationRequests(withIdentifiers: [identifier])
            center.removeDeliveredNotifications(withIdentifiers: [identifier])
        }
    }
    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) { completionHandler([.banner, .sound]) }
    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
        if let value = response.notification.request.content.userInfo["route"] as? String, let url = URL(string: value) {
            Task { @MainActor [weak self] in self?.routeHandler?(url) }
        }
        completionHandler()
    }
    private static let dayFormatter: DateFormatter = { let value = DateFormatter(); value.locale = Locale(identifier: "en_US_POSIX"); value.calendar = Calendar(identifier: .gregorian); value.dateFormat = "yyyy-MM-dd"; return value }()
}
