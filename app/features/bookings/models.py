import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, TimestampMixin


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint(
            "provider_id", "scheduled_date", "start_time",
            name="uq_booking_provider_date_start",
        ),
        Index("ix_bookings_customer_id", "customer_id"),
        Index("ix_bookings_provider_id", "provider_id"),
        Index("ix_bookings_status", "status"),
        Index("ix_bookings_scheduled_date", "scheduled_date"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_services.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_hours: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    base_price_per_hour: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)

    customer_latitude: Mapped[float | None] = mapped_column(Float)
    customer_longitude: Mapped[float | None] = mapped_column(Float)
    customer_address: Mapped[str | None] = mapped_column(Text)

    rejection_reason: Mapped[str | None] = mapped_column(Text)
    completion_note: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    customer = relationship("User", back_populates="bookings", lazy="selectin")
    provider = relationship(
        "ProviderProfile", back_populates="bookings", lazy="selectin",
    )
    service = relationship("ProviderService", lazy="selectin")
    payments = relationship(
        "Payment",
        back_populates="booking",
        lazy="selectin",
    )
    review = relationship(
        "Review",
        back_populates="booking",
        uselist=False,
        lazy="selectin",
    )

