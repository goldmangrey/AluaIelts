# Local Alua

Run from the repository root:

```sh
python3 scripts/local-stack.py up
python3 scripts/local-stack.py status
python3 scripts/local-stack.py down
```

Open **http://localhost:3000**. Backend docs: http://127.0.0.1:8000/docs.
The launcher leaves both processes running after it exits. Next runs in development
mode with hot reload; requests use the same authenticated Next → FastAPI flow as
production. Reading and Listening AI callbacks return to local Next, never to
alua.study. Reading AI is enabled only in the local backend process.

The existing `web/.env.local` supplies public Firebase settings. The existing
`.secrets/firebase-admin.json` supplies backend credentials; projects must match.
Sign in with your existing Firebase account. Registration/provisioning creates a
separate local learner. The local DB starts empty: production attempts/results are
not copied. Firebase identity/password operations still use the real Firebase
project; local application records use only local PostgreSQL.

State, logs, PostgreSQL and private AI caches persist under
`~/.local/share/alua/local-stack` (0700). PostgreSQL uses a private Unix socket,
without a TCP listener. Existing local PostgreSQL installations are untouched.
`down` preserves data. Listening audio is read from `~/Desktop/Listening`.
Requirements: existing backend `.venv`, web `node_modules`, pnpm and Homebrew
PostgreSQL 17. Migrations run only against this dedicated local cluster.

## AI

Wrangler provides the existing AI binding using its authenticated Cloudflare
session. It calls real Workers AI and consumes the account's normal quota.
A synthetic Gemma JSON call succeeded during setup. No public test endpoints or
mock answers are installed. Normal auth, validators and privacy rules remain.

Groq/Gemini/OpenRouter secrets currently are absent locally. Missing Groq skips
to Cloudflare. Production Worker secrets are neither downloaded nor modified.
If local keys are supplied later, use ignored `web/.dev.vars` with the existing
secret names, then restart. Gemini/OpenRouter privacy approval remains denied.

`ALUA_LOCAL_STACK=true` is set only by this launcher. It omits the nonserializable
AbortSignal argument at the Wrangler RPC boundary; the orchestrator's deadline
still bounds the response. A timed-out local remote request can finish remotely.
Native deployed Cloudflare bindings retain their existing abort behavior.

Verified: homepage/login/Reading/Listening render, proxied backend health 200,
protected Reading/Listening/AI routes return 401 without credentials, Firebase
Admin credential refresh succeeds, 288/288 local audio paths exist. Authenticated
exam/AI browser flows require signing in; they were not claimed verified here.
No production configuration, database, commits, pushes or deployments changed.

## Reading Explain button follow-up

Local C04 Test 1 Q1/Q2 clicks returned HTTP 200 immediately, but no provider call:
the backend incorrectly classified standard TRUE/FALSE/NOT GIVEN label-only
options as `incomplete_options`. Boolean IELTS options now allow their complete
standard labels; incomplete nonboolean options still fail closed. Evidence and
ownership validation remain. Fingerprint policy version is v1.3.

The card also appeared after the entire group, below the clicked question's
viewport. Cards now render beside their own saved-answer controls (outside inline
sentence blanks), with independent multi-open state and no automatic scrolling.
Refresh an already open review once to clear its old in-memory unavailable result.

Follow-up checks: 12 targeted backend checks, Reading Chromium/WebKit flows,
TypeScript, targeted ESLint and Ruff passed. Browser coverage includes immediate
visible opening, no-jump, multi-open, evidence navigation and cached reload.
Generative browser responses in these checks were mocked.
