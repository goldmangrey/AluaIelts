# Reading library redesign — local review

Date: 2026-11-02

Production files changed:
- `src/app/reading/page.tsx`
- `src/features/reading/catalog-view.tsx` (collection index markup only)
- `src/features/reading/library.module.css` (scoped styles)

Test file changed: `tests/reading-release-browser.spec.ts`.

The catalog still uses the existing authenticated FastAPI `/reading/books` request,
parser, availability filter, ordering and collection routes. No API, Firebase,
global CSS, homepage, exam engine or Cloudflare configuration changes were made
for this task. Existing unrelated workspace changes were preserved.

## Validation

- `pnpm typecheck`: passed.
- `pnpm lint`: passed.
- `pnpm build`: passed.
- `pnpm build:workers`: passed; `.open-next/worker.js` generated.
- Existing release suite: all 30 existing contract/browser/mobile tests passed.
- New library checks: all 4 passed in Chromium and WebKit on the final focused run:
  `pnpm test:reading-release --grep 'Reading library'`.
- Initial full run had 3 failures in the new tests: two ambiguous Login selectors
  and WebKit's macOS link tabbing behavior. Corrected test selectors and used
  Option+Tab for WebKit; no production code changes were needed.
- Checked widths 320, 390, 430, 768 and 1440; no horizontal overflow or clipped row titles.
- Checked collection URLs and Enter navigation, My attempts navigation,
  Account/Login links, hover, focus outline and reduced motion.
- Checked loading, empty, 503/retry, 403 and signed-out states.
- The existing home → collection → preparation → exam → result → review → history
  workflow passed in Chromium and WebKit; mobile exam workflows passed as well.

## Screenshots

- `desktop.png`: 1440 × 900, authenticated test identity.
- `mobile.png`: 390 × 844, authenticated test identity.
- `local-session.png`: actual local production build, signed out.

Catalog screenshots use the existing isolated release-test app with an API response
fixture derived from validated local backend content (63 enabled exams), not live
production account data. Production code has no fixture or authentication override.
The local production build was also opened at `http://127.0.0.1:3100/reading` and
showed the expected signed-out state. A real Firebase sign-in and live authenticated
FastAPI request were not performed.

No known design deviations. Ready for local visual approval before deployment.
No commit, push, upload or deployment performed.
