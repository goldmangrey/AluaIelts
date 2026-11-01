import Link from "next/link";
import { AccountLink } from "@/features/auth/account-link";

export function SiteHeader() {
  return <header className="site-header"><div className="header-inner">
    <Link className="wordmark" href="/" aria-label="Alua home">alua.</Link>
    <AccountLink />
  </div></header>;
}
