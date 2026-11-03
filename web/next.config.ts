import type { NextConfig } from "next";

const config: NextConfig = {
  poweredByHeader: false,
  // Exact development hosts only; does not change FastAPI CORS or production.
  allowedDevOrigins: ["127.0.0.1", "192.168.10.18"],
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
