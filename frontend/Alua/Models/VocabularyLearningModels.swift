import Foundation

enum LexicalKind: String, Codable, Sendable { case word, synonymUpgrade = "synonym_upgrade", phrase, collocation, phrasalVerb = "phrasal_verb" }
enum VocabularyReviewRating: String, Codable, Sendable { case again, hard, good }
enum VocabularyReviewSessionKind: String, Codable, Sendable { case midday, evening, weekly, manual }
enum VocabularyReviewCardType: String, Codable, Sendable { case termToMeaning = "term_to_meaning", meaningToTerm = "meaning_to_term", phraseToMeaning = "phrase_to_meaning", contextRecall = "context_recall" }

struct LexicalItem: Codable, Sendable, Identifiable, Hashable {
    let id: String; let kind: LexicalKind; let term: String; let translationRU: String
    let definitionEN: String?; let ipa: String?; let usageRU: String?
    let examples: [String]; let synonyms: [String]; let relatedItemIDs: [String]
    let cefr: String?; let topic: String?; let register: String?
    enum CodingKeys: String, CodingKey {
        case id, kind, term, ipa, examples, synonyms, cefr, topic, register
        case translationRU = "translation_ru"; case definitionEN = "definition_en"
        case usageRU = "usage_ru"; case relatedItemIDs = "related_item_ids"
    }
}

struct DailyLexicalPackResponse: Codable, Sendable {
    let packID: String; let schemaVersion: Int; let selectionAlgorithmVersion: Int; let contentVersion: String
    let coreWords: [LexicalItem]; let synonymUpgrades: [LexicalItem]; let phrases: [LexicalItem]
    var count: Int { coreWords.count + synonymUpgrades.count + phrases.count }
    enum CodingKeys: String, CodingKey { case packID = "pack_id"; case schemaVersion = "schema_version"; case selectionAlgorithmVersion = "selection_algorithm_version"; case contentVersion = "content_version"; case coreWords = "core_words"; case synonymUpgrades = "synonym_upgrades"; case phrases }
}

struct ReviewSessionSummary: Codable, Sendable, Identifiable {
    let sessionID: String; let kind: VocabularyReviewSessionKind; let cardCount: Int
    let completedCount: Int; let availableAt: String
    var id: String { sessionID }
    enum CodingKeys: String, CodingKey {
        case kind; case sessionID = "session_id"; case cardCount = "card_count"
        case completedCount = "completed_count"; case availableAt = "available_at"
    }
}

struct CurrentVocabularyRecall: Codable, Sendable {
    let sessionID: String; let cardID: String; let lexicalItemID: String
    let lexicalItem: LexicalItem; let cardType: VocabularyReviewCardType
    let prompt: String; let mode: String
    enum CodingKeys: String, CodingKey { case prompt, mode; case sessionID = "session_id"; case cardID = "card_id"; case lexicalItemID = "lexical_item_id"; case lexicalItem = "lexical_item"; case cardType = "card_type" }
}

struct VocabularyLearningToday: Codable, Sendable {
    let localDate: String; let dailyPack: DailyLexicalPackResponse; let reviewDueCount: Int
    let middaySession: ReviewSessionSummary; let eveningSession: ReviewSessionSummary
    let currentRecall: CurrentVocabularyRecall?
    enum CodingKeys: String, CodingKey {
        case localDate = "local_date"; case dailyPack = "daily_pack"; case reviewDueCount = "review_due_count"
        case middaySession = "midday_session"; case eveningSession = "evening_session"; case currentRecall = "current_recall"
    }
}

struct VocabularyReviewCard: Codable, Sendable, Identifiable {
    let cardID: String; let lexicalItemID: String; let cardType: VocabularyReviewCardType
    let frontTerm: String; let prompt: String; let item: LexicalItem
    var id: String { cardID }
    enum CodingKeys: String, CodingKey { case prompt, item; case cardID = "card_id"; case lexicalItemID = "lexical_item_id"; case cardType = "card_type"; case frontTerm = "front_term" }
}

struct VocabularyReviewSession: Codable, Sendable {
    let sessionID: String; let schemaVersion: Int; let generationVersion: Int; let packID: String; let contentVersion: String
    let localDate: String; let kind: VocabularyReviewSessionKind
    let cards: [VocabularyReviewCard]; let completedLexicalItemIDs: [String]
    enum CodingKeys: String, CodingKey { case kind, cards; case sessionID = "session_id"; case schemaVersion = "schema_version"; case generationVersion = "generation_version"; case packID = "pack_id"; case contentVersion = "content_version"; case localDate = "local_date"; case completedLexicalItemIDs = "completed_lexical_item_ids" }
}

struct VocabularyReviewStateResponse: Codable, Sendable { let lexicalItemID: String; let nextDueAt: Date; enum CodingKeys: String, CodingKey { case lexicalItemID = "lexical_item_id"; case nextDueAt = "next_due_at" } }
struct SubmitVocabularyReviewResult: Codable, Sendable { let eventID: String; let state: VocabularyReviewStateResponse; enum CodingKeys: String, CodingKey { case eventID = "event_id"; case state } }
