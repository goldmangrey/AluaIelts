import Link from "next/link";
import { PageShell } from "@/components/page-shell";
import { CatalogView } from "@/features/reading/catalog-view";
export const metadata = { title: "Reading" };
export default function Reading() {
  return <PageShell><div className="page-intro"><p className="eyebrow">IELTS Academic</p><h1>Reading.</h1>
    <p className="subtitle">Choose a Cambridge IELTS collection.</p><Link className="text-link" href="/reading/history">My attempts</Link></div><CatalogView /></PageShell>;
}
