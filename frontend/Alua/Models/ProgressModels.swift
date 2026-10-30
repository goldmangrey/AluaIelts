import Foundation

enum ProgressDataQuality: String, Codable, Sendable {
    case insufficient, partial, meaningful
}

struct ProgressPeriod: Codable, Sendable {
    let startDate: String
    let endDate: String
    let days: Int
    let timezone: String
    let previousStartDate: String
    let previousEndDate: String

    enum CodingKeys: String, CodingKey {
        case days, timezone
        case startDate = "start_date"
        case endDate = "end_date"
        case previousStartDate = "previous_start_date"
        case previousEndDate = "previous_end_date"
    }
}

struct ProgressSummary: Codable, Sendable {
    let eligibleDays: Int
    let activeDays: Int
    let practiceDays: Int
    let plansGenerated: Int
    let plannedItems: Int
    let completedItems: Int
    let pendingItems: Int
    let fullyCompletedPlanDays: Int
    let estimatedPlannedMinutes: Int
    let estimatedCompletedMinutes: Int
    let assessmentAttempts: Int
    let correctAttempts: Int
    let planCompletionRate: Double?

    enum CodingKeys: String, CodingKey {
        case eligibleDays = "eligible_days"
        case activeDays = "active_days"
        case practiceDays = "practice_days"
        case plansGenerated = "plans_generated"
        case plannedItems = "planned_items"
        case completedItems = "completed_items"
        case pendingItems = "pending_items"
        case fullyCompletedPlanDays = "fully_completed_plan_days"
        case estimatedPlannedMinutes = "estimated_planned_minutes"
        case estimatedCompletedMinutes = "estimated_completed_minutes"
        case assessmentAttempts = "assessment_attempts"
        case correctAttempts = "correct_attempts"
        case planCompletionRate = "plan_completion_rate"
    }
}

struct ProgressDomainAssessment: Codable, Sendable {
    let attempts: Int
    let correct: Int
    let incorrect: Int
    let accuracy: Double?
    let distinctContentPracticed: Int

    enum CodingKeys: String, CodingKey {
        case attempts, correct, incorrect, accuracy
        case distinctContentPracticed = "distinct_content_practiced"
    }
}

struct ProgressDimensionAssessment: Codable, Sendable {
    let dimension: MasteryDimension
    let attempts: Int
    let correct: Int
    let accuracy: Double?
}

struct ProgressAssessmentSummary: Codable, Sendable {
    let attempts: Int
    let correct: Int
    let incorrect: Int
    let accuracy: Double?
    let dataQuality: ProgressDataQuality
    let averageResponseTimeMS: Int?
    let grammar: ProgressDomainAssessment
    let vocabulary: ProgressDomainAssessment
    let dimensions: [ProgressDimensionAssessment]

    enum CodingKeys: String, CodingKey {
        case attempts, correct, incorrect, accuracy, grammar, vocabulary, dimensions
        case dataQuality = "data_quality"
        case averageResponseTimeMS = "average_response_time_ms"
    }
}

struct ProgressDailyPoint: Codable, Sendable, Identifiable {
    let date: String
    let active: Bool
    let practiceActive: Bool
    let learningEvents: Int
    let assessmentAttempts: Int
    let correctAttempts: Int
    let incorrectAttempts: Int
    let grammarAttempts: Int
    let grammarCorrect: Int
    let vocabularyAttempts: Int
    let vocabularyCorrect: Int
    let plannedItems: Int
    let completedItems: Int
    let estimatedPlannedMinutes: Int
    let estimatedCompletedMinutes: Int
    let accuracy: Double?
    var id: String { date }

    enum CodingKeys: String, CodingKey {
        case date, active, accuracy
        case practiceActive = "practice_active"
        case learningEvents = "learning_events"
        case assessmentAttempts = "assessment_attempts"
        case correctAttempts = "correct_attempts"
        case incorrectAttempts = "incorrect_attempts"
        case grammarAttempts = "grammar_attempts"
        case grammarCorrect = "grammar_correct"
        case vocabularyAttempts = "vocabulary_attempts"
        case vocabularyCorrect = "vocabulary_correct"
        case plannedItems = "planned_items"
        case completedItems = "completed_items"
        case estimatedPlannedMinutes = "estimated_planned_minutes"
        case estimatedCompletedMinutes = "estimated_completed_minutes"
    }
}

struct ProgressContentMasteryBreakdown: Codable, Sendable {
    let total: Int
    let assessed: Int
    let unassessed: Int
    let developing: Int
    let competent: Int
    let strong: Int
}

struct ProgressMasterySummary: Codable, Sendable {
    let vocabulary: ProgressContentMasteryBreakdown
    let grammar: ProgressContentMasteryBreakdown
}

struct ProgressConsistency: Codable, Sendable {
    let eligibleDays: Int
    let activeDays: Int
    let practiceDays: Int
    let fullyCompletedPlanDays: Int
    let activityConsistency: Double?

    enum CodingKeys: String, CodingKey {
        case eligibleDays = "eligible_days"
        case activeDays = "active_days"
        case practiceDays = "practice_days"
        case fullyCompletedPlanDays = "fully_completed_plan_days"
        case activityConsistency = "activity_consistency"
    }
}

struct ProgressErrorPattern: Codable, Sendable, Identifiable {
    let tag: String
    let count: Int
    let displayTitle: String
    let explanation: String?
    var id: String { tag }

    enum CodingKeys: String, CodingKey {
        case tag, count, explanation
        case displayTitle = "display_title"
    }
}

struct ProgressComparison: Codable, Sendable {
    let previousDataAvailable: Bool
    let activeDaysDelta: Int
    let practiceDaysDelta: Int
    let assessmentAttemptsDelta: Int
    let completedItemsDelta: Int
    let estimatedCompletedMinutesDelta: Int
    let accuracyPercentagePointsDelta: Double?
    let planCompletionPercentagePointsDelta: Double?
    let accuracyComparisonAvailable: Bool

    enum CodingKeys: String, CodingKey {
        case previousDataAvailable = "previous_data_available"
        case activeDaysDelta = "active_days_delta"
        case practiceDaysDelta = "practice_days_delta"
        case assessmentAttemptsDelta = "assessment_attempts_delta"
        case completedItemsDelta = "completed_items_delta"
        case estimatedCompletedMinutesDelta = "estimated_completed_minutes_delta"
        case accuracyPercentagePointsDelta = "accuracy_percentage_points_delta"
        case planCompletionPercentagePointsDelta = "plan_completion_percentage_points_delta"
        case accuracyComparisonAvailable = "accuracy_comparison_available"
    }
}

struct ProgressSnapshot: Codable, Sendable {
    let period: ProgressPeriod
    let summary: ProgressSummary
    let timeline: [ProgressDailyPoint]
    let assessment: ProgressAssessmentSummary
    let mastery: ProgressMasterySummary
    let consistency: ProgressConsistency
    let recentErrors: [ProgressErrorPattern]
    let strengths: [StudentModelStrength]
    let weaknesses: [StudentModelWeakness]
    let curriculum: StudentModelCurriculum
    let comparison: ProgressComparison
    let generatedAt: Date

    enum CodingKeys: String, CodingKey {
        case period, summary, timeline, assessment, mastery, consistency
        case strengths, weaknesses, curriculum, comparison
        case recentErrors = "recent_errors"
        case generatedAt = "generated_at"
    }
}
