# Phase B verification — 2026-11-01

## Infinite loading: reproduced cause and fix

Before modification, real Chromium at `http://192.168.10.18:3000/reading` still showed Loading after 17 seconds. Network: document and JS chunks 200, **no Reading API request**, repeated failed `ws://192.168.10.18:3000/_next/hmr` handshakes (`ERR_INVALID_HTTP_RESPONSE`). React Fiber properties were absent from main: SSR had not hydrated. Next dev log explicitly reported blocked cross-origin HMR for this LAN host (also 127.0.0.1). The same page at localhost hydrated and showed configuration-unavailable instead of loading.

Added exact Next `allowedDevOrigins` entries. Re-tested LAN: hydration present, loading settled, initially configuration-unavailable; after user supplied real Firebase config, signed-out page displayed Log in. Console: zero errors in the repeated anonymous LAN scenario. Therefore the initial observed loading was caused by dev-origin/hydration, not an API response waiting indefinitely.

Secondary blockers: Firebase Web fields were empty; API pointed to localhost:8000 with no listener. User registered the Web App and filled public Firebase values. API URL was still loopback; changed only web/.env.local API upstream to the known existing HTTPS Alua API. No credentials printed in the report.

Actual read-only HTTP checks: existing `/api/v1/reading/books` without token → 401 `unauthorized`; OPTIONS with LAN Origin and Authorization preflight → 405. Added fixed Next external rewrite `/api/alua/*` to existing FastAPI. Anonymous GET via LAN proxy → same 401. Bearer validation remains on backend; no production CORS/auth settings changed.

## Real production account / LAN browser

User manually entered credentials for an **existing** Alua account. No password was given to the agent. User explicitly confirmed successful sign-in at `/login?next=%2Freading` without errors.

Agent inspected the same Google Chrome window using native browser UI:

- Active `/reading` showed Account and populated Cambridge collection cards, including source numbering/availability reflected by the existing backend. No fake data or browser interception.
- Navigated to `/profile` through a full document load: actual account email and backend display name appeared. Personal values are intentionally omitted here.
- Reloaded the profile using the browser Reload control; refreshed accessibility tree still contained Account and profile data. Session survived refresh.
- Clicked actual Log out. Browser returned home with Log in, then Reading displayed Log in to view practice tests and the return-path login link. Private catalog/profile disappeared.

This verifies actual login (user-performed), redirect to Reading, authenticated catalog, real profile, refresh restoration and logout. The account was signed out during verification. Reading attempts were never started/submitted/reset.

## Actual Firebase SDK with isolated Authentication Emulator

A temporary copied app used demo-alua-web, loopback emulator on 9099, loopback API, no real credentials. Performed via actual forms in Chromium and WebKit, without mocking Firebase methods or HTTP responses:

- Anonymous Reading → login prompt.
- Register → emulator `accounts:signUp` 200.
- Backend unavailable → explicit profile/setup failure; Firebase identity retained.
- Retry account setup → no second signUp request.
- Refresh → same Firebase identity restored.
- Logout/use another account → signed-out form.
- Wrong password → `accounts:signInWithPassword` 400 and generic credential error.
- Correct password → signInWithPassword 200.
- Password reset → `accounts:sendOobCode` 200 and enumeration-safe confirmation.
- Profile logout → home; Reading again required login.

Both final Chromium and WebKit runs passed. Emulator reset acceptance is not a claim about SMTP/inbox delivery. Existing Alua verifier deliberately rejects emulator tokens, so these runs do not claim successful PostgreSQL learner provisioning. API failure in this isolated run was an actual unavailable loopback upstream, not a mock success.

An early WebKit run exposed pre-hydration form submission: SSR inputs were usable before React handlers attached. Inputs and submit now remain disabled during auth initialization, which has a finite deadline. Subsequent Chromium/WebKit runs passed. Another intermediate failure was a test locator colliding with Next’s route-announcer alert; the new tests were narrowed to the form’s alert. Existing tests were not edited.

## Automated targeted verification

- `pnpm typecheck`: Next route generation and strict tsc, exit 0.
- `pnpm lint`: zero warnings/errors, exit 0.
- `pnpm build`: production Turbopack build with actual local Web configuration, exit 0.
- `pnpm test:phase-b`: isolated unconfigured production Webpack build plus **15 passed** checks (9 contract/fault tests; 6 browser scenarios across Chromium, WebKit and mobile WebKit).

Contract tests distinguish exact identity_not_allowed from other 401/403/5xx, verify provisioning payload and retry boundary, safe return paths, non-enumerating error text, malformed catalog fail-closed behavior, one GET token refresh, cancellation and timeout during token initialization. A transient local HTTP fault fixture returned real 503 and stalled a 200 response body; client produced bounded server/timeout errors. This is a failure simulation, not production end-to-end success.

The test runner creates/removes a temporary app copy, empties public configuration for that child build, and never overwrites web/.env.local. Original `contracts.spec.ts` and `public-pages.spec.ts` remain unchanged. Historical Phase A placeholder assertions are not treated as current acceptance tests; original contract tests still run.

## Limits

- No new production Firebase account or new PostgreSQL learner created specifically for testing.
- Production registration/provisioning under new identity, production wrong-password/unknown-user cases, reset email delivery and long-duration automatic token renewal were not exercised against live accounts. SDK flows were exercised in emulator; CAS/registration semantics are existing backend behavior plus targeted client tests.
- No physical iPhone/Android or installed Safari acceptance. WebKit desktop/mobile automation was performed.
- 403/5xx/timeouts were fault/contract scenarios; no deliberate production outage or policy modification.
- No backend deployment/SSH, production environment edit, schema change, SwiftUI edit, commit or push. Git staging remains empty. .env.local and generated build/test artifacts remain ignored.
- Verification servers and emulator stopped after checks; launch the app using the README commands.
