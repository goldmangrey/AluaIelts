"use client";
import { Fragment, useRef, type ReactNode } from "react";
import type { Group, Question, Segment, Block } from "./models";
import type { ResultPosition } from "./results";
import { AssetImage } from "./asset-image";
import styles from "./question-options.module.css";
import aiStyles from "../ai/review.module.css";
export interface QuestionActions {
  results?:ResultPosition[];
  explain?: {isOpen:(id:string)=>boolean; open:(id:string)=>void; render?:(question:Question)=>ReactNode};
  visibleQuestions?:ReadonlySet<string>;
  answers: Record<string, string>; review: ReadonlySet<string>; locked: ReadonlySet<string>; disabled: boolean;
  change: (changes: Record<string, string>) => void;
  toggleReview: (id: string) => void;
  register: (id: string, node: HTMLElement | null) => void;
  focus: (id: string) => void;
}
export function questionOptions(q: Question, g: Group) {
  if (q.type === "true_false_not_given") return ["TRUE", "FALSE", "NOT GIVEN"].map((label) => ({ label, text: label }));
  if (q.type === "yes_no_not_given") return ["YES", "NO", "NOT GIVEN"].map((label) => ({ label, text: label }));
  if (q.options.length) return q.options;
  if (g.options.length) return g.options;
  return (q.constraints.allowed_values.length ? q.constraints.allowed_values : g.constraints.allowed_values).map((label) => ({ label, text: label }));
}
function sharedOptions(g: Group) {
  const selectable = g.questions.filter(q => q.answer_input_type === "single_select" || q.answer_input_type === "multi_select");
  if (!selectable.length || g.type === "multiple_choice_single" || g.type === "multiple_choice_multiple") return [];
  const first = questionOptions(selectable[0]!, g);
  return first.some(o => o.text.trim() !== o.label.trim()) && selectable.every(q => JSON.stringify(questionOptions(q, g)) === JSON.stringify(first)) ? first : [];
}
function inlineQuestionNumbers(g: Group): Set<number> {
  const imageMode = g.representation === "source_image_with_inputs" || (g.assets.length > 0 && g.questions.some(q => q.answer_input_type === "multi_select") && !g.options.length);
  const inline = !imageMode && g.questions.every(q => q.answer_input_type === "text" || q.answer_input_type === "single_select") && g.content_blocks.some(b => b.type === "rich_text" && b.segments.some(s => s.type === "blank") || b.type === "table");
  if (!inline) return new Set();
  return new Set(g.content_blocks.flatMap(b => b.type === "rich_text" ? b.segments : b.type === "list" ? b.items.flat() : b.type === "table" ? b.rows.flat().flatMap(cell => cell.segments) : []).flatMap(s => s.type === "blank" ? [s.number] : []));
}
/** Validate public task material only. Allowed answer labels alone are not option explanations. */
export function questionIntegrity(g: Group): string[] {
  const issues = new Set<string>();
  const sourceImage = g.representation === "source_image_with_inputs" && g.assets.length > 0;
  const material = [g.instructions, ...g.questions.map(q => q.prompt), ...g.content_blocks.flatMap(b => b.type === "rich_text" ? b.segments.filter(s => s.type === "text").map(s => s.text) : b.type === "list" ? b.items.flatMap(item => item.filter(s => s.type === "text").map(s => s.text)) : [])].join("\n");
  for (const q of g.questions) {
    if (sourceImage) continue;
    const options = questionOptions(q, g);
    if (new Set(options.map(o => o.label)).size !== options.length) issues.add("duplicate_option_labels");
    const allowed = q.constraints.allowed_values.length ? q.constraints.allowed_values : g.constraints.allowed_values;
    if (options.length && allowed.some(label => !options.some(o => o.label === label))) issues.add("missing_option_label");
    if ((q.answer_input_type === "single_select" || q.answer_input_type === "multi_select") && !["matching_information", "true_false_not_given", "yes_no_not_given"].includes(q.type)) {
      const explained = options.length > 0 && options.every(o => o.text.trim() !== o.label.trim() || material.split("\n").some(line => line.trim().startsWith(`${o.label} `) && line.trim().slice(o.label.length).trim().length > 2));
      if (!explained && !g.assets.length) issues.add("missing_option_text");
    }
    if (q.constraints.selection_count !== null && options.length && q.constraints.selection_count > options.length) issues.add("invalid_selection_count");
  }
  const sharedPrompt = g.questions.every(q => q.prompt === g.questions[0]?.prompt);
  const inlineShown = inlineQuestionNumbers(g);
  if (!sourceImage && !sharedPrompt && g.questions.some(q => !inlineShown.has(q.number) && g.questions.some(other => other.id !== q.id && normalized(other.prompt).length > 25 && normalized(q.prompt).includes(normalized(other.prompt))))) issues.add("overlapping_question_prompts");
  if (!g.instructions.trim() && !sourceImage) issues.add("missing_instructions");
  if (g.representation === "source_image_with_inputs" && !g.assets.length) issues.add("missing_source_image");
  if (g.type === "diagram_labelling" && !g.assets.length) issues.add("missing_diagram");
  return [...issues];
}
function OptionList({ options }: { options: ReturnType<typeof questionOptions> }) {
  return <dl className={styles.list}>{options.map((o, index) => <div key={`${o.label}:${index}`}><dt>{o.label}</dt><dd>{o.text}</dd></div>)}</dl>;
}
function GroupOptions({ group, options }: { group: Group; options: ReturnType<typeof questionOptions> }) {
  const dialog = useRef<HTMLDialogElement>(null), trigger = useRef<HTMLButtonElement>(null);
  const title = `Options for questions ${group.question_numbers.join(", ")}`;
  return <><div className={styles.access}><span>Options</span><button ref={trigger} type="button" onClick={() => dialog.current?.showModal()}>View options</button></div>
    <OptionList options={options} />
    <dialog ref={dialog} className={styles.dialog} aria-label={title} onClose={() => trigger.current?.focus({ preventScroll: true })}>
      <header><h3>Options</h3><button type="button" autoFocus aria-label="Close options" onClick={() => dialog.current?.close()}>×</button></header><OptionList options={options} />
    </dialog></>;
}
function choiceStatus(q:Question,g:Group,a:QuestionActions,label:string){
  if(!a.results)return undefined;
  const rows=a.results.filter(r=>r.question_id===q.id||r.unordered_group&&g.questions.some(q=>q.id===r.question_id));
  const selected=rows.find(r=>r.user_answer===label);
  if(selected)return selected.is_correct?'correct':selected.unanswered?'unanswered':'incorrect';
  return rows.some(r=>r.accepted_answers.includes(label))?'correct':'neutral';
}
function Review({ q, a, compact = false }: { q: Question; a: QuestionActions; compact?: boolean }) {
  const result=a.results?.find(p=>p.question_id===q.id);
  if(result)return <span className="answer-review" data-review-status={result.unanswered?"unanswered":result.is_correct?"correct":"incorrect"}><span className="review-question-label">Q{q.number}</span><strong>{result.is_correct?"Correct":result.unanswered?"Unanswered":"Incorrect"}</strong><span className="saved-answer-value">Your answer: {result.user_answer||"Blank"}</span><span className="correct-answer">Correct answer: {result.correct_answer}</span>{result.unordered_group&&<span>Letters in this group are graded together; order does not matter.</span>}{a.explain&&<button type="button" className={aiStyles.trigger} aria-label={`Explain question ${q.number} with AI`} aria-expanded={a.explain.isOpen(q.id)} aria-controls={`reading-ai-${q.id}`} onClick={()=>a.explain!.open(q.id)}>✦ Explain with AI</button>}{result.accepted_answers.length>1&&<span>Accepted alternatives: {result.accepted_answers.join(" / ")}</span>}</span>;
  return <button type="button" className={compact ? "review-toggle inline-review" : "review-toggle"} title={compact ? `Review question ${q.number}` : undefined} aria-label={`${a.review.has(q.id) ? "Unmark" : "Mark"} question ${q.number} for review`} aria-pressed={a.review.has(q.id)} onClick={() => a.toggleReview(q.id)}>{compact ? <svg width="14" height="14" viewBox="0 0 20 20" fill={a.review.has(q.id) ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 18V3h11l-2 4 2 4H4" /></svg> : a.review.has(q.id) ? "Marked for review" : "Mark for review"}</button>;
}
function Field({ q, g, a, inline = false }: { q: Question; g: Group; a: QuestionActions; inline?: boolean }) {
  const value = a.answers[q.id] ?? "";
  const opts = questionOptions(q, g);
  const localKey = !sharedOptions(g).length && q.type.startsWith("matching_") ? q.options.filter((o) => o.text !== o.label && !g.options.some((shared) => shared.label === o.label && shared.text === o.text) && !normalized(g.instructions).includes(normalized(o.text))) : [];
  const choice = q.answer_input_type === "single_select" || q.answer_input_type === "boolean";
  const max = q.constraints.max_words ?? g.constraints.max_words;
  const over = max !== null && value.trim().split(/\s+/).filter(Boolean).length > max;
  const limitWords = ["", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN"];
  const limitInInstructions = inline && max !== null && new RegExp(`\\b(?:${max}${limitWords[max] ? `|${limitWords[max]}` : ""})\\s+WORDS?\\b`, "i").test(g.instructions);
  const input = choice && opts.length ? <span className="answer-choices" role="group" aria-label={`Answer ${q.number}`}>
    {opts.map((o, index) => <button type="button" key={`${o.label}:${index}`} data-choice-status={choiceStatus(q,g,a,o.label)} aria-pressed={value === o.label}
      disabled={a.disabled || a.locked.has(q.id) || value !== o.label && q.type.startsWith("matching_") && !q.constraints.reuse_allowed && !g.constraints.reuse_allowed && g.questions.some((other) => other.id !== q.id && a.answers[other.id] === o.label)}
      title={o.text !== o.label ? o.text : undefined} onFocus={() => a.focus(q.id)} onClick={() => a.change({ [q.id]: value === o.label ? "" : o.label })}>{o.label}</button>)}
  </span> : <input aria-label={`Answer ${q.number}`} autoComplete="off" autoCapitalize="none" spellCheck={false} value={value} maxLength={500} disabled={a.disabled || a.locked.has(q.id)} aria-invalid={over || undefined} onFocus={() => a.focus(q.id)} onChange={(e) => a.change({ [q.id]: e.target.value })} />;
  return <span className={inline ? "inline-answer" : "answer-field"}>
    {input}{localKey.length > 0 && <span className="matching-local-key">{localKey.map((o) => <span key={o.label}><strong>{o.label}</strong> {o.text}</span>)}</span>}{max !== null && (!limitInInstructions || over) && <span className={over ? "word-limit over-limit" : "word-limit"}>{over ? "Over word limit" : `Up to ${max} ${max === 1 ? "word" : "words"}${q.constraints.allow_number ? " and/or a number" : ""}`}</span>}
  </span>;
}
function Anchor({ q, a, children, inline = false }: { q: Question; a: QuestionActions; children: ReactNode; inline?: boolean }) {
  const Tag = inline ? "span" : "div";
  return <Tag className={inline ? "inline-question" : "reading-question"} data-question={q.number} data-review-status={a.results?(()=>{const p=a.results.find(p=>p.question_id===q.id);return p?.unanswered?"unanswered":p?.is_correct?"correct":"incorrect";})():undefined} hidden={a.visibleQuestions?!a.visibleQuestions.has(q.id):undefined} tabIndex={a.results?-1:undefined} ref={(node) => a.register(q.id, node)} onFocusCapture={() => a.focus(q.id)}>
    <span className="question-number">{q.number}.</span> {children}{inline && !a.results && <Review q={q} a={a} compact />} {!inline && <><Review q={q} a={a} />{a.explain?.render?.(q)}</>}
  </Tag>;
}
export function multipleSelection(g: Group, answers: Record<string, string>, label: string): Record<string, string> {
  const current = [...new Set(g.questions.map((q) => answers[q.id] ?? "").filter(Boolean))];
  const limit = g.constraints.selection_count ?? g.questions.length;
  const next = current.includes(label) ? current.filter((v) => v !== label) : current.length < limit ? [...current, label] : current;
  return Object.fromEntries(g.questions.map((q, i) => [q.id, next[i] ?? ""]));
}
function MultiChoice({ group: g, actions: a }: { group: Group; actions: QuestionActions }) {
  const opts = questionOptions(g.questions[0]!, g);
  const selected = new Set(g.questions.map((q) => a.answers[q.id]).filter(Boolean));
  const limit = g.constraints.selection_count ?? g.questions.length;
  return <><div className="multi-positions">{g.questions.map((q) => <Anchor key={q.id} q={q} a={a}><span className="sr-only">Answer position {q.number}</span></Anchor>)}</div>
    <fieldset className="choice-list"><legend>Choose {limit} letters <span className="muted">· {selected.size} selected</span></legend>{opts.map((o, index) => <label key={`${o.label}:${index}`} data-choice-status={choiceStatus(g.questions[0]!,g,a,o.label)} className={selected.has(o.label) ? "choice-selected" : undefined}>
      <input type="checkbox" checked={selected.has(o.label)} disabled={a.disabled || g.questions.some((q) => a.locked.has(q.id)) || (!selected.has(o.label) && selected.size >= limit)} onFocus={() => a.focus(g.questions[0]!.id)} onChange={() => a.change(multipleSelection(g, a.answers, o.label))} />
      <span><strong>{o.label}</strong> {o.text}</span>
    </label>)}</fieldset>{selected.size > 0 && <button type="button" className="text-button" disabled={a.disabled || g.questions.some((q) => a.locked.has(q.id))} onClick={() => a.change(Object.fromEntries(g.questions.map((q) => [q.id, ""])))}>Clear selection</button>}</>;
}
function normalized(text: string) { return text.replace(/\s+/g, " ").trim(); }
function withoutRepeatedGroupHeading(text: string, group: Group) {
  const first = group.question_numbers[0], last = group.question_numbers.at(-1);
  const range = first === last ? `${first}` : `${first}\\s*[-–—]\\s*${last}`;
  // The section already supplies this exact numbered heading. Keep all task wording.
  return text.replace(new RegExp(`^\\s*Questions?\\s+${range}\\s*\\n`, "i"), "");
}
function withoutOptionAppendix(text: string, options: ReturnType<typeof questionOptions>) {
  if (!options.length || options.some((o) => o.label === o.text)) return text;
  const escape = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Also accept an exact bank laid out across columns or wrapped PDF lines.
  const appendix = options.map(o => `${escape(o.label)}[.)]?\\s+${normalized(o.text).split(" ").map(escape).join("\\s+")}`).join("\\s+");
  const suffix = new RegExp(`(?:^|\\s)${appendix}\\s*$`).exec(text);
  if (suffix) return text.slice(0, suffix.index).trim();
  const starts = options.map((o) => [...text.matchAll(new RegExp(`^\\s*${escape(o.label)}(?:[.)]?[ \t]+|[.)]?\\n)`, "gm"))].at(-1));
  if (starts.some((match) => !match)) return text;
  for (let i = 0; i < options.length; i++) {
    const start = starts[i]!;
    const end = starts[i + 1]?.index ?? text.length;
    if (end <= start.index! || normalized(text.slice(start.index! + start[0].length, end)) !== normalized(options[i]!.text)) return text;
  }
  return text.slice(0, starts[0]!.index).trim();
}
function RadioQuestion({ q, g, a, prompt = q.prompt }: { q: Question; g: Group; a: QuestionActions; prompt?: string }) {
  return <Anchor q={q} a={a}><fieldset className="choice-list"><legend>{withoutOptionAppendix(prompt, questionOptions(q, g))}</legend>{questionOptions(q, g).map((o, index) => <label key={`${o.label}:${index}`} data-choice-status={choiceStatus(q,g,a,o.label)} className={a.answers[q.id] === o.label ? "choice-selected" : undefined}>
    <input type="radio" name={q.id} checked={a.answers[q.id] === o.label} value={o.label} disabled={a.disabled || a.locked.has(q.id)} onFocus={() => a.focus(q.id)} onClick={() => { if (a.answers[q.id] === o.label) a.change({ [q.id]: "" }); }} onChange={() => a.change({ [q.id]: o.label })} /><span>{o.label === o.text ? o.text : `${o.label}  ${o.text}`}</span>
  </label>)}</fieldset></Anchor>;
}
export function QuestionGroup({ group: g, actions, uid, active }: { group: Group; actions: QuestionActions; uid: string; active: boolean }) {
  const integrity = questionIntegrity(g);
  const a = integrity.length ? { ...actions, disabled: true } : actions;
  const bank = sharedOptions(g);
  const imageMode = g.representation === "source_image_with_inputs" || (g.assets.length > 0 && g.questions.some((q) => q.answer_input_type === "multi_select") && !g.options.length);
  const qByNumber = new Map(g.questions.map((q) => [q.number, q]));
  const shown = new Set<number>();
  const segmentNodes = (segments: Segment[]): ReactNode => segments.map((s, i) => {
    if (s.type === "text") return <Fragment key={i}>{withoutRepeatedGroupHeading(withoutOptionAppendix(s.text, bank), g)}</Fragment>;
    const q = qByNumber.get(s.number);
    if (!q) return <strong key={i} role="alert">Missing question {s.number}</strong>;
    if (shown.has(q.number)) return <span key={i}>[see answer {q.number}]</span>;
    shown.add(q.number);
    return <Anchor key={q.id} q={q} a={a} inline><Field q={q} g={g} a={a} inline /></Anchor>;
  });
  // Emit saved review controls once, beside the source block containing their blank.
  // Fallback questions remain owned by their non-inline Anchor.
  const inlineContent = (segments: Segment[]): ReactNode => {
    const previous = new Set(shown);
    const nodes = segmentNodes(segments);
    const local = g.questions.filter(q => shown.has(q.number) && !previous.has(q.number));
    return <>{nodes}{a.results && local.length > 0 && <div className={styles.inlineReviews} aria-label="Saved answers">{local.map(q => <div key={q.id} data-review-for={q.number}><Review q={q} a={a}/>{a.explain?.render?.(q)}</div>)}</div>}</>;
  };
  const blocks = (b: Block, i: number): ReactNode => {
    switch (b.type) {
      case "rich_text": return <div className="task-text" key={i}>{inlineContent(b.segments)}</div>;
      case "heading": return <h3 key={i}>{b.text}</h3>;
      case "list": return <ul className="task-list" key={i}>{b.items.map((item, j) => <li key={j}>{inlineContent(item)}</li>)}</ul>;
      case "table": return <div className="task-table-scroll" key={i}><table><thead><tr>{b.columns.map((col, j) => <th key={j} scope="col">{col}</th>)}</tr></thead><tbody>{b.rows.map((row, j) => <tr key={j}>{row.map((cell, k) => <td key={k}>{inlineContent(cell.segments)}</td>)}</tr>)}</tbody></table></div>;
      case "image": { const asset = g.assets.find((asset) => asset.id === b.asset_id); return asset ? <AssetImage key={asset.id} asset={asset} uid={uid} active={active} alt={b.alt} /> : <p key={i} role="alert">Required task image is missing.</p>; }
    }
  };
  const sharedPrompt = g.questions.length > 1 && g.questions.every((q) => q.prompt.trim() === g.questions[0]!.prompt.trim());
  let instructions = withoutOptionAppendix(g.instructions, bank);
  const soleRadio = g.questions.length === 1 && g.questions[0]!.type === "multiple_choice_single";
  // A complete single-question source block belongs in its legend once.
  if (soleRadio && normalized(instructions) === normalized(g.questions[0]!.prompt)) instructions = "";
  else if (!sharedPrompt) {
    const first = g.questions[0]!;
    const at = instructions.indexOf(first.prompt);
    // Only trim a verified exact suffix, never the rest of an OCR/source block.
    if (at > 0 && instructions.slice(at).trim() === first.prompt.trim()) instructions = instructions.slice(0, at).replace(new RegExp(`\\n\\s*${first.number}\\s*[.]?$`), "").trim();
  }
  if (g.type === "multiple_choice_multiple" && g.options.length) instructions = withoutOptionAppendix(instructions, g.options);
  instructions = withoutRepeatedGroupHeading(instructions, g);
  const inline = !imageMode && g.questions.every((q) => q.answer_input_type === "text" || q.answer_input_type === "single_select") && g.content_blocks.some((b) => b.type === "rich_text" && b.segments.some((s) => s.type === "blank") || b.type === "table");
  // Compute block nodes now so `shown` correctly tracks fields before fallback rows.
  const content = inline ? g.content_blocks.map(blocks) : null;
  return <section className={`question-group ${a.results?styles.completed:""}`} hidden={a.visibleQuestions?!g.questions.some(q=>a.visibleQuestions!.has(q.id)):undefined} data-question-type={g.type} data-representation={g.representation}>
    <h3 className="group-heading">{g.question_numbers.length === 1 ? `Question ${g.question_numbers[0]}` : `Questions ${g.question_numbers[0]}–${g.question_numbers.at(-1)}`}</h3>
    {integrity.length > 0 && <p className={styles.warning} role="alert">This task needs content review. Answer entry is unavailable; existing answers are preserved.{process.env.NODE_ENV === "development" && <code>{g.id}: {integrity.join(", ")}</code>}</p>}
    {!imageMode && bank.length > 0 && <GroupOptions group={g} options={bank} />}
    {imageMode ? <>{g.assets.map((asset) => <AssetImage key={asset.id} asset={asset} uid={uid} active={active} alt={`Original task, questions ${g.question_numbers.join(", ")}`} />)}<details className="task-transcript"><summary>Task text</summary><p className="task-text">{g.instructions}</p></details></> : inline ? content : instructions ? <p className="task-instructions">{sharedPrompt && !g.instructions.includes(g.questions[0]!.prompt) ? `${instructions}\n${g.questions[0]!.prompt}` : instructions}</p> : null}

    {!imageMode && g.type === "multiple_choice_multiple" && g.options.length ? <MultiChoice group={g} actions={a} /> : g.questions.filter((q) => !shown.has(q.number)).map((q) => {
      if (q.type === "multiple_choice_single" && questionOptions(q, g).length > 0) {
        const prompt = imageMode || sharedPrompt ? `Answer ${q.number}` : instructions && q.prompt.startsWith(instructions) ? q.prompt.slice(instructions.length).trim() : soleRadio ? q.prompt.replace(new RegExp(`^Question\\s+${q.number}\\s*\\n`, "i"), "") : q.prompt;
        return <RadioQuestion key={q.id} q={q} g={g} a={a} prompt={prompt} />;
      }
      const prompt = withoutOptionAppendix(q.prompt, bank);
      const parts = prompt.split(/_{2,}/);
      return <Anchor key={q.id} q={q} a={a}>
        {imageMode || sharedPrompt ? <><span className="source-input-label">Answer {q.number}</span><Field q={q} g={g} a={a} />{q.answer_input_type === "multi_select" && <small>Enter the letter from the source task.</small>}</> : parts.length === 2 && q.answer_input_type === "text" ? <span className="completion-sentence">{parts[0]}<Field q={q} g={g} a={a} inline />{parts[1]}</span> : <><p className="question-prompt">{prompt}</p><Field q={q} g={g} a={a} /></>}
      </Anchor>;
    })}
  </section>;
}
