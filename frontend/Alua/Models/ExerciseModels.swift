import Foundation

enum ExerciseType: String, Codable, Sendable {
    case vocabularyMeaningMCQ = "vocabulary_meaning_mcq"
    case vocabularyRecall = "vocabulary_recall"
    case vocabularyCollocationMCQ = "vocabulary_collocation_mcq"
    case vocabularyContextGap = "vocabulary_context_gap"
    case grammarRuleMCQ = "grammar_rule_mcq"
    case grammarFormChoice = "grammar_form_choice"
    case grammarErrorCorrection = "grammar_error_correction"
    case grammarContrastMCQ = "grammar_contrast_mcq"
}

enum ExerciseSessionStatus: String, Codable, Sendable { case active, completed }
enum ExerciseItemState: String, Codable, Sendable { case unanswered, answered }

struct ExerciseOption: Codable, Sendable, Identifiable, Hashable {
    let id: String
    let text: String
}

struct ExerciseAttemptFeedback: Codable, Sendable {
    let attemptID: UUID
    let exerciseID: String
    let isCorrect: Bool
    let outcome: Double
    let correctAnswerDisplay: String
    let explanation: String
    let errorTags: [String]

    enum CodingKeys: String, CodingKey {
        case outcome, explanation
        case attemptID = "attempt_id"
        case exerciseID = "exercise_id"
        case isCorrect = "is_correct"
        case correctAnswerDisplay = "correct_answer_display"
        case errorTags = "error_tags"
    }
}

struct ExercisePublicItem: Codable, Sendable, Identifiable {
    let exerciseID: String
    let exerciseType: ExerciseType
    let contentType: DailyPlanContentType
    let contentID: String
    let curriculumNodeID: String?
    let instruction: String
    let prompt: String
    let options: [ExerciseOption]
    let sequence: Int
    let state: ExerciseItemState
    let result: ExerciseAttemptFeedback?
    var id: String { exerciseID }

    enum CodingKeys: String, CodingKey {
        case instruction, prompt, options, sequence, state, result
        case exerciseID = "exercise_id"
        case exerciseType = "exercise_type"
        case contentType = "content_type"
        case contentID = "content_id"
        case curriculumNodeID = "curriculum_node_id"
    }
}

struct ExerciseSessionProgress: Codable, Sendable {
    let answered: Int
    let total: Int
    let correct: Int
}

struct ExerciseSession: Codable, Sendable {
    let sessionID: String
    let schemaVersion: Int
    let engineVersion: Int
    let dailyPlanDate: String
    let dailyPlanItemID: String
    let contentType: DailyPlanContentType
    let contentID: String
    let curriculumNodeID: String?
    let planItemKind: DailyPlanItemKind
    let status: ExerciseSessionStatus
    let exercises: [ExercisePublicItem]
    let progress: ExerciseSessionProgress
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case status, exercises, progress
        case sessionID = "session_id"
        case schemaVersion = "schema_version"
        case engineVersion = "engine_version"
        case dailyPlanDate = "daily_plan_date"
        case dailyPlanItemID = "daily_plan_item_id"
        case contentType = "content_type"
        case contentID = "content_id"
        case curriculumNodeID = "curriculum_node_id"
        case planItemKind = "plan_item_kind"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct ExerciseAttemptResult: Codable, Sendable {
    let attemptID: UUID
    let exerciseID: String
    let isCorrect: Bool
    let outcome: Double
    let correctAnswerDisplay: String
    let explanation: String
    let errorTags: [String]
    let sessionProgress: ExerciseSessionProgress
    let sessionStatus: ExerciseSessionStatus
    let dailyPlanItemCompleted: Bool

    enum CodingKeys: String, CodingKey {
        case outcome, explanation
        case attemptID = "attempt_id"
        case exerciseID = "exercise_id"
        case isCorrect = "is_correct"
        case correctAnswerDisplay = "correct_answer_display"
        case errorTags = "error_tags"
        case sessionProgress = "session_progress"
        case sessionStatus = "session_status"
        case dailyPlanItemCompleted = "daily_plan_item_completed"
    }
}

