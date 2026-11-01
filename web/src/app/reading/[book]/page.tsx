import { notFound } from "next/navigation";
import { PageShell } from "@/components/page-shell";
import { CatalogView } from "@/features/reading/catalog-view";
import { parseBook } from "@/features/reading/routes";
export default async function Book({ params }: { params: Promise<{ book: string }> }) {
  const { book } = await params;
  const number = parseBook(book);
  if (!number) notFound();
  return <PageShell backHref="/reading" backLabel="Reading"><div className="page-intro">
    <p className="eyebrow">Academic Reading</p><h1>Cambridge {String(number).padStart(2, "0")}.</h1>
    <p className="subtitle">Choose a practice test.</p></div><CatalogView key={number} bookNumber={number} /></PageShell>;
}
