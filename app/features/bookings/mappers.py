from app.features.bookings.models import Booking

def _latest_payment(b: Booking):
    payments = sorted(b.payments, key=lambda p: p.created_at, reverse=True)
    return payments[0] if payments else None

def _payment_fields(b: Booking) -> dict:
    payment = _latest_payment(b)
    payment_reference = None
    if payment:
        payment_reference = payment.razorpay_payment_id or payment.razorpay_order_id
    return {
        "payment_status": payment.status if payment else "unpaid",
        "payment_id": payment.id if payment else None,
        "payment_reference": payment_reference,
        "paid_at": payment.paid_at if payment else None,
        "refunded_at": payment.refunded_at if payment else None,
    }

def map_booking_to_detail_dict(b: Booking) -> dict:
    data = {
        "id": b.id,
        "customer_id": b.customer_id,
        "provider_id": b.provider_id,
        "service_id": b.service_id,
        "status": b.status,
        "scheduled_date": b.scheduled_date,
        "start_time": b.start_time.strftime("%H:%M"),
        "end_time": b.end_time.strftime("%H:%M"),
        "duration_hours": b.duration_hours,
        "base_price_per_hour": b.base_price_per_hour,
        "total_price": b.total_price,
        "original_price": b.original_price,
        "discount_amount": b.discount_amount,
        "promo_code_text": b.promo_code.code if b.promo_code else None,
        "customer_latitude": b.customer_latitude,
        "customer_longitude": b.customer_longitude,
        "customer_address": b.customer_address,
        "rejection_reason": b.rejection_reason,
        "customer_name": b.customer.full_name if b.customer else None,
        "customer_image": b.customer.profile_image_url if b.customer else None,
        "provider_name": (
            b.provider.user.full_name
            if b.provider and b.provider.user else None
        ),
        "provider_image": (
            b.provider.user.profile_image_url
            if b.provider and b.provider.user else None
        ),
        "provider_firebase_uid": (
            b.provider.user.firebase_uid
            if b.provider and b.provider.user else None
        ),
        "category_name": (
            b.service.category.title
            if b.service and b.service.category else None
        ),
        "confirmed_at": b.confirmed_at,
        "rejected_at": b.rejected_at,
        "cancelled_at": b.cancelled_at,
        "completed_at": b.completed_at,
        "completion_note": b.completion_note,
        "has_review": b.review is not None,
        "created_at": b.created_at,
        "updated_at": b.updated_at,
    }
    data.update(_payment_fields(b))
    return data

def map_booking_to_list_item_dict(b: Booking) -> dict:
    data = {
        "id": b.id,
        "customer_id": b.customer_id,
        "provider_id": b.provider_id,
        "service_id": b.service_id,
        "status": b.status,
        "scheduled_date": b.scheduled_date,
        "start_time": b.start_time.strftime("%H:%M"),
        "end_time": b.end_time.strftime("%H:%M"),
        "duration_hours": b.duration_hours,
        "base_price_per_hour": b.base_price_per_hour,
        "total_price": b.total_price,
        "original_price": b.original_price,
        "discount_amount": b.discount_amount,
        "promo_code_text": b.promo_code.code if b.promo_code else None,
        "customer_latitude": b.customer_latitude,
        "customer_longitude": b.customer_longitude,
        "customer_address": b.customer_address,
        "customer_name": b.customer.full_name if b.customer else None,
        "customer_image": b.customer.profile_image_url if b.customer else None,
        "provider_name": (
            b.provider.user.full_name
            if b.provider and b.provider.user else None
        ),
        "provider_image": (
            b.provider.user.profile_image_url
            if b.provider and b.provider.user else None
        ),
        "provider_firebase_uid": (
            b.provider.user.firebase_uid
            if b.provider and b.provider.user else None
        ),
        "category_name": (
            b.service.category.title
            if b.service and b.service.category else None
        ),
        "rejection_reason": b.rejection_reason,
        "confirmed_at": b.confirmed_at,
        "rejected_at": b.rejected_at,
        "cancelled_at": b.cancelled_at,
        "completed_at": b.completed_at,
        "completion_note": b.completion_note,
        "has_review": b.review is not None,
        "created_at": b.created_at,
        "updated_at": b.updated_at,
    }
    data.update(_payment_fields(b))
    return data
