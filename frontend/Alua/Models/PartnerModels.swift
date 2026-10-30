import Foundation

struct PartnerSharingSettings: Codable, Sendable, Equatable {
    var shareDailyActivity: Bool = true
    var shareProgressAnalytics: Bool = true
    var shareLearningProfile: Bool = true
    var shareRecentErrorPatterns: Bool = true
    var allowAIProgressAnalysis: Bool = false

    enum CodingKeys: String, CodingKey {
        case shareDailyActivity = "share_daily_activity"
        case shareProgressAnalytics = "share_progress_analytics"
        case shareLearningProfile = "share_learning_profile"
        case shareRecentErrorPatterns = "share_recent_error_patterns"
        case allowAIProgressAnalysis = "allow_ai_progress_analysis"
    }
}

struct PartnerRelationshipSummary: Codable, Sendable {
    let relationshipID: String
    let displayName: String
    let connectedAt: Date
    let sharingSettings: PartnerSharingSettings
    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
        case relationshipID = "relationship_id"
        case connectedAt = "connected_at"
        case sharingSettings = "sharing_settings"
    }
}

struct PartnerStatus: Codable, Sendable {
    let sharingMyProgress: PartnerRelationshipSummary?
    let monitoringLearner: PartnerRelationshipSummary?
    enum CodingKeys: String, CodingKey {
        case sharingMyProgress = "sharing_my_progress"
        case monitoringLearner = "monitoring_learner"
    }
}

struct PartnerInvite: Codable, Sendable {
    let inviteID: String
    let code: String
    let expiresAt: Date
    enum CodingKeys: String, CodingKey {
        case code
        case inviteID = "invite_id"
        case expiresAt = "expires_at"
    }
}

struct PartnerLearnerSummary: Codable, Sendable { let displayName: String
    enum CodingKeys: String, CodingKey { case displayName = "display_name" }
}

struct PartnerTodayActivity: Codable, Sendable {
    let localDate: String
    let hasPlan: Bool
    let targetMinutes: Int?
    let estimatedMinutes: Int?
    let estimatedCompletedMinutes: Int
    let totalItems: Int
    let completedItems: Int
    let remainingItems: Int
    let planStatus: String?
    let currentFocus: String?
    let grammarItems: Int
    let vocabularyItems: Int
    let reviewItems: Int
    enum CodingKeys: String, CodingKey {
        case localDate = "local_date"; case hasPlan = "has_plan"
        case targetMinutes = "target_minutes"; case estimatedMinutes = "estimated_minutes"
        case estimatedCompletedMinutes = "estimated_completed_minutes"
        case totalItems = "total_items"; case completedItems = "completed_items"
        case remainingItems = "remaining_items"; case planStatus = "plan_status"
        case currentFocus = "current_focus"; case grammarItems = "grammar_items"
        case vocabularyItems = "vocabulary_items"; case reviewItems = "review_items"
    }
}

struct PartnerLearningProfile: Codable, Sendable {
    let curriculum: StudentModelCurriculum
    let mastery: StudentModelMasteryOverview
    let strengths: [StudentModelStrength]
    let weaknesses: [StudentModelWeakness]
    let dataQuality: StudentModelDataQuality
    enum CodingKeys: String, CodingKey { case curriculum, mastery, strengths, weaknesses; case dataQuality = "data_quality" }
}

struct PartnerDashboardSnapshot: Codable, Sendable {
    let learner: PartnerLearnerSummary
    let relationshipID: String
    let connectedAt: Date
    let permissions: PartnerSharingSettings
    let todayActivity: PartnerTodayActivity?
    let progress: ProgressSnapshot?
    let learningProfile: PartnerLearningProfile?
    let recentErrors: [ProgressErrorPattern]?
    let generatedAt: Date
    enum CodingKeys: String, CodingKey {
        case learner, permissions, progress
        case relationshipID = "relationship_id"; case connectedAt = "connected_at"
        case todayActivity = "today_activity"; case learningProfile = "learning_profile"
        case recentErrors = "recent_errors"; case generatedAt = "generated_at"
    }
}
