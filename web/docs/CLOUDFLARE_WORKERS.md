# Alua Web on Cloudflare Workers

## Audited configuration

Existing App Router application, without migration or UI changes. Verified with Node 26.12.0, pnpm 12.14.0, Next.js 16.4.3, React 19.3.1, `@opennextjs/cloudflare` 1.20.15 and Wrangler 4.156.0. OpenNext supports this Next version; vinext is unnecessary. `build` remains `next build` (Turbopack).

Worker name: `alua-ielts`. Compatibility date `2026-10-23` matches the installed workerd binary; `nodejs_compat` and `global_fetch_strictly_public` are enabled. The only bindings are static assets and the Worker's own service reference. Public prerendered shells use the read-only static assets incremental cache. There is no ISR, R2, KV, D1 or additional backend. Private Reading data remains in FastAPI and the existing browser storage.

## Environment

Set these **Build variables** in Cloudflare Workers Builds, using the existing Firebase Web app's values from your local configuration:

```dotenv
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
NEXT_PUBLIC_API_BASE_URL=https://alua-api.flora-flowers.kz/api/v1
```

These public identifiers and the fixed upstream URL are inlined by Next.js at **build time**. Runtime variables alone cannot configure an already built bundle: rebuild after a change. No Firebase Admin key, service account, database password or second authentication backend is needed. No required runtime secret is introduced. Leave the optional Auth Emulator URL unset for production.

Local builds read the existing `.env.local`. Local preview can optionally use `.dev.vars` based on `.dev.vars.example` (`NEXTJS_ENV=production`); this is not required. `.env.local`, `.dev.vars*`, `.open-next`, `.wrangler` and generated Cloudflare types are ignored. `keep_vars` preserves separately configured dashboard runtime variables on future deploys.

Use the current Firebase project. Email/password login does not add OAuth redirects or custom reset continue URLs. Check the eventual HTTPS hostname against any existing API-key HTTP referrer restrictions. Additional Firebase authorised-domain configuration is relevant if enabling domain-dependent auth flows; do not disable restrictions or change the Firebase project for this preparation.

## Fixed server proxy

The browser continues to request `/api/alua/*`. The Route Handler forwards only to the configured Alua upstream, including `/api/v1`. Both relative web-client paths and already prefixed `/api/v1/*` paths are accepted.

The initial external rewrite reached FastAPI in workerd, but did not retain the configured Next response cache header. The adapter's external fetch implementation also had no bounded upstream timeout and followed redirects. A small Node-runtime Route Handler replaces that rewrite so the transport behavior is explicit in both Next and Workers.

- Bearer Authorization, method, JSON/body bytes and upstream status are preserved, including 401/403/409/422/5xx.
- All responses use `Cache-Control: no-store` and `Vary: Authorization`. Cookies and client forwarding headers are not passed. Static immutable caching is restricted to `/_next/static/*`.
- Query/body input cannot select an upstream host. Path segments are validated. Upstream redirects are rejected without forwarding credentials to another origin.
- The 12-second deadline covers request body, upstream fetch and complete response body. Network failure returns 502; timeout returns 504. Bodies are bounded to 4 MiB request / 16 MiB response, including authenticated PNG assets.
- Authorization and response data are not logged by the proxy. Worker observability is disabled in the checked-in configuration.

No FastAPI authentication or CORS setting is changed. The existing `reuse_active` Start contract still requires the compatible backend described in `READING_RELEASE_VERIFICATION.md`; preparing a Worker does not deploy those pre-existing backend changes.

## Local commands

```bash
cd /Users/yeskendir/Projects/Alua/web
pnpm install --frozen-lockfile
pnpm build:workers
pnpm preview:workers --port 8787 --ip 127.0.0.1
```

Open `http://127.0.0.1:8787`. `pnpm preview` builds and then starts the same local workerd preview. `pnpm dev` remains ordinary Next development and is not a substitute for Workers verification. Stop the local preview with Ctrl-C.

```bash
pnpm typecheck
pnpm lint
pnpm test:phase-b
pnpm test:phase-c --workers=1 --timeout=90000
pnpm test:reading-release --workers=1 --timeout=90000
pnpm build:workers
pnpm test:workers
pnpm exec wrangler deploy --dry-run --outdir .wrangler/dry-run
```

The longer Reading test budget allows the existing all-question-family browser scenarios to run on a busy workstation without changing assertions. Run suites sequentially: Phase C and release tests share port 3300. `test:workers` requires the real-config Worker build, creates a disposable app with a frozen dependency install, and runs a second actual workerd against a controlled HTTP upstream. No production user or attempt is created. Temporary fixture apps and servers are removed afterward. Its PNG/status/body/timeout tests are transport fixtures, not claims of production attempt completion.

Optional binding type generation: `pnpm cf:typegen`. Generated runtime globals are excluded from the Next application's TypeScript compilation; this app does not currently use Cloudflare-specific bindings in application code.

## Production deployment — 2026-11-02

Published through the existing Wrangler OAuth session with the user's explicit production-deployment authorization:

- URL: https://alua-ielts.yeskendiriskakov.workers.dev
- Worker: `alua-ielts`
- Version: `fc7f543d-326e-4ac9-a7f0-9e4c22363118`
- Account: the existing authenticated Cloudflare account. No login was required.

```bash
cd /Users/yeskendir/Projects/Alua/web
pnpm run build:workers
pnpm run deploy:workers
```

The deploy command publishes the already built Worker with `--keep-vars`.

Verification in this deployment session:

- Typecheck, lint, production Next build and OpenNext build passed.
- Actual local workerd preview: public and dynamic Reading page shells returned 200. Both `/api/alua/reading/books` and `/api/alua/api/v1/reading/books` returned the existing upstream's 401 with `no-store`.
- Production HTTPS: `/`, `/login`, `/reading`, `/reading/history`, book/exam pages and synthetic-ID result/review page shells returned 200. Both API path forms returned 401 with `no-store`. These page-shell checks do not claim authenticated data access.
- Workers transport suite: 10 tests passed (real upstream unauthenticated request; fixture status/body/bearer, PNG, redirect rejection and timeout). Its browser hydration test could not launch because macOS denied Chromium's Mach port registration.
- Reading release suite: all 12 contract tests passed. Its 18 desktop/mobile browser tests could not launch Chromium/WebKit under the execution restrictions; they did not reach application assertions. No full browser E2E success is claimed.
- Firebase public configuration was present at build time; the read-only Firebase project-config endpoint returned 200. No real account sign-in was performed. The workers.dev hostname is absent from the current authorized-domain list; the existing UI uses email/password auth and Firebase-hosted reset handling, not popup/redirect OAuth. Firebase configuration was left unchanged.
- Published static assets were checked for Cambridge PDF, key/fixture files, source maps and private credential material. None were found. The test-only app containing Reading fixtures was built in a separate temporary directory, never deployed.
- No production Reading attempt was created, saved or finished. No Oracle, FastAPI, PostgreSQL or Firebase project changes, Git commit or push were performed in this deployment session.

## Cloudflare GitHub integration

After reviewing and committing these files yourself, use **Workers & Pages → Create → Import a repository**, choose the existing Alua GitHub repository, and configure **Workers Builds** (not a Pages static export):

| Setting | Value |
| --- | --- |
| Worker name | `alua-ielts` |
| Production branch | `main` |
| Root directory | `web` |
| Build command | `pnpm run build:workers` |
| Deploy command | `pnpm run deploy:workers` |
| Non-production branch/version command, if enabled | `pnpm run upload:workers` |
| Build watch include paths | `web/*` (relative to repository root; includes descendants) |
| Build variable `NODE_VERSION` | `26.12.0` (matches the tested local runtime) |
| Build variable `PNPM_VERSION` | `12.14.0` |
| Public build variables | All six variables listed above |

The packageManager field additionally pins pnpm 12.14.0. Use the committed frozen lockfile; Cloudflare's default pnpm version must not replace it. Do not put Cloudflare API tokens in `NEXT_PUBLIC_*`, repository files or client code. Manage the integration's deploy credentials inside Cloudflare's build settings.

Git integration enables remote builds/deployments on matching pushes once connected; enabling it is a publishing action for the user. No integration was connected here. On the eventual HTTPS deployment, repeat login, refresh, catalog, existing history and existing-attempt/PNG checks without creating attempts solely for testing.

References: [OpenNext setup](https://opennext.js.org/cloudflare/get-started), [static assets caching](https://opennext.js.org/cloudflare/caching), [environment variables](https://opennext.js.org/cloudflare/howtos/env-vars), [Cloudflare build configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/), [build image overrides](https://developers.cloudflare.com/workers/ci-cd/builds/build-image/), [watch paths](https://developers.cloudflare.com/workers/ci-cd/builds/build-watch-paths/).
