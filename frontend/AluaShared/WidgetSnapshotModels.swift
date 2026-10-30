import Foundation

struct WidgetSnapshotEnvelope: Codable, Sendable {
    let schemaVersion: Int
    let generationID: String
    let generatedAt: Date
    let validFrom: Date
    let validUntil: Date
    let userMode: String
    let learner: LearnerWidgetSnapshot?
    let partner: PartnerWidgetSnapshot?
    var glance: GlanceWidgetSnapshot? = nil
    var isSupported: Bool { schemaVersion == 5 && validUntil > validFrom }
    enum CodingKeys: String, CodingKey {
        case learner, partner, glance
        case schemaVersion = "schema_version"
        case generationID = "generation_id"
        case generatedAt = "generated_at"
        case validFrom = "valid_from"
        case validUntil = "valid_until"
        case userMode = "user_mode"
    }
}

struct LearnerWidgetSnapshot: Codable, Sendable {
    let displayName: String?
    let localDate: String
    let packID: String
    let contentVersion: String
    let packSchemaVersion: Int
    let today: WidgetTodaySnapshot?
    let vocabularyCards: [WidgetVocabularySnapshot]
    let grammarCards: [WidgetGrammarSnapshot]
    let practice: WidgetPracticeSnapshot?
    enum CodingKeys: String, CodingKey {
        case today, practice
        case vocabularyCards = "vocabulary_cards"
        case grammarCards = "grammar_cards"
        case displayName = "display_name"
        case localDate = "local_date"
        case packID = "pack_id"
        case contentVersion = "content_version"
        case packSchemaVersion = "pack_schema_version"
    }
}

struct WidgetTodaySnapshot: Codable, Sendable {
    let completedItems: Int
    let totalItems: Int
    let estimatedPlannedMinutes: Int
    let estimatedCompletedMinutes: Int
    let currentFocus: String?
    let grammarItems: Int
    let vocabularyItems: Int
    let reviewItems: Int
    var isComplete: Bool { totalItems > 0 && completedItems == totalItems }
    enum CodingKeys: String, CodingKey {
        case completedItems = "completed_items"; case totalItems = "total_items"
        case estimatedPlannedMinutes = "estimated_planned_minutes"
        case estimatedCompletedMinutes = "estimated_completed_minutes"
        case currentFocus = "current_focus"; case grammarItems = "grammar_items"
        case vocabularyItems = "vocabulary_items"; case reviewItems = "review_items"
    }
}

struct WidgetVocabularySnapshot: Codable, Sendable {
    let contentID: String; let term: String; let translationRU: String
    let ipa: String?; let cefr: String?; let definitionEN: String?
    let example: String?; let partOfSpeech: String?
    enum CodingKeys: String, CodingKey {
        case term, ipa, example, cefr; case contentID = "content_id"; case definitionEN = "definition_en"
        case translationRU = "translation_ru"; case partOfSpeech = "part_of_speech"
    }
}

struct WidgetGrammarSnapshot: Codable, Sendable {
    let contentID: String; let displayTitle: String; let shortTitle: String
    let formula: String; let supportRU: String?; let example: String?
    enum CodingKeys: String, CodingKey {
        case formula, example; case contentID = "content_id"; case displayTitle = "display_title"
        case shortTitle = "short_title"; case supportRU = "support_ru"
    }
}

struct WidgetPracticeSnapshot: Codable, Sendable {
    let localDate: String; let dailyPlanItemID: String; let title: String; let itemKind: String
    let existingSessionID: String?
    let questionCount: Int?; let remainingCount: Int?; let estimatedMinutes: Int
    let hasExistingSession: Bool
    enum CodingKeys: String, CodingKey {
        case title; case localDate = "local_date"; case dailyPlanItemID = "daily_plan_item_id"
        case itemKind = "item_kind"; case existingSessionID = "existing_session_id"
        case questionCount = "question_count"; case remainingCount = "remaining_count"
        case estimatedMinutes = "estimated_minutes"; case hasExistingSession = "has_existing_session"
    }
}

struct PartnerWidgetPermissions: Codable, Sendable {
    let dailyActivity: Bool; let progressAnalytics: Bool
    enum CodingKeys: String, CodingKey { case dailyActivity = "daily_activity"; case progressAnalytics = "progress_analytics" }
}

struct PartnerWidgetSnapshot: Codable, Sendable {
    let learnerDisplayName: String; let localDate: String; let activeToday: Bool?
    let completedItems: Int?; let totalItems: Int?; let estimatedPlannedMinutes: Int?
    let estimatedCompletedMinutes: Int?; let currentFocus: String?; let activeDays7: Int?
    let lastActivityAt: Date?; let permissions: PartnerWidgetPermissions
    enum CodingKeys: String, CodingKey {
        case permissions; case learnerDisplayName = "learner_display_name"; case localDate = "local_date"
        case activeToday = "active_today"; case completedItems = "completed_items"; case totalItems = "total_items"
        case estimatedPlannedMinutes = "estimated_planned_minutes"; case estimatedCompletedMinutes = "estimated_completed_minutes"
        case currentFocus = "current_focus"; case activeDays7 = "active_days_7"; case lastActivityAt = "last_activity_at"
    }
}
