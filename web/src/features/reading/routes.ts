// Syntax validation only. Availability always comes from the authenticated API.
export function parseBook(slug: string): number | null {
  const match = /^cambridge-([1-9]\d?)$/.exec(slug);
  return match?.[1] ? Number(match[1]) : null;
}
export function matchesExamBook(examId: string, book: number): boolean {
  return new RegExp(`^cambridge-${String(book).padStart(2, "0")}-test-\\d{2}$`).test(examId);
}
