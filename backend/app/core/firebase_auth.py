"""Firebase authenticates identity only; all learner data stays in PostgreSQL."""

import os
from threading import Lock

import firebase_admin
from firebase_admin import auth, exceptions
from google.auth.exceptions import GoogleAuthError

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError, UnauthorizedError

_initialization_lock = Lock()


def firebase_app() -> firebase_admin.App:
    settings = get_settings()
    # Admin SDK bypasses signature checks when this environment variable is present.
    # Fail closed even in local mode; tests mock the verification boundary instead.
    if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST") or not settings.firebase_project_id:
        raise ExternalServiceError("Authentication is unavailable.", "auth_unavailable")
    with _initialization_lock:
        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(
                options={"projectId": settings.firebase_project_id, "httpTimeout": 10}
            )
        if app.project_id != settings.firebase_project_id:
            raise ExternalServiceError("Authentication is unavailable.", "auth_unavailable")
        return app


def verify_firebase_token(token: str) -> str:
    try:
        claims = auth.verify_id_token(token, app=firebase_app(), check_revoked=True)
        uid = claims.get("uid")
        if not isinstance(uid, str) or not 1 <= len(uid) <= 128:
            raise ValueError("Invalid subject")
        return uid
    except (
        auth.InvalidIdTokenError,
        auth.RevokedIdTokenError,
        auth.UserDisabledError,
        auth.UserNotFoundError,
        ValueError,
    ) as error:
        raise UnauthorizedError("Please sign in again.", "invalid_firebase_token") from error
    except (exceptions.FirebaseError, GoogleAuthError) as error:
        # Never turn a verifier outage into legacy fallback or leak SDK/credential details.
        raise ExternalServiceError("Authentication is unavailable.", "auth_unavailable") from error
