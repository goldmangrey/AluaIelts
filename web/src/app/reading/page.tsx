import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { CatalogView } from "@/features/reading/catalog-view";
import styles from "@/features/reading/library.module.css";

export const metadata = { title: "Reading" };

export default function Reading() {
  return <><SiteHeader /><main id="main" className={styles.library}>
    <nav className={styles.navigation} aria-label="Reading navigation">
      <Link href="/"><span aria-hidden="true">←</span> All sections</Link>
      <Link href="/reading/history">My attempts <span aria-hidden="true">↗</span></Link>
    </nav>
    <div className={styles.intro}>
      <p className={styles.eyebrow}>IELTS Academic</p>
      <h1>Reading.</h1>
      <p className={styles.subtitle}>Cambridge IELTS Academic</p>
    </div>
    <CatalogView />
  </main></>;
}
