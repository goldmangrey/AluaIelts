import { Suspense } from "react";
import Link from "next/link";
import { AuthForm } from "@/features/auth/auth-form";
import s from "@/features/auth/login.module.css";
export const metadata = { title: "Log in" };
export default function Page() { return <div className={s.page}><header className={s.header}>
  <Link href="/" className={s.wordmark} aria-label="Alua home">alua<span>.</span></Link>
  <Link href="/" className={s.homeLink}>Back to home <span aria-hidden="true">↗</span></Link>
  </header><main id="main" className={s.main}><Suspense fallback={<p role="status">Loading account form…</p>}><AuthForm mode="login" /></Suspense></main></div>; }
