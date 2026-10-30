# Local release candidate — release gates

Production baseline reported by owner: `20261029_0002` (Stage 1).
Required backend: Stage 2 `20261030_0003`, then Stage 3 `20261031_0004`.
Stage 5 adds no PostgreSQL schema or SRS algorithm migration.

## Before any production installation

- [ ] Owner confirms an external automatic backup exists, its retention/location/access, and a successful restore test. **Unconfirmed: release blocker.**
- [ ] Preserve a verified backup of PostgreSQL and current Stage 1 backend/iOS artifacts.
- [ ] Review the backend source bundle/checksums and additive migrations 0003 → 0004.
- [ ] Explicitly approve and perform the backend update. No production update was performed by this task.
- [ ] Confirm the deployed Alembic head is `20261031_0004` and all old endpoints remain compatible.
- [ ] Authenticated smoke test of `/study/today`, `/study/book`, `/study/actions` with both existing learner IDs.
- [ ] Confirm old history, grammar, diagnostics, device enrollments and current tokens remain accessible.
- [ ] Only then install the signed RC on the two enrolled physical iPhones. The new app requires Stage 3 APIs.

## Compatible update order

1. Confirm backup and restore; record counts/IDs of profiles, enrollments, old review states/events and daily plans.
2. Supply the complete backend app/content and migration source in the bundle. Keep production secrets outside it. Preserve existing identity configuration. Disable remote exercise/progress AI for the deterministic vocabulary course.
3. Run the reviewed additive upgrades from 0002 through 0003 to 0004 in the approved production maintenance process. Never recreate the schema or import a fresh test database.
4. Start the compatible backend; verify auth and existing Stage 1 clients before updating either phone.
5. Test Stage 3 endpoints with authorized devices and isolated smoke actions as agreed with the owner.
6. Install the RC, one phone at a time; verify resume/history before the second phone.

## Physical smoke test, on BOTH iPhones

- [ ] Existing Keychain enrollment restores without a fresh code. Correct learner and prior history.
- [ ] Today → 10 cards → pause → close → resume on card 11; later restart at 18/30 resumes on card 19.
- [ ] A different calendar date does not skip an incomplete day. Complete 30; next day unlocks in Asia/Almaty.
- [ ] Completed day remains in Book; English/Russian search; topic views; hidden filter; restore a hidden card.
- [ ] Review from Book records an answer only after Check/Не знаю, with manual Next.
- [ ] Airplane mode: an answer is durably queued. Relaunch; reconnect; same UUID is acknowledged once. Do not delete the app.
- [ ] Add **Alua Glance** to a rectangular Lock Screen slot. No Russian answer is visible.
- [ ] Tap the visible term: that exact term opens. Simply opening/closing does not change review counts.
- [ ] Submit a reply; after sync the widget no longer offers the answered card as immediately due. Wait for WidgetKit refresh scheduling.
- [ ] Hide a due card; old widget link opens ordinary reviews, not a scored hidden-card response.
- [ ] Check stale/expired URL and a link from the other learner: fallback without mutation.
- [ ] Switch away/back and verify no other learner's snapshot or queue is applied.
- [ ] Confirm My Book and review still work after completion of Day 50 (automated isolated DB test covers the full course).
- [ ] Grammar, practice and the 12-question diagnostic remain accessible.

## Accessibility walkthrough

Settings → Accessibility → Display & Text Size → Larger Text. Test long English expressions and Russian examples on both phones. All content must remain vertically scrollable.

Enable VoiceOver using the device shortcut or Settings → Accessibility → VoiceOver. Swipe through Today, one lesson, Book, a card, one correct and one incorrect review answer, then the Lock Screen widget. Check the reading order, progress announcement, selected answer, close/settings labels, keyboard and return focus. Automated layout/label tests are not a substitute for this walkthrough.

## Safe app rollback

- Keep backend schema at 0004 and preserve both legacy and Stage 3 endpoints. Do NOT downgrade/drop learning tables or erase history.
- Before installing an earlier app build, get all offline queues acknowledged and confirm Book/history on the server. Keep local device data and Keychain.
- Use the same bundle identifier, team and App Group. Do not delete/reinstall the app or reset device enrollment to perform a rollback.
- Prefer a signed forward-fix retaining the Stage 3 queue contract. An older Stage 1 app will not drain a Stage 3 offline queue.
- If database restore becomes necessary, stop writes and use the independently verified backup/restore process under owner approval. Application rollback alone is not a reason to restore/delete the database.

## Release status

A signed development RC is not an App Store/TestFlight production release. Production deployment, external backup confirmation and the two-phone smoke/accessibility checks remain explicit gates.
