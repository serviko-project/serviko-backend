import uuid

from sqlalchemy import select, and_, func

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.features.bookings.models import Booking
from app.features.promo_codes.models import PromoCode
from app.features.providers.models import ProviderProfile
from app.features.promo_codes.services.base_service import BasePromoService


class ProviderPromoService(BasePromoService):
    async def create_promo_code(
        self, provider_user_id: uuid.UUID, data: dict,
    ) -> dict:
        provider = await self._get_provider_by_user(provider_user_id)
        code_upper = data["code"].strip().upper()

        # Validate percentage range
        if data["discount_type"] == "percentage" and data["discount_value"] > 100:
            raise ValidationException("Percentage discount cannot exceed 100%")

        if data.get("expires_at"):
            from datetime import datetime, timezone
            if data["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                raise ValidationException("Expiry date cannot be in the past")

        # Check uniqueness within provider
        existing = await self.db.execute(
            select(PromoCode).where(
                and_(
                    PromoCode.provider_id == provider.id,
                    PromoCode.code == code_upper,
                ),
            ),
        )
        if existing.scalar_one_or_none():
            raise ConflictException(
                f"Promo code '{code_upper}' already exists")

        promo = PromoCode(
            provider_id=provider.id,
            code=code_upper,
            description=data.get("description"),
            discount_type=data["discount_type"],
            discount_value=data["discount_value"],
            min_booking_amount=data.get("min_booking_amount"),
            max_uses=data.get("max_uses"),
            max_discount_amount=data.get("max_discount_amount"),
            expires_at=data.get("expires_at"),
        )
        self.db.add(promo)
        await self.db.flush()
        await self.db.refresh(promo)

        usage_count = await self._get_usage_count(promo.id)
        return self._to_response_dict(promo, usage_count)

    async def list_provider_promos(
        self,
        provider_user_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        provider = await self._get_provider_by_user(provider_user_id)

        # Count
        count_q = select(func.count(PromoCode.id)).where(
            PromoCode.provider_id == provider.id,
        )
        total = (await self.db.execute(count_q)).scalar() or 0

        # Fetch
        q = (
            select(PromoCode)
            .where(PromoCode.provider_id == provider.id)
            .order_by(PromoCode.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(q)
        promos = result.scalars().all()

        usage_counts = await self._get_usage_counts_batch([p.id for p in promos])
        items = [
            self._to_response_dict(p, usage_counts.get(p.id, 0))
            for p in promos
        ]

        return items, total

    async def list_promos_by_provider_id(
        self,
        provider_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        # Count
        count_q = select(func.count(PromoCode.id)).where(
            and_(
                PromoCode.provider_id == provider_id,
                PromoCode.is_active == True,
            )
        )
        total = (await self.db.execute(count_q)).scalar() or 0

        # Fetch
        q = (
            select(PromoCode)
            .where(
                and_(
                    PromoCode.provider_id == provider_id,
                    PromoCode.is_active == True,
                )
            )
            .order_by(PromoCode.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(q)
        promos = result.scalars().all()

        usage_counts = await self._get_usage_counts_batch([p.id for p in promos])
        items = [
            self._to_response_dict(p, usage_counts.get(p.id, 0))
            for p in promos
        ]

        return items, total

    async def update_promo_code(
        self,
        promo_id: uuid.UUID,
        provider_user_id: uuid.UUID,
        data: dict,
    ) -> dict:
        promo = await self._get_owned_promo(promo_id, provider_user_id)

        for field in ("description", "is_active", "min_booking_amount", "max_uses", "max_discount_amount", "expires_at"):
            if field in data:
                setattr(promo, field, data[field])

        await self.db.flush()
        await self.db.refresh(promo)
        usage_count = await self._get_usage_count(promo.id)
        return self._to_response_dict(promo, usage_count)

    async def deactivate_promo_code(
        self,
        promo_id: uuid.UUID,
        provider_user_id: uuid.UUID,
    ) -> dict:
        promo = await self._get_owned_promo(promo_id, provider_user_id)
        promo.is_active = False
        await self.db.flush()
        await self.db.refresh(promo)
        usage_count = await self._get_usage_count(promo.id)
        return self._to_response_dict(promo, usage_count)

    # -- Private helpers --

    async def _get_usage_counts_batch(self, promo_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not promo_ids:
            return {}
        q = (
            select(Booking.promo_code_id, func.count(Booking.id))
            .where(
                and_(
                    Booking.promo_code_id.in_(promo_ids),
                    Booking.status != "cancelled",
                )
            )
            .group_by(Booking.promo_code_id)
        )
        result = await self.db.execute(q)
        return dict(result.all())

    async def _get_provider_by_user(
        self, user_id: uuid.UUID,
    ) -> ProviderProfile:
        result = await self.db.execute(
            select(ProviderProfile).where(
                ProviderProfile.user_id == user_id,
            ),
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise NotFoundException("Provider profile not found")
        return provider

    async def _get_owned_promo(
        self, promo_id: uuid.UUID, provider_user_id: uuid.UUID,
    ) -> PromoCode:
        provider = await self._get_provider_by_user(provider_user_id)
        result = await self.db.execute(
            select(PromoCode).where(PromoCode.id == promo_id),
        )
        promo = result.scalar_one_or_none()
        if not promo:
            raise NotFoundException("Promo code not found")
        if promo.provider_id != provider.id:
            raise ForbiddenException("You don't own this promo code")
        return promo

    def _to_response_dict(self, promo: PromoCode, usage_count: int) -> dict:
        return {
            "id": promo.id,
            "provider_id": promo.provider_id,
            "code": promo.code,
            "description": promo.description,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "min_booking_amount": promo.min_booking_amount,
            "max_uses": promo.max_uses,
            "max_uses_per_customer": promo.max_uses_per_customer,
            "max_discount_amount": promo.max_discount_amount,
            "expires_at": promo.expires_at,
            "is_active": promo.is_active,
            "usage_count": usage_count,
            "created_at": promo.created_at,
            "updated_at": promo.updated_at,
        }
