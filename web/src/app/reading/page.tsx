import {LuaMascot} from '@/components/lua-mascot';
import {PersonalLink} from "@/features/auth/guest-access";
import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { CatalogView } from "@/features/reading/catalog-view";
import styles from "@/features/reading/library.module.css";

export const metadata = { title: "Reading" };

export default function Reading() {
  return <><SiteHeader /><main id="main" className={styles.library}>
    <nav className={styles.navigation} aria-label="Reading navigation">
      <Link href="/"><span aria-hidden="true">←</span> All sections</Link>
      <PersonalLink href="/reading/history">My attempts <span aria-hidden="true">↗</span></PersonalLink>
    </nav>
    <div className={styles.intro}>
      <p className={styles.eyebrow}>IELTS Academic</p>
      <h1 style={{display:"flex",alignItems:"center",gap:16}}>Reading. <LuaMascot emotion="scholar" size={88}/></h1>
      <p className={styles.subtitle}>Cambridge IELTS Academic</p>
    </div>
    <CatalogView />
  </main></>;
}
