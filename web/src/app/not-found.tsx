import { PageShell } from "@/components/page-shell";
import { StatusPanel } from "@/components/status-panel";
export default function NotFound() {
  return <PageShell><StatusPanel title="Page not found." href="/" label="Back to all sections">
    This page is unavailable. Choose a section to continue.
  </StatusPanel></PageShell>;
}
