from typing import Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import HomeContext, require_home_permission, get_db
from src.services.privacy_governance_service import PrivacyGovernanceService

router = APIRouter(prefix="/homes/{home_id}/privacy", tags=["Privacy & Data Governance"])


class DataDeletionRequest(BaseModel):
    confirmation_phrase: str


@router.get("/summary", response_model=Dict[str, Any])
async def get_privacy_summary(
    home_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("homes:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns transparency overview of stored household data, AI privacy rules, and retention schedule.
    """
    return await PrivacyGovernanceService.get_privacy_summary(
        db=db, home_id=home_ctx.home_id, user_id=home_ctx.user.id
    )


@router.get("/export", response_model=Dict[str, Any])
async def export_household_data(
    home_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("homes:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Exports a complete structured JSON package of personal and household data for GDPR portability.
    """
    return await PrivacyGovernanceService.export_user_and_home_data(
        db=db, home_id=home_ctx.home_id, user_id=home_ctx.user.id
    )


@router.post("/delete", response_model=Dict[str, Any])
async def request_data_deletion(
    home_id: UUID,
    body: DataDeletionRequest,
    home_ctx: HomeContext = Depends(require_home_permission("homes:view")),
    db: AsyncSession = Depends(get_db),
):

    """
    Requests personal data erasure & anonymization (GDPR Article 17 Right to Erasure).
    """
    res = await PrivacyGovernanceService.request_data_deletion(
        db=db,
        home_id=home_ctx.home_id,
        user_id=home_ctx.user.id,
        confirmation_phrase=body.confirmation_phrase
    )
    if res.get("status") == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("message")
        )
    return res
