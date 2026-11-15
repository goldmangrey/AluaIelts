"use client";
import Link from "next/link";
import { useSession } from "./session";
export function AccountLink({ className = "account-link" }: { className?: string }) {
  const session = useSession();
  if(session.status==="loading")return <span role="status" aria-label="Checking session" style={{minWidth:80,minHeight:44}}/>;
  return <Link className={className} href={session.user ? "/profile" : "/login"}>
    {session.user ? "Profile" : "Log in"} {className === "account-link" ? <span aria-hidden="true">↗</span> : <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg>}
  </Link>;
}
