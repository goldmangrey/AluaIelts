# Alua local setup

## 1. Requirements

- Python 3.12 and `uv`
- Xcode with an iOS 17+ SDK
- XcodeGen
- A Firebase project with an Apple app
- An OpenAI API project

Keep secrets out of Git and enter them directly into local files or your shell. Do not paste API
keys or service-account JSON into chats, source code, Swift build settings, or `project.yml`.

## 2. Firebase setup

1. Create or select the Alua project in Firebase Console.
2. Add an Apple app with bundle ID `com.alua.app`.
3. In **Authentication → Sign-in method**, enable **Email/Password** only.
4. In **Firestore Database**, create the default database in standard/native mode and choose the
   appropriate region. The application does not create databases at runtime.

iOS uses Firebase only for authentication. Firestore access remains:

```text
Swift → FastAPI → Firebase Admin → Firestore
```

Do not add the FirebaseFirestore Swift package.

## 3. OpenAI setup

1. Create an OpenAI API project for Alua.
2. Create a project-scoped API key, preferably with an expiration/rotation policy.
3. Store the key only in `backend/.env` as `OPENAI_API_KEY`.
4. Never expose the key to Swift, Xcode build settings, or Firebase client configuration.

The configured model names select models for future requests; they do not create additional
OpenAI clients or make network calls during startup.

## 4. Backend environment

From `backend/`, create `.env` from `.env.example` if it does not already exist. Preserve existing
local values and configure the missing entries directly:

```dotenv
APP_NAME=Alua API
APP_VERSION=0.1.0
APP_ENV=local
DEBUG=true
API_PREFIX=/api/v1

OPENAI_API_KEY=
OPENAI_EXERCISE_MODEL=gpt-5.6-luna
OPENAI_ANALYSIS_MODEL=gpt-5.6-terra

FIREBASE_PROJECT_ID=
GOOGLE_APPLICATION_CREDENTIALS=

ALLOWED_ORIGINS=
```

`FIREBASE_CREDENTIALS_PATH` remains accepted temporarily for existing local environments, but new
configuration should use the standard `GOOGLE_APPLICATION_CREDENTIALS` name.

## 5. Firebase Admin credentials

In Firebase Console, open **Project Settings → Service Accounts** and generate a private key for
local development, or use another appropriate Google Application Default Credentials flow.

Keep the downloaded JSON outside tracked source. A recommended local convention is:

```text
Alua/.secrets/firebase-admin.json
```

`.secrets/` and common Firebase Admin credential filenames are ignored by Git. Set an absolute
path in `backend/.env`:

```dotenv
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/Alua/.secrets/firebase-admin.json
FIREBASE_PROJECT_ID=your-firebase-project-id
```

The backend also supports ADC supplied by the host environment when only the project ID is
configured. Never add Admin credentials to the iOS app.

## 6. iOS Firebase plist

Download the Apple configuration file from **Firebase Console → Project Settings → Your apps** and
place it at:

```text
frontend/Alua/Resources/GoogleService-Info.plist
```

The `Alua` source directory is included by XcodeGen, so an existing plist is copied only into the
main application target. `AluaWidgets` uses a separate source directory and does not receive it.
The filename is ignored by Git. Without the plist, the app still compiles and reports that Firebase
is not configured.

## 7. Start backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Verify `http://127.0.0.1:8000/api/v1/health`. Firebase and OpenAI may be absent for health/startup,
but authenticated profile endpoints require Firebase Admin configuration.

## 8. Generate and build iOS project

```bash
cd frontend
xcodegen generate
xcodebuild \
  -project Alua.xcodeproj \
  -scheme Alua \
  -sdk iphonesimulator \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO \
  build
```

Debug uses `http://127.0.0.1:8000`, which reaches the Mac only from iOS Simulator. For a physical
iPhone, configure a reachable LAN/HTTPS backend URL. Set the production API URL before release.

## 9. Common local issues

- **Firebase is not configured:** verify the plist location and regenerate the Xcode project.
- **Email/password sign-in fails:** confirm the provider is enabled in Firebase Console.
- **Profile endpoint returns 503:** verify the absolute credential path, project ID, Firestore
  database, and service-account access.
- **Simulator cannot reach backend:** ensure Uvicorn is running and the build uses the Debug URL.
- **OpenAI unavailable:** configure the backend key; no OpenAI validation call runs at startup.
