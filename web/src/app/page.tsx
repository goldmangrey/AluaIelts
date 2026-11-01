import Link from "next/link";
import { SiteHeader } from "@/components/site-header";

const sections = [
  { name: "Listening", href: "/listening", label: "Coming soon" },
  { name: "Reading", href: "/reading", label: "Practice tests" },
  { name: "Writing", href: "/writing", label: "Coming soon" },
  { name: "Speaking", href: "/speaking", label: "Coming soon" },
];
export default function Home() {
  return <><SiteHeader /><main id="main" className="home">
    <div className="home-intro"><p className="eyebrow">IELTS Academic</p><h1>Practice tests.</h1>
    <p className="subtitle">Four sections. One place to prepare.</p></div>
    <nav className="section-grid" aria-label="IELTS sections">{sections.map((section, i) =>
      <Link href={section.href} key={section.href} className={`section-card ${section.name === "Reading" ? "reading-card" : ""}`}>
        <span className="section-number">0{i + 1}</span>
        <div className="section-card-bottom"><h2>{section.name}</h2>
          <div className="card-meta"><span>{section.label}</span><span className="card-arrow" aria-hidden="true">→</span></div>
        </div>
      </Link>)}
    </nav>
  </main></>;
}
