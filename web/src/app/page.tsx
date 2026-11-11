import Image from "next/image";
import Link from "next/link";
import type { CSSProperties } from "react";
import { AccountLink } from "@/features/auth/account-link";
import s from "./home.module.css";

const sections = [
  { name: "Listening", key: "listening", detail: "4 sections · 40 questions", label: "4 sections, 40 questions", width: 914, height: 960 },
  { name: "Reading", key: "reading", detail: "3 passages · 40 questions", label: "3 passages, 40 questions", width: 960, height: 952 },
  { name: "Writing", key: "writing", detail: "Task 2 · 40 min", label: "Task 2, 40 min", width: 960, height: 957 },
  { name: "Speaking", key: "speaking", detail: "3 parts · 11–14 min", label: "3 parts, 11–14 min", width: 737, height: 960 },
];

export default function Home() {
  return <div className={s.homepage}>
    <header className={`${s.container} ${s.header}`}>
      <Link className={s.wordmark} href="/" aria-label="Alua home">alua<span>.</span></Link>
      <AccountLink className={s.account} />
    </header>
    <main id="main" className={`${s.container} ${s.main}`}>
      <div className={s.hero}><p className={s.eyebrow}>IELTS ACADEMIC<span aria-hidden="true" /></p>
        <h1>Practice tests.</h1><p className={s.subtitle}>Four sections. One place to prepare.</p></div>
      <nav className={s.grid} aria-label="IELTS sections">{sections.map((section, i) =>
        <div className={s.entrance} style={{ "--order": i } as CSSProperties} key={section.key}>
          <Link href={`/${section.key}`} className={`${s.card} ${s[section.key]}`} aria-label={`${section.name}, ${section.label}`}>
            <span className={s.surface} aria-hidden="true" /><span className={s.contactShadow} aria-hidden="true" />
            <Image src={`/images/home/${section.key}.webp`} alt="" width={section.width} height={section.height}
              className={s.object} unoptimized loading={i === 3 ? "lazy" : "eager"} fetchPriority={i === 0 ? "high" : "auto"} />
            <span className={s.number}>0{i + 1}</span>
            <div className={s.details}><h2>{section.name}</h2><p>{section.detail}</p></div>
            <span className={s.arrow} aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 12h15m-6-6 6 6-6 6" /></svg></span>
          </Link>
        </div>)}
      </nav>
    </main>
  </div>;
}
