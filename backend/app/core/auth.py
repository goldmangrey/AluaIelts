from typing import Annotated

from fastapi import Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.exceptions import UnauthorizedError
from app.integrations.firebase.auth import verify_firebase_token

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    uid: str
    email: str | None = None
    name: str | None = None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError(
            message="A valid bearer token is required.",
            code="unauthorized",
        )
    token = credentials.credentials.strip()
    if not token:
        raise UnauthorizedError(message="A bearer token is required.", code="unauthorized")

    decoded_token = await run_in_threadpool(verify_firebase_token, token)
    uid = decoded_token.get("uid") or decoded_token.get("sub")
    if not isinstance(uid, str) or not uid:
        raise UnauthorizedError(message="The authentication token is invalid.", code="unauthorized")
    email = decoded_token.get("email")
    name = decoded_token.get("name")
    return AuthenticatedUser(
        uid=uid,
        email=email if isinstance(email, str) else None,
        name=name if isinstance(name, str) else None,
    )
