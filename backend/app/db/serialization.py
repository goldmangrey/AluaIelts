from typing import Any

from pydantic import BaseModel


def document(model: BaseModel) -> dict[str, Any]:
    """Return a JSON-safe representation suitable for JSONB storage."""
    return model.model_dump(mode="json")
