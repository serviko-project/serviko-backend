from app.features.bookings.models import Booking

def map_booking_to_detail_dict(b: Booking) -> dict:
    return {
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
        "category_name": (
            b.service.category.title
            if b.service and b.service.category else None
        ),
        "confirmed_at": b.confirmed_at,
        "rejected_at": b.rejected_at,
        "cancelled_at": b.cancelled_at,
        "created_at": b.created_at,
        "updated_at": b.updated_at,
    }

def map_booking_to_list_item_dict(b: Booking) -> dict:
    return {
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
        "category_name": (
            b.service.category.title
            if b.service and b.service.category else None
        ),
        "rejection_reason": b.rejection_reason,
        "confirmed_at": b.confirmed_at,
        "rejected_at": b.rejected_at,
        "cancelled_at": b.cancelled_at,
        "created_at": b.created_at,
        "updated_at": b.updated_at,
    }
