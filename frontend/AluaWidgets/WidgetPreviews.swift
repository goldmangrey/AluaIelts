#if DEBUG
import WidgetKit

private enum WidgetPreviewFixtures {
    static func learner(completed: Bool) -> WidgetSnapshotEnvelope {
        WidgetSnapshotEnvelope(
            schemaVersion: 5, generationID: UUID().uuidString, generatedAt: .now,
            validFrom: .now, validUntil: .now.addingTimeInterval(86_400), userMode: "learner",
            learner: LearnerWidgetSnapshot(
                displayName: "Alua", localDate: currentDate,
                packID: "preview-pack", contentVersion: "preview-v2", packSchemaVersion: 2,
                today: WidgetTodaySnapshot(
                    completedItems: completed ? 8 : 6, totalItems: 8,
                    estimatedPlannedMinutes: 30, estimatedCompletedMinutes: completed ? 30 : 22,
                    currentFocus: completed ? nil : "Present Perfect",
                    grammarItems: 1, vocabularyItems: 5, reviewItems: 2
                ),
                vocabularyCards: [WidgetVocabularySnapshot(
                    contentID: "vocab_mitigate_v_01", term: "mitigate", translationRU: "смягчать",
                    ipa: "[ˈmɪtɪɡeɪt]", cefr: "B2", definitionEN: "to make something less severe",
                    example: "Public transport can mitigate congestion.", partOfSpeech: "verb"
                )],
                grammarCards: [], practice: nil
            ), partner: nil
        )
    }
    static let partner = WidgetSnapshotEnvelope(
        schemaVersion: 5, generationID: UUID().uuidString, generatedAt: .now,
        validFrom: .now, validUntil: .now.addingTimeInterval(86_400), userMode: "partner", learner: nil,
        partner: PartnerWidgetSnapshot(
            learnerDisplayName: "Alua", localDate: currentDate, activeToday: true,
            completedItems: 6, totalItems: 10, estimatedPlannedMinutes: 40,
            estimatedCompletedMinutes: 24, currentFocus: "Present Perfect",
            activeDays7: 5, lastActivityAt: nil,
            permissions: PartnerWidgetPermissions(dailyActivity: true, progressAnalytics: true)
        )
    )
    static var currentDate: String {
        let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: .now)
    }
}

#Preview("Today", as: .systemSmall) { TodayLearningWidget() } timeline: {
    AluaWidgetEntry(date: .now, snapshot: WidgetPreviewFixtures.learner(completed: false))
}
#Preview("Completed", as: .systemSmall) { TodayLearningWidget() } timeline: {
    AluaWidgetEntry(date: .now, snapshot: WidgetPreviewFixtures.learner(completed: true))
}
#Preview("Partner", as: .systemMedium) { PartnerProgressWidget() } timeline: {
    AluaWidgetEntry(date: .now, snapshot: WidgetPreviewFixtures.partner)
}
#Preview("Empty", as: .systemSmall) { VocabularyWidget() } timeline: {
    AluaWidgetEntry(date: .now, snapshot: nil)
}
#endif
