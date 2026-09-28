from firebase_admin import firestore
from google.cloud.firestore import Client

from app.core.exceptions import ExternalServiceError
from app.integrations.firebase.client import get_firebase_app


def get_firestore_client() -> Client:
    try:
        return firestore.client(app=get_firebase_app())
    except ExternalServiceError:
        raise
    except Exception as exc:
        raise ExternalServiceError(
            message="The user profile service is temporarily unavailable.",
            code="firestore_unavailable",
        ) from exc
