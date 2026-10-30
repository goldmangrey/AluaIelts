from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.exceptions import NotFoundError
from app.db.database import Database, get_database
from app.modules.enrollment.repository import DeviceEnrollmentRepository
from app.modules.enrollment.schemas import (
    DeviceEnrollmentListResponse,
    DeviceEnrollmentResponse,
    DeviceRevocationResponse,
    EnrollDeviceRequest,
    EnrollDeviceResponse,
)
from app.modules.enrollment.service import DeviceEnrollmentService

router = APIRouter(tags=["enrollment"])


@router.post("/enrollment", response_model=EnrollDeviceResponse)
async def enroll_device(
    request: EnrollDeviceRequest,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> EnrollDeviceResponse:
    response.headers["Cache-Control"] = "no-store"
    return await run_in_threadpool(
        DeviceEnrollmentService(database).enroll, request.code, request.device_name
    )


@router.get("/devices", response_model=DeviceEnrollmentListResponse)
async def list_devices(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    database: Annotated[Database, Depends(get_database)],
) -> DeviceEnrollmentListResponse:
    rows = await run_in_threadpool(DeviceEnrollmentRepository(database).list_active, identity.uid)
    return DeviceEnrollmentListResponse(
        devices=[
            DeviceEnrollmentResponse(
                enrollment_id=row.enrollment_id,
                device_name=row.device_name,
                created_at=row.created_at,
                last_used_at=row.last_used_at,
                is_current=row.enrollment_id == identity.enrollment_id,
            )
            for row in rows
        ]
    )


@router.delete("/devices/{enrollment_id}", response_model=DeviceRevocationResponse)
async def revoke_device(
    enrollment_id: str,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    database: Annotated[Database, Depends(get_database)],
) -> DeviceRevocationResponse:
    revoked = await run_in_threadpool(
        DeviceEnrollmentRepository(database).revoke, identity.uid, enrollment_id
    )
    if not revoked:
        raise NotFoundError(message="Device enrollment not found.", code="device_not_found")
    return DeviceRevocationResponse(revoked=True)


@router.delete("/device", response_model=DeviceRevocationResponse)
async def revoke_current_device(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    database: Annotated[Database, Depends(get_database)],
) -> DeviceRevocationResponse:
    revoked = await run_in_threadpool(
        DeviceEnrollmentRepository(database).revoke, identity.uid, identity.enrollment_id
    )
    if not revoked:
        raise NotFoundError(message="Device enrollment not found.", code="device_not_found")
    return DeviceRevocationResponse(revoked=True)
