import Link from "next/link";
import { SiteHeader } from "./site-header";

export function PageShell({ children, backHref = "/", backLabel = "All sections" }: {
  children: React.ReactNode; backHref?: string; backLabel?: string;
}) {
  return <><SiteHeader /><main id="main" className="page-shell">
    <Link className="back-link" href={backHref}><span aria-hidden="true">←</span> {backLabel}</Link>
    {children}
  </main></>;
}
