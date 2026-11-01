import type { NextConfig } from "next";

const upstream = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
const config: NextConfig = {
  poweredByHeader: false,
  // Exact development hosts only; does not change FastAPI CORS or production.
  allowedDevOrigins: ["127.0.0.1", "192.168.10.18"],
  async rewrites() {
    if (!upstream) return [];
    const url = new URL(upstream);
    if (url.username || url.password || url.search || url.hash ||
        !(url.protocol === "https:" || (url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname)))) {
      throw new Error("API_BASE_URL must be HTTPS or a local loopback API URL.");
    }
    // Fixed configured upstream, no user-controlled forwarding or auth bypass.
    return [{ source: "/api/alua/:path*", destination: `${upstream}/:path*` }];
  },
  async headers() {
    return [{ source: "/api/alua/:path*", headers: [{ key: "Cache-Control", value: "no-store" }] }, { source: "/:path*", headers: [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
    ] }];
  },
};
export default config;
