import Foundation

enum AIProgressLanguage: String, Codable, Sendable {
    case en, ru
}

struct AIProgressInsight: Codable, Sendable, Identifiable {
    let title: String
    let statement: String
    let supportingFactIDs: [String]
    let severity: String
    var id: String { "\(title)-\(statement)" }
    enum CodingKeys: String, CodingKey {
        case title, statement, severity
        case supportingFactIDs = "supporting_fact_ids"
    }
}

struct AIProgressRecommendation: Codable, Sendable, Identifiable {
    let title: String
    let recommendation: String
    let reason: String
    let supportingFactIDs: [String]
    var id: String { "\(title)-\(recommendation)" }
    enum CodingKeys: String, CodingKey {
        case title, recommendation, reason
        case supportingFactIDs = "supporting_fact_ids"
    }
}

struct AIProgressDataLimitation: Codable, Sendable, Identifiable {
    let statement: String
    var id: String { statement }
}

struct AIProgressReport: Codable, Sendable {
    let headline: String
    let summary: String
    let highlights: [AIProgressInsight]
    let areasToWorkOn: [AIProgressInsight]
    let recommendations: [AIProgressRecommendation]
    let dataLimitations: [AIProgressDataLimitation]
    enum CodingKeys: String, CodingKey {
        case headline, summary, highlights, recommendations
        case areasToWorkOn = "areas_to_work_on"
        case dataLimitations = "data_limitations"
    }
}

struct AIProgressReportResponse: Codable, Sendable {
    let report: AIProgressReport
    let periodDays: Int
    let timezone: String
    let language: AIProgressLanguage
    let generatedAt: Date
    enum CodingKeys: String, CodingKey {
        case report, timezone, language
        case periodDays = "period_days"
        case generatedAt = "generated_at"
    }
}

struct AIProgressChatConversation: Codable, Sendable {
    let conversationID: String
    let periodDays: Int
    let timezone: String
    let language: AIProgressLanguage
    let status: String
    let createdAt: Date
    let updatedAt: Date
    enum CodingKeys: String, CodingKey {
        case timezone, language, status
        case conversationID = "conversation_id"
        case periodDays = "period_days"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct AIProgressChatMessage: Codable, Sendable, Identifiable {
    let messageID: String
    let role: String
    let content: String
    let createdAt: Date
    let supportingFactIDs: [String]
    var id: String { messageID }
    enum CodingKeys: String, CodingKey {
        case role, content
        case messageID = "message_id"
        case createdAt = "created_at"
        case supportingFactIDs = "supporting_fact_ids"
    }
}

struct AIProgressChatAnswer: Codable, Sendable {
    let answer: String
    let supportingFactIDs: [String]
    let limitations: [String]
    let suggestedFollowups: [String]
    enum CodingKeys: String, CodingKey {
        case answer, limitations
        case supportingFactIDs = "supporting_fact_ids"
        case suggestedFollowups = "suggested_followups"
    }
}

struct AIProgressConversationResponse: Codable, Sendable {
    let conversation: AIProgressChatConversation
    let messages: [AIProgressChatMessage]
}

struct AIProgressChatResponse: Codable, Sendable {
    let message: AIProgressChatMessage
    let answer: AIProgressChatAnswer
}
