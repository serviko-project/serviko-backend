from fastapi import APIRouter, Depends

from app.core.responses import SuccessResponse, success_response
from app.features.auth.dependencies import get_current_user
from app.features.communication.schemas import TokenResponse
from app.features.communication.service import CommunicationService
from app.features.users.models import User

router = APIRouter(prefix="/api/v1/communication", tags=["Communication"])


@router.post("/token", response_model=SuccessResponse[TokenResponse])
async def generate_token(
    current_user: User = Depends(get_current_user),
):
    svc = CommunicationService()
    token_data = svc.generate_token(user_id=current_user.firebase_uid)
    return success_response(data=token_data, message="Token generated")
