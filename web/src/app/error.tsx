"use client";
import { PageShell } from "@/components/page-shell";
import { StatusPanel } from "@/components/status-panel";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <PageShell><StatusPanel title="This page couldn’t load." retry={reset}>
    Please try again in a moment.
  </StatusPanel></PageShell>;
}
