import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, TimestampMixin


class PromoCode(TimestampMixin, Base):
    __tablename__ = "promo_codes"
    __table_args__ = (
        UniqueConstraint("provider_id", "code", name="uq_provider_promo_code"),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))
    discount_type: Mapped[str] = mapped_column(
        String(15), nullable=False,
    )
    discount_value: Mapped[float] = mapped_column(Float, nullable=False)
    min_booking_amount: Mapped[float | None] = mapped_column(Float)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    max_uses_per_customer: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1,
    )
    max_discount_amount: Mapped[float | None] = mapped_column(Float)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
    )

    # Relationships
    provider = relationship("ProviderProfile", lazy="selectin")
