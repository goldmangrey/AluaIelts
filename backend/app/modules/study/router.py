from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.modules.study.service import StudyService

router = APIRouter(prefix="/study", tags=["study"])
Identity = Annotated[AuthenticatedUser, Depends(get_current_user)]


class StudyAction(BaseModel):
    learner_id: str | None = None
    event_id: UUID
    item_id: str = Field(min_length=1, max_length=180)
    action: Literal["next", "known", "unknown", "hide", "unhide", "report", "review"]
    answer: str | None = Field(default=None, max_length=1000)
    comment: str = Field(default="", max_length=1000)


@router.get("/today")
def today(identity: Identity, learner_id: str | None = None):
    if learner_id is not None and learner_id != identity.uid:
        raise HTTPException(409, "Learner changed")
    return StudyService().snapshot(identity.uid)


@router.get("/book")
def book(
    identity: Identity,
    q: str = "",
    status: str = "all",
    topic: int | None = None,
    day: int | None = None,
):
    data = StudyService().snapshot(identity.uid)
    ids = set(data["days"][day - 1]["ids"]) if day and 1 <= day <= 50 else None
    return {
        "cards": [
            c
            for c in data["book"]
            if (not q or q.casefold() in (c["term"] + " " + c["translation_ru"]).casefold())
            and (status == "all" or c["status"] == status)
            and (topic is None or topic in c["topic_ids"])
            and (ids is None or c["id"] in ids)
        ],
        "days": data["days"],
        "topics": data["topics"],
    }


@router.post("/actions")
def action(request: StudyAction, identity: Identity):
    return StudyService().act(identity.uid, request)
