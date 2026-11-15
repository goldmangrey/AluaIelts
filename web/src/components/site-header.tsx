import Link from "next/link";
import { PersonalNavigation } from "@/features/auth/guest-access";

export function SiteHeader() {
  return <header className="site-header"><div className="header-inner">
    <Link className="wordmark" href="/" aria-label="Alua home">alua.</Link>
    <PersonalNavigation className="account-nav"/>
  </div></header>;
}
