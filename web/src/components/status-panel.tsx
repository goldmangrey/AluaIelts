import Link from "next/link";

export function StatusPanel({ title, children, href, label, retry }: {
  title: string; children: React.ReactNode; href?: string; label?: string; retry?: () => void;
}) {
  return <section className="status-panel" aria-live="polite"><h2>{title}</h2><p>{children}</p>
    {href && <Link className="text-link" href={href}>{label} <span aria-hidden="true">→</span></Link>}
    {retry && <button className="button secondary" onClick={retry}>Try again</button>}
  </section>;
}
