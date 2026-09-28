from pathlib import Path
from threading import Lock

import firebase_admin
from firebase_admin import App, credentials

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError

_initialization_lock = Lock()


def initialize_firebase() -> App | None:
    settings = get_settings()
    if not settings.google_application_credentials and not settings.firebase_project_id:
        return None
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass
    with _initialization_lock:
        try:
            return firebase_admin.get_app()
        except ValueError:
            try:
                credential = None
                if settings.google_application_credentials:
                    path = Path(settings.google_application_credentials).expanduser()
                    if not path.is_file():
                        raise ExternalServiceError(
                            message="Firebase credentials file was not found.",
                            code="firebase_credentials_not_found",
                        )
                    credential = credentials.Certificate(path)
                options = (
                    {"projectId": settings.firebase_project_id}
                    if settings.firebase_project_id
                    else None
                )
                return firebase_admin.initialize_app(credential=credential, options=options)
            except ExternalServiceError:
                raise
            except Exception as exc:
                raise ExternalServiceError(
                    message="Firebase could not be initialized.",
                    code="firebase_initialization_failed",
                ) from exc


def get_firebase_app() -> App:
    app = initialize_firebase()
    if app is None:
        raise ExternalServiceError(
            message="Firebase is not configured.", code="firebase_not_configured"
        )
    return app
