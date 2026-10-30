import Foundation

enum CurriculumTrack: String, Codable, Sendable, CaseIterable {
    case grammar
    case vocabulary
    case mixed

    var title: String {
        switch self {
        case .grammar: "Grammar"
        case .vocabulary: "Vocabulary"
        case .mixed: "Reinforcement"
        }
    }
}

enum CurriculumNodeType: String, Codable, Sendable {
    case grammarTopic = "grammar_topic"
    case vocabularyTrack = "vocabulary_track"
    case reinforcement
}

enum CurriculumNodeStatus: String, Codable, Sendable {
    case locked
    case available
    case active
    case completed

    var title: String { rawValue.capitalized }

    var systemImage: String {
        switch self {
        case .locked: "lock"
        case .available: "circle"
        case .active: "play.circle.fill"
        case .completed: "checkmark.circle.fill"
        }
    }
}

struct CurriculumNode: Codable, Sendable, Identifiable, Hashable {
    let id: String
    let stageID: String
    let track: CurriculumTrack
    let type: CurriculumNodeType
    let title: String
    let shortTitle: String?
    let description: String
    let order: Int
    let cefrLevel: EnglishLevel
    let estimatedMinutes: Int
    let prerequisites: [String]
    let objectives: [String]
    let contentRefs: [String]
    let tags: [String]
    let required: Bool

    enum CodingKeys: String, CodingKey {
        case id, track, type, title, description, order, prerequisites, objectives, tags, required
        case stageID = "stage_id"
        case shortTitle = "short_title"
        case cefrLevel = "cefr_level"
        case estimatedMinutes = "estimated_minutes"
        case contentRefs = "content_refs"
    }
}

struct CurriculumStage: Codable, Sendable, Identifiable, Hashable {
    let id: String
    let order: Int
    let title: String
    let subtitle: String
    let cefrFrom: EnglishLevel
    let cefrTo: EnglishLevel
    let description: String
    let targetIELTSRange: String?
    let estimatedWeeks: Int?
    let nodes: [CurriculumNode]

    enum CodingKeys: String, CodingKey {
        case id, order, title, subtitle, description, nodes
        case cefrFrom = "cefr_from"
        case cefrTo = "cefr_to"
        case targetIELTSRange = "target_ielts_range"
        case estimatedWeeks = "estimated_weeks"
    }
}

struct CurriculumProgram: Codable, Sendable {
    let id: String
    let version: Int
    let versionLabel: String
    let title: String
    let description: String
    let stages: [CurriculumStage]

    enum CodingKeys: String, CodingKey {
        case id, version, title, description, stages
        case versionLabel = "version_label"
    }
}

struct UserCurriculumState: Codable, Sendable, Equatable {
    let programID: String
    let curriculumVersion: Int
    let recommendedStageID: String
    let activeNodeID: String?
    let startedNodeIDs: [String]
    let completedNodeIDs: [String]
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case programID = "program_id"
        case curriculumVersion = "curriculum_version"
        case recommendedStageID = "recommended_stage_id"
        case activeNodeID = "active_node_id"
        case startedNodeIDs = "started_node_ids"
        case completedNodeIDs = "completed_node_ids"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct CurriculumNodeProgress: Codable, Sendable, Identifiable {
    let node: CurriculumNode
    let status: CurriculumNodeStatus
    let isRecommended: Bool

    var id: String { node.id }

    enum CodingKeys: String, CodingKey {
        case node, status
        case isRecommended = "is_recommended"
    }
}

struct CurriculumStageProgress: Codable, Sendable, Identifiable {
    let stage: CurriculumStage
    let nodes: [CurriculumNodeProgress]

    var id: String { stage.id }
}

struct UserCurriculumOverview: Codable, Sendable {
    let programID: String
    let curriculumVersion: Int
    let versionLabel: String
    let recommendedStageID: String
    let activeNodeID: String?
    let state: UserCurriculumState
    let stages: [CurriculumStageProgress]
    let recommendedNextNodes: [CurriculumNode]

    enum CodingKeys: String, CodingKey {
        case state, stages
        case programID = "program_id"
        case curriculumVersion = "curriculum_version"
        case versionLabel = "version_label"
        case recommendedStageID = "recommended_stage_id"
        case activeNodeID = "active_node_id"
        case recommendedNextNodes = "recommended_next_nodes"
    }
}
