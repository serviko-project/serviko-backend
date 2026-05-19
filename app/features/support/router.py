from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.features.support.schemas import FAQResponse, PrivacyPolicyResponse
from app.features.support.service import SupportService

router = APIRouter(prefix="/api/v1/support", tags=["Support"])

# Retrieve active FAQs
@router.get("/faqs", description="Get a list of active FAQs, optionally filtered by search or category")
async def list_faqs(
    category: str | None = Query(None, description="Filter FAQs by category"),
    search: str | None = Query(
        None, description="Search term in questions or answers"),
    db: AsyncSession = Depends(get_db)
):
    service = SupportService(db)
    faqs = await service.list_faqs(category=category, search=search)
    return success_response(
        data=[FAQResponse.model_validate(faq).model_dump(
            mode="json") for faq in faqs],
        message="FAQs retrieved successfully"
    )

# Retrieve the latest Privacy Policy
@router.get("/privacy-policy", description="Get the latest active Privacy Policy")
async def get_privacy_policy(
    db: AsyncSession = Depends(get_db)
):
    service = SupportService(db)
    policy = await service.get_latest_privacy_policy()
    return success_response(
        data=PrivacyPolicyResponse.model_validate(
            policy).model_dump(mode="json"),
        message="Privacy Policy retrieved successfully"
    )
