import Foundation

enum LearningEventType: String, Codable, Sendable {
    case curriculumNodeStarted = "curriculum_node_started"
    case grammarLessonOpened = "grammar_lesson_opened"
    case vocabularyTrackOpened = "vocabulary_track_opened"
    case vocabularyItemOpened = "vocabulary_item_opened"
}

enum LearningEventCategory: String, Codable, Sendable {
    case engagement, assessment, review, system
}

enum LearningEventSource: String, Codable, Sendable {
    case iosApp = "ios_app"
    case backend, widget
}

enum LearningContentType: String, Codable, Sendable {
    case curriculumNode = "curriculum_node"
    case grammarLesson = "grammar_lesson"
    case vocabularyTrack = "vocabulary_track"
    case vocabularyItem = "vocabulary_item"
}

struct LearningEvent: Codable, Sendable, Identifiable {
    let eventID: UUID
    let schemaVersion: Int
    let userID: String
    let eventType: LearningEventType
    let category: LearningEventCategory
    let source: LearningEventSource
    let contentType: LearningContentType
    let contentID: String
    let curriculumNodeID: String?
    let clientOccurredAt: Date?
    let serverReceivedAt: Date
    let timezone: String?
    let sessionID: UUID?

    var id: UUID { eventID }

    enum CodingKeys: String, CodingKey {
        case category, source, timezone
        case eventID = "event_id"
        case schemaVersion = "schema_version"
        case userID = "user_id"
        case eventType = "event_type"
        case contentType = "content_type"
        case contentID = "content_id"
        case curriculumNodeID = "curriculum_node_id"
        case clientOccurredAt = "client_occurred_at"
        case serverReceivedAt = "server_received_at"
        case sessionID = "session_id"
    }
}

struct CreateLearningEventRequest: Encodable, Sendable {
    let eventID: UUID
    let schemaVersion = 1
    let eventType: LearningEventType
    let contentID: String
    let curriculumNodeID: String?
    let clientOccurredAt: Date
    let timezone: String
    let sessionID: UUID?

    enum CodingKeys: String, CodingKey {
        case eventID = "event_id"
        case schemaVersion = "schema_version"
        case eventType = "event_type"
        case contentID = "content_id"
        case curriculumNodeID = "curriculum_node_id"
        case clientOccurredAt = "client_occurred_at"
        case timezone
        case sessionID = "session_id"
    }
}

struct LearningEventsResponse: Codable, Sendable {
    let items: [LearningEvent]
    let limit: Int
}
