import type {Module} from './api';

export const skills: Module[] = ['listening', 'reading', 'writing', 'speaking'];
export const human = (value: string) => value.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
export type Point = {id: string; title: string; date: string; value: number; attempt_number: number; attempt_count: number};
export type Chart = {points: Point[]; scale: number; truncated: boolean};
export type FocusArea = {module: Module; category: string; attempts: number; distinct_tests: number; answered: number; incorrect: number; unanswered: number; not_graded: number; incorrect_attempts: number};
export type Criterion = {criterion: string; band: number; assessments: number};
export type Analytics = {
  counts: Record<Module, number>;
  mistakes: {total: number; reviewed: number};
  charts: Partial<Record<Module, Chart>>;
  weak_areas: FocusArea[];
  writing_criteria: Criterion[];
  speaking_assessment_available: boolean;
};

export function limited(area: FocusArea) {
  return area.distinct_tests < 2 || area.answered < 10 || area.incorrect_attempts < 2;
}
/** Recurring errors across tests outrank small samples; rate alone never sets priority. */
export function rankFocusAreas(areas: FocusArea[]) {
  const weight = (a: FocusArea) => a.incorrect * (a.answered / (a.answered + 10))
    * Math.min(a.distinct_tests, 4) * (1 + Math.min(a.incorrect_attempts, 5) / 5);
  return areas.filter(a => a.answered > 0 && a.incorrect > 0).toSorted((a, b) =>
    Number(limited(a)) - Number(limited(b)) || weight(b) - weight(a) || a.category.localeCompare(b.category));
}
