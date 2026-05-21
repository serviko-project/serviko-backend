import uuid

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ValidationException
from app.core.responses import SuccessResponse, success_response
from app.features.auth.dependencies import get_current_user
from app.features.payments.razorpay_client import RazorpayClient
from app.features.payments.schemas import (
    PaymentOrderResponse,
    PaymentResponse,
    PaymentVerifyRequest,
)
from app.features.payments.service import PaymentService
from app.features.users.models import User

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post(
    "/bookings/{booking_id}/order",
    response_model=SuccessResponse[PaymentOrderResponse],
    status_code=201,
)
async def create_booking_payment_order(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PaymentService(db)
    result = await service.create_order(
        booking_id=booking_id,
        customer_id=current_user.id,
    )
    return success_response(data=result, message="Payment order created")


@router.post("/verify", response_model=SuccessResponse[PaymentResponse])
async def verify_payment(
    body: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PaymentService(db)
    result = await service.verify_payment(
        customer_id=current_user.id,
        booking_id=body.booking_id,
        razorpay_order_id=body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
        razorpay_signature=body.razorpay_signature,
    )
    return success_response(data=result, message="Payment verified")


@router.get(
    "/bookings/{booking_id}",
    response_model=SuccessResponse[PaymentResponse],
)
async def get_booking_payment(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PaymentService(db)
    result = await service.get_booking_payment(
        booking_id=booking_id,
        user_id=current_user.id,
    )
    return success_response(data=result)


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    if not x_razorpay_signature:
        raise ValidationException("Missing Razorpay webhook signature")

    client = RazorpayClient()
    if not client.verify_webhook_signature(
        payload=body,
        signature=x_razorpay_signature,
    ):
        raise ValidationException("Invalid Razorpay webhook signature")

    payload = await request.json()
    await PaymentService(db).handle_webhook(payload=payload)
    return {"status": "ok"}