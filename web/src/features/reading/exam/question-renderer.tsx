"use client";
import { Fragment, type ReactNode } from "react";
import type { Group, Question, Segment, Block } from "./models";
import type { ResultPosition } from "./results";
import { AssetImage } from "./asset-image";
export interface QuestionActions {
  results?:ResultPosition[];
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
function Review({ q, a }: { q: Question; a: QuestionActions }) {
  const result=a.results?.find(p=>p.question_id===q.id);
  if(result)return <span className="answer-review"><strong>{result.is_correct?"Correct":result.unanswered?"Unanswered":"Incorrect"}</strong><span>Your answer: {result.user_answer||"Blank"}</span><span>Correct answer: {result.correct_answer}</span>{result.unordered_group&&<span>Letters in this group are graded together; order does not matter.</span>}{result.accepted_answers.length>1&&<span>Accepted alternatives: {result.accepted_answers.join(" / ")}</span>}</span>;
  return <button type="button" className="review-toggle" aria-label={`${a.review.has(q.id) ? "Unmark" : "Mark"} question ${q.number} for review`} aria-pressed={a.review.has(q.id)} onClick={() => a.toggleReview(q.id)}>{a.review.has(q.id) ? "Marked for review" : "Mark for review"}</button>;
}
function Field({ q, g, a, inline = false }: { q: Question; g: Group; a: QuestionActions; inline?: boolean }) {
  const value = a.answers[q.id] ?? "";
  const opts = questionOptions(q, g);
  const select = q.answer_input_type === "single_select" && !["multiple_choice_single"].includes(q.type);
  const max = q.constraints.max_words ?? g.constraints.max_words;
  const over = max !== null && value.trim().split(/\s+/).filter(Boolean).length > max;
  const input = select && opts.length ? <select aria-label={`Answer ${q.number}`} value={value} disabled={a.disabled || a.locked.has(q.id)} onFocus={() => a.focus(q.id)} onChange={(e) => a.change({ [q.id]: e.target.value })}>
    <option value="">Choose…</option>{opts.map((o) => <option key={o.label} value={o.label} disabled={q.type.startsWith("matching_") && !q.constraints.reuse_allowed && !g.constraints.reuse_allowed && g.questions.some((other) => other.id !== q.id && a.answers[other.id] === o.label)}>{o.label === o.text ? o.label : `${o.label} · ${o.text}`}</option>)}
  </select> : <input aria-label={`Answer ${q.number}`} autoComplete="off" autoCapitalize="none" spellCheck={false} value={value} maxLength={500} disabled={a.disabled || a.locked.has(q.id)} aria-invalid={over || undefined} onFocus={() => a.focus(q.id)} onChange={(e) => a.change({ [q.id]: e.target.value })} />;
  return <span className={inline ? "inline-answer" : "answer-field"}>
    {input}{max !== null && <span className={over ? "word-limit over-limit" : "word-limit"}>{over ? "Over word limit · " : ""}Up to {max} {max === 1 ? "word" : "words"}{q.constraints.allow_number ? " and/or a number" : ""}</span>}
  </span>;
}
function Anchor({ q, a, children, inline = false }: { q: Question; a: QuestionActions; children: ReactNode; inline?: boolean }) {
  const Tag = inline ? "span" : "div";
  return <Tag className={inline ? "inline-question" : "reading-question"} data-question={q.number} ref={(node) => a.register(q.id, node)} onFocusCapture={() => a.focus(q.id)}>
    <span className="question-number">{q.number}.</span> {children} <Review q={q} a={a} />
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
    <fieldset className="choice-list"><legend>Choose {limit} letters <span className="muted">· {selected.size} selected</span></legend>{opts.map((o) => <label key={o.label}>
      <input type="checkbox" checked={selected.has(o.label)} disabled={a.disabled || g.questions.some((q) => a.locked.has(q.id)) || (!selected.has(o.label) && selected.size >= limit)} onFocus={() => a.focus(g.questions[0]!.id)} onChange={() => a.change(multipleSelection(g, a.answers, o.label))} />
      <span><strong>{o.label}</strong> {o.text}</span>
    </label>)}</fieldset>{selected.size > 0 && <button type="button" className="text-button" disabled={a.disabled || g.questions.some((q) => a.locked.has(q.id))} onClick={() => a.change(Object.fromEntries(g.questions.map((q) => [q.id, ""])))}>Clear selection</button>}</>;
}
function RadioQuestion({ q, g, a }: { q: Question; g: Group; a: QuestionActions }) {
  return <Anchor q={q} a={a}><fieldset className="choice-list"><legend>{q.prompt}</legend>{questionOptions(q, g).map((o) => <label key={o.label}>
    <input type="radio" name={q.id} checked={a.answers[q.id] === o.label} value={o.label} disabled={a.disabled || a.locked.has(q.id)} onChange={() => a.change({ [q.id]: o.label })} /><span>{o.label === o.text ? o.text : `${o.label}  ${o.text}`}</span>
  </label>)}</fieldset></Anchor>;
}
export function QuestionGroup({ group: g, actions: a, uid, active }: { group: Group; actions: QuestionActions; uid: string; active: boolean }) {
  const imageMode = g.representation === "source_image_with_inputs" || (g.assets.length > 0 && g.questions.some((q) => q.answer_input_type === "multi_select") && !g.options.length);
  const qByNumber = new Map(g.questions.map((q) => [q.number, q]));
  const shown = new Set<number>();
  const segmentNodes = (segments: Segment[]): ReactNode => segments.map((s, i) => {
    if (s.type === "text") return <Fragment key={i}>{s.text}</Fragment>;
    const q = qByNumber.get(s.number);
    if (!q) return <strong key={i} role="alert">Missing question {s.number}</strong>;
    if (shown.has(q.number)) return <span key={i}>[see answer {q.number}]</span>;
    shown.add(q.number);
    return <Anchor key={q.id} q={q} a={a} inline><Field q={q} g={g} a={a} inline /></Anchor>;
  });
  const blocks = (b: Block, i: number): ReactNode => {
    switch (b.type) {
      case "rich_text": return <div className="task-text" key={i}>{segmentNodes(b.segments)}</div>;
      case "heading": return <h3 key={i}>{b.text}</h3>;
      case "list": return <ul className="task-list" key={i}>{b.items.map((item, j) => <li key={j}>{segmentNodes(item)}</li>)}</ul>;
      case "table": return <div className="task-table-scroll" key={i}><table><thead><tr>{b.columns.map((col, j) => <th key={j} scope="col">{col}</th>)}</tr></thead><tbody>{b.rows.map((row, j) => <tr key={j}>{row.map((cell, k) => <td key={k}>{segmentNodes(cell.segments)}</td>)}</tr>)}</tbody></table></div>;
      case "image": { const asset = g.assets.find((asset) => asset.id === b.asset_id); return asset ? <AssetImage key={asset.id} asset={asset} uid={uid} active={active} alt={b.alt} /> : <p key={i} role="alert">Required task image is missing.</p>; }
    }
  };
  const sharedPrompt = g.questions.length > 1 && g.questions.every((q) => q.prompt.trim() === g.questions[0]!.prompt.trim());
  let instructions = g.instructions;
  if (!sharedPrompt && g.questions[0]!.prompt.length > 20) {
    const at = instructions.indexOf(g.questions[0]!.prompt);
    if (at > 0) instructions = instructions.slice(0, at).replace(new RegExp(`\\n\\s*${g.questions[0]!.number}\\s*$`), "").trim();
  }
  const inline = !imageMode && g.questions.every((q) => q.answer_input_type === "text" || q.answer_input_type === "single_select") && g.content_blocks.some((b) => b.type === "rich_text" && b.segments.some((s) => s.type === "blank") || b.type === "table");
  // Compute block nodes now so `shown` correctly tracks fields before fallback rows.
  const content = inline ? g.content_blocks.map(blocks) : null;
  return <section className="question-group" data-question-type={g.type} data-representation={g.representation}>
    <h3 className="group-heading">Questions {g.question_numbers[0]}–{g.question_numbers.at(-1)}</h3>
    {imageMode ? <>{g.assets.map((asset) => <AssetImage key={asset.id} asset={asset} uid={uid} active={active} alt={`Original task, questions ${g.question_numbers.join(", ")}`} />)}<details className="task-transcript"><summary>Task text</summary><p className="task-text">{g.instructions}</p></details></> : inline ? content : <p className="task-instructions">{sharedPrompt && !g.instructions.includes(g.questions[0]!.prompt) ? `${g.instructions}\n${g.questions[0]!.prompt}` : instructions}</p>}
    {!imageMode && g.type === "multiple_choice_multiple" && g.options.length ? <MultiChoice group={g} actions={a} /> : g.questions.filter((q) => !shown.has(q.number)).map((q) => {
      if (q.answer_input_type === "boolean" || q.type === "multiple_choice_single" && questionOptions(q, g).length > 0) return <RadioQuestion key={q.id} q={q} g={g} a={a} />;
      const parts = q.prompt.split(/_{2,}/);
      return <Anchor key={q.id} q={q} a={a}>
        {imageMode || sharedPrompt ? <><span className="source-input-label">Answer {q.number}</span><Field q={q} g={g} a={a} />{q.answer_input_type === "multi_select" && <small>Enter the letter from the source task.</small>}</> : parts.length === 2 && q.answer_input_type === "text" ? <span className="completion-sentence">{parts[0]}<Field q={q} g={g} a={a} inline />{parts[1]}</span> : <><p className="question-prompt">{q.prompt}</p><Field q={q} g={g} a={a} /></>}
      </Anchor>;
    })}
  </section>;
}
