import Foundation

enum DailyPlanItemKind: String, Codable, Sendable {
    case grammarFocus = "grammar_focus"
    case vocabularyLearning = "vocabulary_learning"
    case grammarReview = "grammar_review"
    case vocabularyReview = "vocabulary_review"
    case reinforcement

    var title: String {
        switch self {
        case .grammarFocus: "Grammar focus"
        case .vocabularyLearning: "Vocabulary"
        case .grammarReview: "Grammar review"
        case .vocabularyReview: "Vocabulary review"
        case .reinforcement: "Reinforcement"
        }
    }

    var systemImage: String {
        switch self {
        case .grammarFocus, .grammarReview: "textformat"
        case .vocabularyLearning, .vocabularyReview: "character.book.closed"
        case .reinforcement: "arrow.triangle.2.circlepath"
        }
    }
}

enum DailyPlanContentType: String, Codable, Sendable {
    case grammarLesson = "grammar_lesson"
    case vocabularyItem = "vocabulary_item"
    case curriculumNode = "curriculum_node"
}

enum DailyPlanItemState: String, Codable, Sendable {
    case pending
    case completed
    case skipped
}

enum DailyPlanPriority: String, Codable, Sendable {
    case high
    case normal
    case low
}

enum DailyPlanReason: String, Codable, Sendable {
    case activeCurriculum = "active_curriculum"
    case nextCurriculum = "next_curriculum"
    case weakMastery = "weak_mastery"
    case decliningMastery = "declining_mastery"
    case reinforcement
    case continuity

    var userFacingTitle: String {
        switch self {
        case .activeCurriculum: "Continue your current topic"
        case .nextCurriculum: "Next in your learning path"
        case .weakMastery: "Needs review"
        case .decliningMastery: "Priority review"
        case .reinforcement: "Consolidate recent learning"
        case .continuity: "Build vocabulary continuity"
        }
    }
}

enum DailyPlanStrategy: String, Codable, Sendable {
    case curriculumFirst = "curriculum_first"
    case balanced
    case weaknessFocus = "weakness_focus"
    case reviewHeavy = "review_heavy"
}

enum DailyPlanStatus: String, Codable, Sendable {
    case ready
    case completed
    case noAvailableContent = "no_available_content"
}

struct DailyPlanGenerationContext: Codable, Sendable {
    let declaredLevel: EnglishLevel?
    let recommendedStageID: String?
    let activeNodeID: String?
    let studentModelCoverage: StudentModelCoverageStatus
    let targetMinutes: Int

    enum CodingKeys: String, CodingKey {
        case declaredLevel = "declared_level"
        case recommendedStageID = "recommended_stage_id"
        case activeNodeID = "active_node_id"
        case studentModelCoverage = "student_model_coverage"
        case targetMinutes = "target_minutes"
    }
}

struct DailyPlanItem: Codable, Sendable, Identifiable {
    let itemID: String
    let kind: DailyPlanItemKind
    let contentType: DailyPlanContentType
    let contentID: String
    let curriculumNodeID: String?
    let title: String
    let subtitle: String?
    let cefrLevel: String?
    let estimatedMinutes: Int
    let priority: DailyPlanPriority
    let reason: DailyPlanReason
    let state: DailyPlanItemState
    let sequence: Int

    var id: String { itemID }

    enum CodingKeys: String, CodingKey {
        case kind, title, subtitle, priority, reason, state, sequence
        case itemID = "item_id"
        case contentType = "content_type"
        case contentID = "content_id"
        case curriculumNodeID = "curriculum_node_id"
        case cefrLevel = "cefr_level"
        case estimatedMinutes = "estimated_minutes"
    }
}

struct DailyPlan: Codable, Sendable {
    let planID: String
    let schemaVersion: Int
    let plannerVersion: Int
    let localDate: String
    let timezoneAtGeneration: String
    let targetMinutes: Int
    let estimatedMinutes: Int
    let curriculumVersion: Int
    let vocabularyVersion: Int
    let grammarVersion: Int
    let strategy: DailyPlanStrategy
    let status: DailyPlanStatus
    let items: [DailyPlanItem]
    let vocabulary: DailyPlanVocabularySummary
    let totalItems: Int
    let completedItems: Int
    let remainingItems: Int
    let completedEstimatedMinutes: Int
    let createdAt: Date
    let updatedAt: Date
    let generationContext: DailyPlanGenerationContext

    enum CodingKeys: String, CodingKey {
        case strategy, status, items, vocabulary
        case planID = "plan_id"
        case schemaVersion = "schema_version"
        case plannerVersion = "planner_version"
        case localDate = "local_date"
        case timezoneAtGeneration = "timezone_at_generation"
        case targetMinutes = "target_minutes"
        case estimatedMinutes = "estimated_minutes"
        case curriculumVersion = "curriculum_version"
        case vocabularyVersion = "vocabulary_version"
        case grammarVersion = "grammar_version"
        case totalItems = "total_items"
        case completedItems = "completed_items"
        case remainingItems = "remaining_items"
        case completedEstimatedMinutes = "completed_estimated_minutes"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case generationContext = "generation_context"
    }
}

struct DailyPlanVocabularySummary: Codable, Sendable {
    let packID: String
    let contentVersion: String
    let totalLexicalUnits: Int
    let coreWordCount: Int
    let synonymUpgradeCount: Int
    let phraseChunkCount: Int
    let reviewDueCount: Int

    enum CodingKeys: String, CodingKey {
        case packID = "pack_id"
        case contentVersion = "content_version"
        case totalLexicalUnits = "total_lexical_units"
        case coreWordCount = "core_word_count"
        case synonymUpgradeCount = "synonym_upgrade_count"
        case phraseChunkCount = "phrase_chunk_count"
        case reviewDueCount = "review_due_count"
    }
}
