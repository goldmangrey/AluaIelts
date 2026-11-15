import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: { default: "Alua — IELTS Academic practice", template: "%s · Alua" },
  description: "Four sections. One place to prepare. IELTS Academic practice with Alua.",
  metadataBase: new URL("https://alua.study"),
  openGraph: {
    title: "Alua IELTS",
    description: "Practice IELTS Listening, Reading, Writing and Speaking with Alua.",
    type: "website",
    url: "https://alua.study",
    images: [{ url: "https://alua.study/social/alua-ielts-cfc052ca7588.png", width: 1448, height: 1086, type: "image/png", alt: "Alua IELTS" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Alua IELTS",
    description: "Practice IELTS Listening, Reading, Writing and Speaking with Alua.",
    images: ["https://alua.study/social/alua-ielts-cfc052ca7588.png"],
  },
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><a className="skip-link" href="#main">Skip to content</a>{children}</body></html>;
}
