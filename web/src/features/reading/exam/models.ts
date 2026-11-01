export const questionTypes = ["multiple_choice_single", "multiple_choice_multiple", "true_false_not_given", "yes_no_not_given", "matching_headings", "matching_information", "matching_features", "matching_sentence_endings", "sentence_completion", "summary_completion", "note_completion", "table_completion", "flow_chart_completion", "diagram_labelling", "short_answer"] as const;
export type QuestionType = typeof questionTypes[number];
export interface Option { label: string; text: string }
export interface Constraints { max_words: number | null; allow_number: boolean; allowed_values: string[]; reuse_allowed: boolean; selection_count: number | null }
export type Segment = { type: "text"; text: string } | { type: "blank"; number: number };
export type Block = { type: "rich_text"; segments: Segment[] } | { type: "image"; asset_id: string; alt: string } | { type: "heading"; text: string } | { type: "list"; items: Segment[][] } | { type: "table"; columns: string[]; rows: { segments: Segment[] }[][] };
export interface Asset { id: string; mime_type: string; width: number; height: number; sha256: string }
export interface Question { id: string; number: number; group_id: string; type: QuestionType; prompt: string; answer_input_type: "text" | "boolean" | "single_select" | "multi_select"; options: Option[]; constraints: Constraints }
export interface Group { id: string; type: QuestionType; instructions: string; question_numbers: number[]; options: Option[]; content_blocks: Block[]; assets: Asset[]; constraints: Constraints; questions: Question[]; representation: "structured_text" | "source_image_with_inputs" }
export interface Passage { id: string; number: number; title: string; subtitle: string | null; content: { type: "paragraph" | "heading"; text: string; label: string | null }[]; question_groups: Group[]; question_numbers: number[] }
export interface Exam { id: string; dataset_version: string; source_book: number; source_test_number: number; duration_seconds: number; question_count: number; passages: Passage[] }
export interface Attempt { id: string; exam_id: string; mode: "full_exam" | "passage_practice"; status: "in_progress" | "submitted" | "expired"; version: number; content_hash: string; server_now: string; deadline_at: string | null; answers: Record<string, string>; state: { current_passage: number; checked_question_ids: string[] }; not_fully_proofread: boolean; mutation_applied?: boolean; started_at?:string; submitted_at?:string|null; exam?: Exam }
export interface PassageViewState { passageId: string; textScrollTop: number; questionsScrollTop: number; lastFocusedQuestionId: string | null }
export const allQuestions = (exam: Exam) => exam.passages.flatMap((p) => p.question_groups.flatMap((g) => g.questions));
