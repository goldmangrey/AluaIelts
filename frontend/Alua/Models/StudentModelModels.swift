import Foundation

enum StudentModelCoverageStatus: String, Codable, Sendable {
    case insufficient
    case partial
    case meaningful

    var title: String { rawValue.capitalized }
}

struct StudentModelCurriculum: Codable, Sendable {
    let declaredLevel: EnglishLevel?
    let recommendedStageID: String?
    let recommendedStageTitle: String?
    let activeNodeID: String?

    enum CodingKeys: String, CodingKey {
        case declaredLevel = "declared_level"
        case recommendedStageID = "recommended_stage_id"
        case recommendedStageTitle = "recommended_stage_title"
        case activeNodeID = "active_node_id"
    }
}

struct StudentModelMasteryOverview: Codable, Sendable {
    let assessedSkillCount: Int
    let vocabularyAssessedItemCount: Int
    let grammarAssessedLessonCount: Int
    let vocabularyLevel: MasteryLevel
    let grammarLevel: MasteryLevel

    enum CodingKeys: String, CodingKey {
        case assessedSkillCount = "assessed_skill_count"
        case vocabularyAssessedItemCount = "vocabulary_assessed_item_count"
        case grammarAssessedLessonCount = "grammar_assessed_lesson_count"
        case vocabularyLevel = "vocabulary_level"
        case grammarLevel = "grammar_level"
    }
}

struct StudentModelStrength: Codable, Sendable, Identifiable {
    let contentType: MasteryContentType
    let contentID: String
    let dimension: MasteryDimension
    let level: MasteryLevel
    let score: Double
    let confidence: Double
    var id: String { "\(contentType.rawValue)-\(contentID)-\(dimension.rawValue)" }

    enum CodingKeys: String, CodingKey {
        case dimension, level, score, confidence
        case contentType = "content_type"
        case contentID = "content_id"
    }
}

struct StudentModelWeakness: Codable, Sendable, Identifiable {
    let contentType: MasteryContentType
    let contentID: String
    let dimension: MasteryDimension
    let score: Double
    let confidence: Double
    var id: String { "\(contentType.rawValue)-\(contentID)-\(dimension.rawValue)" }

    enum CodingKeys: String, CodingKey {
        case dimension, score, confidence
        case contentType = "content_type"
        case contentID = "content_id"
    }
}

struct StudentModelErrorTag: Codable, Sendable, Identifiable {
    let tag: String
    let count: Int
    var id: String { tag }
}

struct StudentModelDataQuality: Codable, Sendable {
    let assessmentEvidenceCount: Int
    let assessedVocabularyItems: Int
    let assessedGrammarLessons: Int
    let coverageStatus: StudentModelCoverageStatus

    enum CodingKeys: String, CodingKey {
        case assessmentEvidenceCount = "assessment_evidence_count"
        case assessedVocabularyItems = "assessed_vocabulary_items"
        case assessedGrammarLessons = "assessed_grammar_lessons"
        case coverageStatus = "coverage_status"
    }
}

struct StudentModelSnapshot: Codable, Sendable {
    let userID: String
    let generatedAt: Date
    let curriculum: StudentModelCurriculum
    let mastery: StudentModelMasteryOverview
    let strengths: [StudentModelStrength]
    let weaknesses: [StudentModelWeakness]
    let recentErrorTags: [StudentModelErrorTag]
    let dataQuality: StudentModelDataQuality

    enum CodingKeys: String, CodingKey {
        case curriculum, mastery, strengths, weaknesses
        case userID = "user_id"
        case generatedAt = "generated_at"
        case recentErrorTags = "recent_error_tags"
        case dataQuality = "data_quality"
    }
}
