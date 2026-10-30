import Foundation

enum VocabularyPartOfSpeech: String, Codable, Sendable, CaseIterable {
    case noun, verb, adjective, adverb, phrase
    case phrasalVerb = "phrasal_verb"
    case other

    var title: String { rawValue.replacingOccurrences(of: "_", with: " ").capitalized }
}

enum VocabularyRegister: String, Codable, Sendable {
    case neutral, informal, formal, academic
}

enum VocabularyFrequency: String, Codable, Sendable {
    case veryCommon = "very_common"
    case common
    case lessCommon = "less_common"
}

enum VocabularyImportance: String, Codable, Sendable {
    case core, high, supporting
}

struct WordFamilyMember: Codable, Sendable, Hashable {
    let lemma: String
    let partOfSpeech: VocabularyPartOfSpeech

    enum CodingKeys: String, CodingKey {
        case lemma
        case partOfSpeech = "part_of_speech"
    }
}

struct VocabularyItem: Codable, Sendable, Identifiable, Hashable {
    let id: String
    let lemma: String
    let normalizedLemma: String
    let partOfSpeech: VocabularyPartOfSpeech
    let sense: String
    let definitionEN: String
    let translationRU: String
    let cefrLevel: EnglishLevel
    let register: VocabularyRegister
    let frequency: VocabularyFrequency
    let importance: VocabularyImportance
    let topics: [String]
    let trackIDs: [String]
    let wordFamily: [WordFamilyMember]
    let collocations: [String]
    let synonyms: [String]
    let antonyms: [String]
    let examples: [String]
    let usageNotes: [String]
    let commonConfusions: [String]
    let tags: [String]

    enum CodingKeys: String, CodingKey {
        case id, lemma, sense, register, frequency, importance, topics, collocations
        case synonyms, antonyms, examples, tags
        case normalizedLemma = "normalized_lemma"
        case partOfSpeech = "part_of_speech"
        case definitionEN = "definition_en"
        case translationRU = "translation_ru"
        case cefrLevel = "cefr_level"
        case trackIDs = "track_ids"
        case wordFamily = "word_family"
        case usageNotes = "usage_notes"
        case commonConfusions = "common_confusions"
    }
}

struct VocabularyTrack: Codable, Sendable, Identifiable, Hashable {
    let id: String
    let stageID: String
    let title: String
    let description: String
    let cefrLevel: EnglishLevel
    let topic: String
    let itemIDs: [String]

    enum CodingKeys: String, CodingKey {
        case id, title, description, topic
        case stageID = "stage_id"
        case cefrLevel = "cefr_level"
        case itemIDs = "item_ids"
    }
}

struct VocabularyListResponse: Codable, Sendable {
    let items: [VocabularyItem]
    let total: Int
    let limit: Int
    let offset: Int
}

struct VocabularyTrackSummary: Codable, Sendable, Identifiable, Hashable {
    let id: String
    let stageID: String
    let title: String
    let description: String
    let cefrLevel: String
    let topic: String
    let itemCount: Int

    enum CodingKeys: String, CodingKey {
        case id, title, description, topic
        case stageID = "stage_id"
        case cefrLevel = "cefr_level"
        case itemCount = "item_count"
    }
}

struct VocabularyTrackDetail: Codable, Sendable {
    let track: VocabularyTrack
    let items: [VocabularyItem]
}

struct CurriculumVocabularyResponse: Codable, Sendable {
    let curriculumNodeID: String
    let tracks: [VocabularyTrackDetail]

    enum CodingKeys: String, CodingKey {
        case tracks
        case curriculumNodeID = "curriculum_node_id"
    }
}
