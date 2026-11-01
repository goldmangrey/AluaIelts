import { PageShell } from "@/components/page-shell";
import { ProfileView } from "@/features/auth/profile-view";
export const metadata = { title: "Your account" };
export default function Page() { return <PageShell><ProfileView /></PageShell>; }
