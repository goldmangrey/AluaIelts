"use client";
import Link from "next/link";
import { useSession } from "./session";
export function AccountLink() {
  const session = useSession();
  return <Link className="account-link" href={session.user ? "/profile" : "/login"}>
    {session.user ? "Account" : "Log in"} <span aria-hidden="true">↗</span>
  </Link>;
}
