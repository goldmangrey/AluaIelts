import { PageShell } from "./page-shell";
export function ComingSoon({ name }: { name: string }) {
  return <PageShell><div className="page-intro"><p className="eyebrow">IELTS Academic</p><h1>{name}.</h1>
    <p className="subtitle">Coming soon.</p></div></PageShell>;
}
