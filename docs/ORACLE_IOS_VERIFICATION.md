> Авторизация Alua 2.1: команды привязки в этом документе устарели. Используйте [актуальную инструкцию S1](ALUA_2_1_STAGE1_AUTH_TRANSITION.md); публичный bootstrap удалён, новые профили не создаются.

# Oracle API and iOS verification — 2026-10-29

## Changes in this task

- `frontend/Alua/App/AppEnvironment.swift`: Debug and Release fallback hosts now use `https://alua-api.flora-flowers.kz`.
- `frontend/project.yml`: both configurations use that host; explicit generated app Info.plist includes `API_BASE_URL`.
- `frontend/Alua/Info.plist`: XcodeGen-generated app metadata with the API host build-setting substitution.
- `frontend/Alua.xcodeproj/project.pbxproj`: regenerated using XcodeGen.
- This report.

The base URL has no `/api/v1` suffix. Service endpoint paths already contain it; APIClient trims leading slashes and appends the path once. All API-backed services, including WidgetSyncService, receive the same APIClient from DependencyContainer. No Cloud Run endpoint remains in frontend sources/configuration.

The extension compiles only AluaWidgets and AluaShared sources. Those sources contain no networking implementation, bearer tokens, Keychain access, or credentials. WidgetTimelineProvider reads App Group snapshots written by the app. DeviceTokenStore stores the device token in the app's Keychain with AfterFirstUnlockThisDeviceOnly accessibility, without a shared Keychain access group.

## Local validation

XcodeGen and Xcode 27 were used to build the Alua scheme, including its AluaWidgets dependency, for the generic iOS Simulator destination with code signing disabled. Debug and Release passed. Inspecting the built app confirmed API_BASE_URL resolves to the production HTTPS host. The initial generated-Info.plist-only configuration omitted this custom key; the explicit Info.plist fixes that.

FastAPI TestClient used disposable local SQLite databases, with external AI disabled and no production connection:

- All 48 protected API operations rejected anonymous requests with 401.
- Two CLI-generated test codes redeemed into distinct learner UUIDs; reuse, invalid codes and expired codes were rejected.
- Invalid and revoked device tokens were rejected.
- Supplying another learner's UID did not redirect profile reads or writes.
- Each learner listed only their own device; attempts to revoke the other's device returned 404.
- Looking up another learner's stored event, exercise session, vocabulary review session and mastery state returned 404.
- Unlinked partner dashboard access returned 401.
- Guessed HTTP enrollment-generation routes returned 404 for anonymous and enrolled callers. Source inspection confirms generation is only in app.cli; POST /api/v1/enrollment redeems existing codes.

One test assertion initially matched the word enrollment inside `/devices/{enrollment_id}`; inspection confirmed this is the authenticated device-revocation route, not code generation. AI conversation requests returned 503 with AI disabled, so AI authorization was reviewed in source rather than claimed as a successful runtime authorization test. AI services require an active partner relationship, sharing permission and conversation ownership.

Learner repositories scope private records by the authenticated learner ID. The intentional exception is consent-based partner sharing: invited partners can view the configured shared progress. Two independently enrolled learners are not automatically partners.

SQLite validation does not exercise PostgreSQL row locks or concurrent redemption. The PostgreSQL enrollment implementation locks the code row with FOR UPDATE and redeems it in the same transaction as learner/device creation. Temporary test databases were removed automatically; tests ran from stdin, leaving no test scripts.

## Oracle enrollment commands — not executed

The actual entry point is:

```bash
python -m app.cli create-enrollment-code --name 'Learner 1' --ttl-minutes 30
```

Omit `--learner-id` for BOTH new learners. Each code creates a distinct learner upon first redemption. Passing an existing learner ID instead links a device to that existing learner. Codes are random, one-time, expire after the specified TTL, and are stored as SHA-256 hashes; the raw code is printed only by the CLI. Redemption returns a random device bearer token stored by iOS in Keychain.

The repository service example uses user/group `alua`, directory `/opt/alua/backend`, and environment file `/etc/alua/alua.env`. These deployed paths have NOT been confirmed: Oracle was not accessed. The example also has port 8101, whereas the confirmed deployment uses 8010; do not install the example or change the running service.

On Oracle, first inspect only the service metadata (no secret values):

```bash
sudo systemctl show alua.service \
  --property=User --property=Group --property=WorkingDirectory --property=EnvironmentFiles
sudo test -x /opt/alua/backend/.venv/bin/python
```

If those values match the paths/user above, run the following in a private administrator terminal. Otherwise substitute the actual Alua-only paths/user from the running service before running. These transient oneshot commands load the service environment via systemd, avoiding shell-sourcing an environment file or printing DATABASE_URL. They do not restart or deploy the API. `--pipe` sends the codes to the terminal rather than the journal.

```bash
sudo systemd-run --quiet --wait --pipe --collect \
  --property=Type=oneshot \
  --property=User=alua --property=Group=alua \
  --property=WorkingDirectory=/opt/alua/backend \
  --property=EnvironmentFile=/etc/alua/alua.env \
  /opt/alua/backend/.venv/bin/python -m app.cli \
  create-enrollment-code --name 'Learner 1' --ttl-minutes 30

sudo systemd-run --quiet --wait --pipe --collect \
  --property=Type=oneshot \
  --property=User=alua --property=Group=alua \
  --property=WorkingDirectory=/opt/alua/backend \
  --property=EnvironmentFile=/etc/alua/alua.env \
  /opt/alua/backend/.venv/bin/python -m app.cli \
  create-enrollment-code --name 'Learner 2' --ttl-minutes 30
```

Replace display names as desired. Enter the first code on learner 1's iPhone and the second on learner 2's iPhone within 30 minutes. Do not publish terminal output or add a generation HTTP endpoint. No production codes were generated in this task.

## Remaining validation

- Confirm actual Oracle unit/environment/interpreter paths before using the commands.
- Production authorization, live enrollment and PostgreSQL concurrency remain untested because Oracle access was prohibited.
- Physical-device installation requires your signing team/profiles and App Group provisioning; simulator builds do not verify these or live widget refresh after enrollment.

No remote deployment, Oracle access, FLORA modification, commit or push was performed. Existing unrelated uncommitted work was retained. No Firebase/Google dependencies or secrets were added.
