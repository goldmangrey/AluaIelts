import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 3,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure" },
  projects: [
    { name: "contracts", testMatch: "contracts.spec.ts" },
    { name: "chromium", testMatch: "public-pages.spec.ts", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", testMatch: "public-pages.spec.ts", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", testMatch: "public-pages.spec.ts", use: { ...devices["Desktop Safari"] } },
    { name: "mobile", testMatch: "public-pages.spec.ts", use: { ...devices["iPhone 13"] } },
  ],
  webServer: {
    command: "pnpm start --hostname 127.0.0.1 --port 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
    env: {
      NEXT_PUBLIC_API_BASE_URL: "",
      NEXT_PUBLIC_FIREBASE_API_KEY: "",
      NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: "",
      NEXT_PUBLIC_FIREBASE_PROJECT_ID: "",
      NEXT_PUBLIC_FIREBASE_APP_ID: "",
    },
  },
});
