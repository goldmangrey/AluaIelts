> Исторический отчёт Phase A. Актуальные проверки авторизации: [Phase B](PHASE_B_VERIFICATION.md).

# Phase A verification — 2026-11-01

## Environment

macOS ARM64, Node 22.21.1, pnpm 12.14.0. Next.js 16.4.3, React 19.3.1, TypeScript 5.9.3. Public env not populated; no actual Firebase sign-in. Production backend and PostgreSQL were not contacted.

## Completed checks

| Check | Result |
|---|---|
| `pnpm install --frozen-lockfile` | Exit 0, lockfile current |
| `pnpm peers check` | No peer dependency issues |
| `pnpm typecheck` | Exit 0, Next route generation + strict tsc |
| `pnpm lint` | Exit 0, zero warnings |
| `pnpm build` | Exit 0, all routes built |
| `pnpm audit --prod` | No known vulnerabilities after scoped gRPC override |
| `pnpm exec playwright test --project=chromium` | 3 passed |
| `pnpm exec playwright test --project=webkit --project=mobile` | 6 passed |
| `pnpm exec playwright test --project=firefox --project=contracts` | 7 passed |
| Local `ReadingCatalog()` projection through web runtime validator | 17 visible books, 63 enabled tests; Cambridge 12 Test 5–8 preserved |
| `git diff --exit-code -- backend frontend` | Exit 0, existing tracked files unchanged |
| `git diff --cached --name-only` | Empty; nothing staged |
| Ignore checks | node_modules, .next, .env.local, tsbuildinfo, test-results ignored |

16 final scenarios passed across the listed Playwright commands. Contract fixtures stay in tests and are never imported by production. Real catalog validation was run with transient `/tmp` metadata, not a dataset copy inside web.

Browser tests cover the exact four-card home layout; 2 columns desktop / 1 column mobile; no horizontal overflow; skip-link focus; navigation; all Coming soon pages; Reading unavailable state; book/test route shells; original source numbering; invalid book/exam combinations; not-found; explicit future-auth messaging with no credentials collected. Contract tests cover filtering disabled/blocked entries, malformed/duplicate/mismatched responses, token refresh retry bounds, 403, invalid JSON, absent session and cancellation during token retrieval.

WebKit tests use Option-Tab for link traversal, matching [Safari’s default keyboard navigation](https://help.apple.com/safari/mac/8.0/en.lproj/cpsh003.html). Initial Tab-only assertion failed in WebKit; explicit reproduction showed browser-default behavior, and the test was corrected without changing website keyboard handling. Chromium and Firefox use Tab.

Manual Playwright inspection: home at 1440×1000 and 390×844; Reading at 390×844. Screenshots reviewed; spacing and approved card composition verified. Initial missing favicon 404 fixed. Final home console: 0 errors, 0 warnings; no hydration/page exceptions in final public scenarios. Both production server and dev server opened locally. Runtime files/screenshots are ignored and not part of deliverable source.

## Not claimed

- No end-to-end Firebase login, registration, password reset, provisioning or authenticated HTTP catalog scenario. These need Phase B and real public Web configuration + account, with existing backend CORS configured for the web origin.
- No visual acceptance of the populated catalog/test preparation against a signed-in browser. Data parsing/filtering was checked against the actual backend catalog independently of HTTP/auth.
- WebKit automation is not a test on physical iPhone or installed Safari; Chromium/Firefox automation is not manual Chrome/Firefox acceptance. Physical iOS/Android, assistive technology, actual browser zoom and full performance metrics remain Phase F.
- No Reading renderer, attempts, save/recovery, timer, submit or results. No fake start/result, no user state mutation.
- No full backend test suite rerun: backend unchanged. Existing tests/contracts read; actual content loader validations executed.
- No deployment, SSH, commit, push, production settings changes or secret-file staging.
