import Foundation

enum MasteryContentType: String, Codable, Sendable {
    case vocabularyItem = "vocabulary_item"
    case grammarLesson = "grammar_lesson"
}

enum MasteryDimension: String, Codable, Sendable {
    case meaningRecognition = "meaning_recognition"
    case meaningRecall = "meaning_recall"
    case collocation
    case contextualUsage = "contextual_usage"
    case production
    case ruleRecognition = "rule_recognition"
    case formControl = "form_control"
    case errorDetection = "error_detection"
    case contrastSelection = "contrast_selection"

    var title: String {
        rawValue.replacingOccurrences(of: "_", with: " ").capitalized
    }
}

enum MasteryLevel: String, Codable, Sendable {
    case unassessed
    case developing
    case competent
    case strong

    var title: String { rawValue.capitalized }
}

enum MasteryTrend: String, Codable, Sendable {
    case unknown
    case improving
    case stable
    case declining
}

struct MasteryState: Codable, Sendable, Identifiable {
    let stateID: String
    let userID: String
    let contentType: MasteryContentType
    let contentID: String
    let dimension: MasteryDimension
    let score: Double?
    let confidence: Double
    let evidenceCount: Int
    let successfulEvidenceCount: Int
    let failedEvidenceCount: Int
    let weightedSuccessSum: Double
    let weightedEvidenceSum: Double
    let previousScore: Double?
    let lastEvidenceAt: Date
    let lastSuccessAt: Date?
    let lastFailureAt: Date?
    let level: MasteryLevel
    let trend: MasteryTrend
    let errorTagCounts: [String: Int]
    let createdAt: Date
    let updatedAt: Date
    let engineVersion: Int

    var id: String { stateID }

    enum CodingKeys: String, CodingKey {
        case dimension, score, confidence, level, trend
        case stateID = "state_id"
        case userID = "user_id"
        case contentType = "content_type"
        case contentID = "content_id"
        case evidenceCount = "evidence_count"
        case successfulEvidenceCount = "successful_evidence_count"
        case failedEvidenceCount = "failed_evidence_count"
        case weightedSuccessSum = "weighted_success_sum"
        case weightedEvidenceSum = "weighted_evidence_sum"
        case previousScore = "previous_score"
        case lastEvidenceAt = "last_evidence_at"
        case lastSuccessAt = "last_success_at"
        case lastFailureAt = "last_failure_at"
        case errorTagCounts = "error_tag_counts"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case engineVersion = "engine_version"
    }
}

struct MasteryDimensionSummary: Codable, Sendable, Identifiable {
    let dimension: MasteryDimension
    let score: Double?
    let confidence: Double
    let level: MasteryLevel
    let trend: MasteryTrend
    let evidenceCount: Int
    let lastEvidenceAt: Date?

    var id: MasteryDimension { dimension }

    enum CodingKeys: String, CodingKey {
        case dimension, score, confidence, level, trend
        case evidenceCount = "evidence_count"
        case lastEvidenceAt = "last_evidence_at"
    }
}

struct MasteryErrorTagCount: Codable, Sendable, Identifiable {
    let tag: String
    let count: Int
    var id: String { tag }
}

struct ContentMasterySummary: Codable, Sendable {
    let contentType: MasteryContentType
    let contentID: String
    let overallScore: Double?
    let overallConfidence: Double
    let overallLevel: MasteryLevel
    let dimensions: [MasteryDimensionSummary]
    let evidenceCount: Int
    let lastEvidenceAt: Date?
    let topErrorTags: [MasteryErrorTagCount]

    enum CodingKeys: String, CodingKey {
        case dimensions
        case contentType = "content_type"
        case contentID = "content_id"
        case overallScore = "overall_score"
        case overallConfidence = "overall_confidence"
        case overallLevel = "overall_level"
        case evidenceCount = "evidence_count"
        case lastEvidenceAt = "last_evidence_at"
        case topErrorTags = "top_error_tags"
    }
}

struct MasteryStatesResponse: Codable, Sendable {
    let items: [MasteryState]
    let limit: Int
    let offset: Int
}
