import {reviewJSON, ProviderError} from './providers';
interface EvidenceContext {segments: {id: string; start: number; end: number; text: string}[]; duration: number}
export function validateReview(output: unknown, context: EvidenceContext) {
  const review = reviewJSON(output);
  const texts = ['what_happened','why','next_time'].map(k => review[k] as string);
  if (texts.some(t => !t.trim() || /[<>\x00-\x08]/.test(t))) throw new ProviderError(502);
  const ids = review.segment_ids as string[], quote = review.quote as string;
  if (!ids.length) {
    if (quote !== '') throw new ProviderError(502);
    return review;
  }
  const indexes = ids.map(id => context.segments.findIndex(s => s.id === id));
  if (indexes.some((index, i) => index < 0 || index !== indexes[0]! + i)) throw new ProviderError(502);
  const chosen = indexes.map(i => context.segments[i]!);
  const first = chosen[0]!, last = chosen[chosen.length - 1]!;
  if (!quote.trim() || !chosen.map(s => s.text.trim()).join(' ').includes(quote) ||
      !Number.isFinite(context.duration) || !Number.isFinite(first.start) || !Number.isFinite(last.end) ||
      first.start < 0 || last.end <= first.start || last.end - first.start > 60 || last.end > context.duration)
    throw new ProviderError(502);
  return review;
}
