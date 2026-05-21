import uuid
from datetime import datetime

from pydantic import BaseModel


class PaymentOrderResponse(BaseModel):
    payment_id: uuid.UUID
    booking_id: uuid.UUID
    razorpay_key_id: str
    razorpay_order_id: str
    amount: int
    amount_rupees: float
    currency: str
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    description: str


class PaymentVerifyRequest(BaseModel):
    booking_id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: float
    currency: str
    status: str
    gateway: str
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    paid_at: datetime | None = None
    refunded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
