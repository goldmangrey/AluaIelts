from typing import Any

from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError

from app.core.exceptions import ExternalServiceError, UnauthorizedError
from app.integrations.firebase.client import get_firebase_app


def verify_firebase_token(token: str) -> dict[str, Any]:
    if not token.strip():
        raise UnauthorizedError(message="Firebase ID token is required.", code="token_required")
    try:
        return auth.verify_id_token(token, app=get_firebase_app())
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError) as exc:
        raise UnauthorizedError(
            message="Firebase ID token is invalid or expired.",
            code="invalid_firebase_token",
        ) from exc
    except FirebaseError as exc:
        raise ExternalServiceError(
            message="Firebase authentication is temporarily unavailable.",
            code="firebase_auth_unavailable",
        ) from exc
