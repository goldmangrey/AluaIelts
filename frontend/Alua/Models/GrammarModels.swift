import Foundation

struct GrammarStructure: Codable, Sendable, Hashable {
    let label: String
    let formula: String
    let example: String
}

struct GrammarUse: Codable, Sendable, Hashable {
    let title: String
    let explanationEN: String
    let explanationRU: String?
    let example: String
    let translationRU: String?

    enum CodingKeys: String, CodingKey {
        case title, example
        case explanationEN = "explanation_en"
        case explanationRU = "explanation_ru"
        case translationRU = "translation_ru"
    }
}

struct GrammarExample: Codable, Sendable, Hashable {
    let sentence: String
    let translationRU: String?
    let note: String?

    enum CodingKeys: String, CodingKey {
        case sentence, note
        case translationRU = "translation_ru"
    }
}

struct GrammarCommonError: Codable, Sendable, Hashable, Identifiable {
    let wrong: String
    let correct: String
    let explanationEN: String
    let explanationRU: String
    let errorTag: String

    var id: String { errorTag }

    enum CodingKeys: String, CodingKey {
        case wrong, correct
        case explanationEN = "explanation_en"
        case explanationRU = "explanation_ru"
        case errorTag = "error_tag"
    }
}

struct GrammarContrast: Codable, Sendable, Hashable, Identifiable {
    let relatedLessonID: String?
    let title: String
    let explanationEN: String
    let explanationRU: String
    let examples: [GrammarExample]

    var id: String { relatedLessonID ?? title }

    enum CodingKeys: String, CodingKey {
        case title, examples
        case relatedLessonID = "related_lesson_id"
        case explanationEN = "explanation_en"
        case explanationRU = "explanation_ru"
    }
}

struct GrammarLesson: Codable, Sendable, Identifiable, Hashable {
    let id: String
    let title: String
    let shortTitle: String
    let cefrLevel: EnglishLevel
    let stageID: String
    let summary: String
    let explanationEN: String
    let explanationRU: String
    let structures: [GrammarStructure]
    let uses: [GrammarUse]
    let examples: [GrammarExample]
    let commonErrors: [GrammarCommonError]
    let contrasts: [GrammarContrast]
    let usageNotes: [String]
    let keywords: [String]
    let tags: [String]
    let curriculumNodeIDs: [String]
    let estimatedStudyMinutes: Int?

    enum CodingKeys: String, CodingKey {
        case id, title, summary, structures, uses, examples, contrasts, keywords, tags
        case shortTitle = "short_title"
        case cefrLevel = "cefr_level"
        case stageID = "stage_id"
        case explanationEN = "explanation_en"
        case explanationRU = "explanation_ru"
        case commonErrors = "common_errors"
        case usageNotes = "usage_notes"
        case curriculumNodeIDs = "curriculum_node_ids"
        case estimatedStudyMinutes = "estimated_study_minutes"
    }
}

struct GrammarListResponse: Codable, Sendable {
    let items: [GrammarLesson]
    let total: Int
    let limit: Int
    let offset: Int
    let datasetVersion: Int

    enum CodingKeys: String, CodingKey {
        case items, total, limit, offset
        case datasetVersion = "dataset_version"
    }
}

struct GrammarStageResponse: Codable, Sendable {
    let stageID: String
    let title: String
    let lessons: [GrammarLesson]
    let datasetVersion: Int

    enum CodingKeys: String, CodingKey {
        case title, lessons
        case stageID = "stage_id"
        case datasetVersion = "dataset_version"
    }
}
