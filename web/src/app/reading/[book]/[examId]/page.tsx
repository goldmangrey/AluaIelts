import { notFound } from "next/navigation";
import { PageShell } from "@/components/page-shell";
import { CatalogView } from "@/features/reading/catalog-view";
import { matchesExamBook, parseBook } from "@/features/reading/routes";
export default async function Test({ params }: { params: Promise<{ book: string; examId: string }> }) {
  const { book, examId } = await params;
  const number = parseBook(book);
  if (!number || !matchesExamBook(examId, number)) notFound();
  const testNumber = Number(examId.split("-").at(-1));
  return <PageShell backHref={`/reading/${book}`} backLabel={`Cambridge ${String(number).padStart(2, "0")}`}>
    <div className="page-intro"><p className="eyebrow">Cambridge IELTS {String(number).padStart(2, "0")}</p>
      <h1 className="test-title">Academic Reading.</h1><p className="subtitle">Test {testNumber}</p></div>
    <CatalogView key={examId} bookNumber={number} examId={examId} />
  </PageShell>;
}
