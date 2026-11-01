import { Suspense } from "react";
import { PageShell } from "@/components/page-shell";
import { AuthForm } from "@/features/auth/auth-form";
export const metadata = { title: "Log in" };
export default function Page() { return <PageShell><Suspense fallback={<p className="loading-text" role="status">Loading account form…</p>}><AuthForm mode="login" /></Suspense></PageShell>; }
