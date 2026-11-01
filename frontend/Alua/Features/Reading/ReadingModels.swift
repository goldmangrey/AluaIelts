import Foundation

// Wire names deliberately match Stage 2 and canonical Dataset v1, not a parallel DTO dialect.
enum ReadingMode: String, Codable, Sendable { case full_exam, passage_practice }
enum ReadingQuestionType: String, Codable, CaseIterable, Sendable {
    case multiple_choice_single, multiple_choice_multiple, true_false_not_given, yes_no_not_given
    case matching_headings, matching_information, matching_features, matching_sentence_endings
    case sentence_completion, summary_completion, note_completion, table_completion
    case flow_chart_completion, diagram_labelling, short_answer
    var title: String { rawValue.replacingOccurrences(of: "_", with: " ").capitalized }
}
enum ReadingInputType: String, Codable, Sendable { case text, boolean, single_select, multi_select }
struct ReadingCatalogResponse: Codable, Sendable { var items: [ReadingBook]; var dataset_version: String }
struct ReadingBook: Codable, Identifiable, Sendable {
    var book_number: Int; var exams: [ReadingCatalogEntry]
    var id: Int { book_number }
    var available: [ReadingCatalogEntry] { exams.filter(\.enabled_for_private_practice).sorted { $0.test_ordinal < $1.test_ordinal } }
}
struct ReadingCatalogEntry: Codable, Identifiable, Sendable {
    var exam_id: String; var source_book: Int; var source_test_number: Int; var test_ordinal: Int
    var dataset_version: String; var content_hash: String; var content_status: String
    var enabled_for_private_practice: Bool; var not_fully_proofread: Bool
    var completed_attempts: Int; var in_progress_attempt_ids: [String]; var best_estimated_band: Double?
    var id: String { exam_id }
    var title: String { "Cambridge \(source_book) · Test \(source_test_number)" }
}
struct ReadingExam: Codable, Identifiable, Sendable {
    var id: String; var dataset_version: String; var source_book: Int; var source_test_number: Int
    var test_ordinal: Int; var duration_seconds: Int; var question_count: Int; var content_status: String
    var passages: [ReadingPassage]
    var title: String { "Cambridge \(source_book) · Test \(source_test_number)" }
    var questions: [ReadingQuestion] { passages.flatMap { $0.question_groups.flatMap(\.questions) } }
    var assets: [ReadingAsset] { passages.flatMap { $0.question_groups.flatMap(\.assets) } }
    func passage(for question: String) -> ReadingPassage? { passages.first { $0.questions.contains { $0.id == question } } }
    func group(for question: String) -> ReadingGroup? { passages.flatMap(\.question_groups).first { $0.questions.contains { $0.id == question } } }
}
struct ReadingPassage: Codable, Identifiable, Sendable {
    var id: String; var number: Int; var title: String; var subtitle: String?
    var content: [ReadingParagraph]; var question_groups: [ReadingGroup]; var question_numbers: [Int]
    var questions: [ReadingQuestion] { question_groups.flatMap(\.questions) }
}
struct ReadingParagraph: Codable, Equatable, Sendable { var type: String; var text: String; var label: String? }
struct ReadingGroup: Codable, Identifiable, Sendable {
    var id: String; var type: ReadingQuestionType; var instructions: String
    var question_numbers: [Int]; var options: [ReadingOption]; var content_blocks: [ReadingBlock]
    var assets: [ReadingAsset]; var constraints: ReadingConstraints; var questions: [ReadingQuestion]
    var representation: String
    var usesImage: Bool { representation == "source_image_with_inputs" }
    func options(for question: ReadingQuestion) -> [ReadingOption] {
        if !question.options.isEmpty { return question.options }
        if !options.isEmpty { return options }
        return question.constraints.allowed_values.map { ReadingOption(label: $0, text: $0) }
    }
}
struct ReadingQuestion: Codable, Identifiable, Sendable {
    var id: String; var number: Int; var group_id: String; var type: ReadingQuestionType
    var prompt: String; var answer_input_type: ReadingInputType
    var options: [ReadingOption]; var constraints: ReadingConstraints
}
struct ReadingOption: Codable, Equatable, Identifiable, Sendable {
    var label: String; var text: String; var id: String { label }
}
struct ReadingConstraints: Codable, Sendable {
    var max_words: Int?; var allow_number: Bool; var allowed_values: [String]
    var reuse_allowed: Bool; var selection_count: Int?
}
struct ReadingSegment: Codable, Sendable {
    enum Kind: String, Codable, Sendable { case text, blank }
    var type: Kind; var text: String?; var number: Int?
}
struct ReadingCell: Codable, Sendable { var segments: [ReadingSegment] }
struct ReadingBlock: Codable, Sendable {
    enum Kind: String, Codable, Sendable { case rich_text, image, table, list, heading }
    var type: Kind; var segments: [ReadingSegment]?; var asset_id: String?; var alt: String?
    var columns: [String]?; var rows: [[ReadingCell]]?; var items: [[ReadingSegment]]?; var text: String?
}
struct ReadingAsset: Codable, Identifiable, Sendable {
    var id: String; var mime_type: String; var width: Int; var height: Int; var sha256: String
    var url: String?
}
struct ReadingAnnotation: Codable, Identifiable, Equatable, Sendable {
    var id: UUID; var passage_id: String; var content_hash: String; var block_index: Int
    var start: Int; var end: Int; var quote: String; var color: String; var note: String?
}
struct ReadingCrossedOption: Codable, Equatable, Sendable { var question_id: String; var option_label: String }
struct ReadingAttemptState: Codable, Sendable {
    var current_passage: Int = 1
    var annotations: [ReadingAnnotation] = []
    var crossed_options: [ReadingCrossedOption] = []
    var checked_question_ids: [String] = []
    var reported_active_seconds: [String: Int] = [:]
}
struct ReadingAttemptList: Codable, Sendable { var items: [ReadingAttempt]; var limit: Int; var offset: Int }
struct ReadingAttempt: Codable, Identifiable, Sendable {
    var id: String; var exam_id: String; var dataset_version: String; var content_hash: String
    var content_revision: String; var mode: ReadingMode; var selected_passage: Int?; var status: String
    var version: Int; var started_at: Date; var deadline_at: Date?; var submitted_at: Date?
    var server_now: Date; var remaining_seconds: Int?; var elapsed_seconds: Int
    var content_status: String; var not_fully_proofread: Bool; var timing_status: String
    var answers: [String: String]?; var state: ReadingAttemptState?; var exam: ReadingExam?
    var result: ReadingResult?; var checked_result: ReadingResult?
    var raw_score: Int?; var estimated_band: Double?; var mutation_applied: Bool?; var rejection_reason: String?
    var terminal: Bool { status != "in_progress" }
}
struct ReadingStatistic: Codable, Sendable {
    var correct: Int; var incorrect: Int; var unanswered: Int; var total: Int; var accuracy: Double
    var reported_active_seconds: Int?; var time_is_verified: Bool?
}
struct ReadingGradingGroup: Codable, Sendable {
    var id: String; var mode: String; var question_numbers: [Int]; var expected_units: [[String]]
}
indirect enum ReadingJSON: Codable, Sendable {
    case string(String), object([String: ReadingJSON]), array([ReadingJSON]), number(Double), bool(Bool), null
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode([String: ReadingJSON].self) { self = .object(v) }
        else { self = .array(try c.decode([ReadingJSON].self)) }
    }
    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case let .string(v): try c.encode(v)
        case let .object(v): try c.encode(v)
        case let .array(v): try c.encode(v)
        case let .number(v): try c.encode(v)
        case let .bool(v): try c.encode(v)
        case .null: try c.encodeNil()
        }
    }
    var quote: String? {
        switch self { case let .string(v): v; case let .object(v): v["quote"]?.quote; default: nil }
    }
}
struct ReadingPositionResult: Codable, Identifiable, Sendable {
    var question_id: String; var number: Int; var question_type: ReadingQuestionType; var passage_number: Int
    var user_answer: String; var correct_answer: String; var accepted_answers: [String]
    var grading_group: ReadingGradingGroup?; var is_correct: Bool; var unanswered: Bool
    var evidence: ReadingJSON?; var id: String { question_id }
}
struct ReadingResult: Codable, Sendable {
    var exam_id: String; var raw_score: Int; var total_questions: Int; var accuracy: Double
    var estimated_band: Double?; var band_is_estimate: Bool; var band_label: String?
    var elapsed_seconds: Int; var timing_status: String
    var correct_count: Int; var incorrect_count: Int; var unanswered_count: Int
    var positions: [ReadingPositionResult]; var per_passage: [String: ReadingStatistic]
    var per_question_type: [String: ReadingStatistic]; var weakest_question_types: [String]
}
struct ReadingStart: Codable, Sendable {
    var event_id = UUID(); var exam_id: String; var mode: ReadingMode; var selected_passage: Int?
}
struct ReadingMutationBody: Codable, Sendable {
    var event_id: UUID; var expected_version: Int
    var answer: String?; var answers: [String: String]?
    var current_passage: Int?; var annotations: [ReadingAnnotation]?; var crossed_options: [ReadingCrossedOption]?
    var question_ids: [String]?
}
