import hashlib
import re
from datetime import date

PACK_SCHEMA_VERSION = 2
REVIEW_SESSION_SCHEMA_VERSION = 2
REVIEW_SESSION_GENERATION_VERSION = 2
REVIEW_STATE_SCHEMA_VERSION = 2
REVIEW_EVENT_SCHEMA_VERSION = 2
REVIEW_CONTRACT_VERSION = 2


def content_signature(content_version: str) -> str:
    readable = re.sub(r"[^A-Za-z0-9_-]", "-", content_version).strip("-")[:40]
    digest = hashlib.sha256(content_version.encode()).hexdigest()[:10]
    return f"{readable}-{digest}"


def pack_document_id(
    local_date: date, content_version: str, selector_version: int, revision: int = 0
) -> str:
    base = (
        f"{local_date.isoformat()}__schema{PACK_SCHEMA_VERSION}__selector{selector_version}__"
        f"{content_signature(content_version)}"
    )
    return base if revision == 0 else f"{base}__repair{revision}"


def session_signature(pack_ids: tuple[str, ...]) -> str:
    return hashlib.sha256("\n".join(pack_ids).encode()).hexdigest()[:12]


def state_document_id(lexical_item_id: str) -> str:
    return f"state{REVIEW_STATE_SCHEMA_VERSION}__{lexical_item_id}"
