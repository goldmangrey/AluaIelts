/** Local publication gate: real server projection, frontend parser and static Renderer. No network. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(web);
const require = createRequire(path.join(web, 'package.json'));
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const argument = (name) => {
  const index = process.argv.indexOf(name);
  if (index < 0) return null;
  if (!process.argv[index + 1] || process.argv[index + 1].startsWith('--')) throw Error(`Missing ${name}`);
  return path.resolve(process.argv[index + 1]);
};
const base = argument('--dataset') || path.join(root, 'backend/app/content/reading_v1');
const baseline = argument('--baseline');
const python = process.env.READING_PYTHON || path.join(root, 'backend/.venv/bin/python');
// Explicit public projection only: answer keys never enter the Node/UI process.
const data = JSON.parse(execFileSync(python, ['-c', `
import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from app.modules.reading.catalog import ReadingCatalog
c=ReadingCatalog(Path(sys.argv[2]))
print(json.dumps([{'exam':c.public_exam(e),'enabled':c.entries[eid]['enabled_for_private_practice'],
 'reasons':c.entries[eid]['exclusion_reasons']} for eid,e in c.exams.items()]))
`, path.join(root, 'backend'), base], { maxBuffer: 30_000_000 }));
const modules = new Map();
function compile(file) {
  if (modules.has(file)) return modules.get(file);
  const exports = {};
  modules.set(file, exports);
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  new Function('require', 'exports', 'process', code)((id) => {
    if (id.endsWith('.module.css')) return { default: new Proxy({}, { get: (_, key) => String(key) }) };
    // SSR checks the image reference; bytes, dimensions and checksum are checked below.
    if (id === './asset-image') return { AssetImage: ({ asset, alt }) => React.createElement('img', { 'data-asset': asset.id, alt }) };
    if (id === '@/lib/api/client') return { ApiError: class extends Error {} };
    if (id.startsWith('.')) {
      const local = path.resolve(path.dirname(file), id);
      return compile([local, `${local}.ts`, `${local}.tsx`].find((f) => fs.existsSync(f)));
    }
    return require(id);
  }, exports, process);
  return exports;
}
const { parseExam } = compile(path.join(web, 'src/features/reading/exam/parse.ts'));
const { QuestionGroup, questionIntegrity, questionOptions } = compile(path.join(web, 'src/features/reading/exam/question-renderer.tsx'));
const manifest = JSON.parse(fs.readFileSync(path.join(base, 'manifest.json')));
const hash = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const norm = (value) => String(value).replace(/\s+/g, ' ').trim();
const visibleText = (html) => norm(html.replace(/<[^>]*>/g, ' ').replace(/&amp;/g, '&').replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>'));
const errors = [], blocked = [], types = {}, representatives = {};
let groups = 0, questions = 0, assets = 0;
for (const { exam, enabled, reasons } of data) {
  const issues = [];
  const add = (id, message) => issues.push(`${id}: ${message}`);
  parseExam(exam); // Also rejects private answer fields.
  const entry = manifest.exams.find((row) => row.id === exam.id);
  const raw = JSON.parse(fs.readFileSync(path.join(base, entry.exam_path)));
  const old = baseline && JSON.parse(fs.readFileSync(path.join(baseline, entry.exam_path)));
  if (baseline && hash(fs.readFileSync(path.join(base, entry.answer_key_path))) !== hash(fs.readFileSync(path.join(baseline, entry.answer_key_path)))) errors.push(`${exam.id}: answer key bytes changed`);
  const all = exam.passages.flatMap((p) => p.question_groups.flatMap((g) => g.questions));
  if (JSON.stringify(all.map((q) => q.number)) !== JSON.stringify(Array.from({ length: 40 }, (_, i) => i + 1))) add(exam.id, 'positions must be exactly 1–40');
  if (old) {
    const mapping = (e) => e.passages.flatMap((p) => p.question_groups.flatMap((g) => g.questions.map((q) => [p.id, g.id, q.id, q.number, q.answer_input_type])));
    if (JSON.stringify(mapping(old)) !== JSON.stringify(mapping(exam))) errors.push(`${exam.id}: question/answer mapping changed`);
  }
  for (const passage of exam.passages) for (const group of passage.question_groups) {
    groups++; questions += group.questions.length;
    types[group.type] = (types[group.type] || 0) + 1;
    representatives[group.type] ||= group.id;
    for (const message of questionIntegrity(group)) add(group.id, message);
    const imageMode = group.representation === 'source_image_with_inputs' || (group.assets.length && group.questions.some((q) => q.answer_input_type === 'multi_select') && !group.options.length);
    const html = renderToStaticMarkup(React.createElement(QuestionGroup, {
      group, uid: 'local-content-gate', active: true,
      actions: { answers: {}, review: new Set(), locked: new Set(), disabled: false, change() {}, toggleReview() {}, register() {}, focus() {} },
    }));
    const shown = visibleText(html.replace(/<dialog\b[\s\S]*?<\/dialog>/g, ''));
    for (const q of group.questions) {
      if (q.id !== `${exam.id}-q-${String(q.number).padStart(2, '0')}` || q.group_id !== group.id) add(q.id, 'invalid identity');
      if ((html.match(new RegExp(`data-question="${q.number}"`, 'g')) || []).length !== 1) add(q.id, 'answer anchor missing/duplicated');
      const opts = questionOptions(q, group), labels = opts.map((o) => o.label);
      const allowed = q.constraints.allowed_values.length ? q.constraints.allowed_values : group.constraints.allowed_values;
      if (!imageMode && new Set(labels).size !== labels.length) add(q.id, 'duplicate option label');
      if (!imageMode && ['single_select', 'multi_select'].includes(q.answer_input_type) && !labels.length) add(q.id, 'missing answer bank');
      if (!imageMode && allowed.some((value) => !labels.includes(value))) add(q.id, 'saved value has no displayed option');
      if (!imageMode && opts.some((o) => norm(o.text) !== norm(o.label) && !shown.includes(norm(o.text)))) add(q.id, 'option text omitted');
      if (q.constraints.selection_count && labels.length && q.constraints.selection_count > labels.length) add(q.id, 'invalid selection count');
      if (group.type === 'matching_headings') {
        const label = q.prompt.match(/\b(?:Paragraph|Section)\s+([A-Z])\b/i)?.[1];
        if (label && !passage.content.some((b) => b.label === label)) add(q.id, 'missing heading paragraph label');
      }
    }
    if (group.type === 'matching_information') {
      const labels = group.constraints.allowed_values;
      if (!labels.length || labels.some((label) => !passage.content.some((b) => b.label === label))) add(group.id, 'missing referenced paragraph labels');
    }
    if (!norm(group.instructions)) add(group.id, 'missing instructions');
    const blanks = [];
    for (const block of group.content_blocks) {
      const segments = block.type === 'rich_text' ? block.segments : block.type === 'list' ? block.items.flat() : block.type === 'table' ? block.rows.flat().flatMap((c) => c.segments) : [];
      blanks.push(...segments.filter((s) => s.type === 'blank').map((s) => s.number));
      if (!imageMode && block.type === 'table' && (!html.includes('<table') || block.rows.some((r) => r.length !== block.columns.length))) add(group.id, 'broken table');
      if (block.type === 'image' && !html.includes(`data-asset="${block.asset_id}"`)) add(group.id, 'image not rendered');
    }
    if (blanks.some((n) => !group.question_numbers.includes(n))) add(group.id, 'blank references unknown position');
    if (group.type === 'diagram_labelling' && !group.assets.length) add(group.id, 'missing diagram');
    const rawGroup = raw.passages.flatMap((p) => p.question_groups).find((g) => g.id === group.id);
    for (const asset of rawGroup.assets) {
      assets++;
      const file = path.resolve(base, asset.path);
      if (!file.startsWith(base + path.sep)) throw Error('Asset path escapes dataset');
      const bytes = fs.readFileSync(file);
      if (hash(bytes) !== asset.sha256 || bytes.toString('hex', 0, 8) !== '89504e470d0a1a0a' || bytes.readUInt32BE(16) !== asset.width || bytes.readUInt32BE(20) !== asset.height) add(group.id, 'invalid image bytes/dimensions/hash');
    }
  }
  if (enabled) errors.push(...issues);
  else blocked.push({ exam: exam.id, reasons, contentIssues: [...new Set(issues)] });
}
console.log(JSON.stringify({ exams: data.length, enabled: data.filter((e) => e.enabled).length, groups, questions, assets, types, representatives, blocked, errors }, null, 2));
if (errors.length) process.exitCode = 1;
