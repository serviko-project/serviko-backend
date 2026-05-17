import uuid
from datetime import time

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, TimestampMixin


class ProviderProfile(TimestampMixin, Base):
    __tablename__ = "provider_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    professional_title: Mapped[str | None] = mapped_column(String(150))
    years_of_experience: Mapped[int | None] = mapped_column(SmallInteger)
    about: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    coverage_radius_km: Mapped[float | None] = mapped_column(
        Float, default=15.0
    )
    banner_image_url: Mapped[str | None] = mapped_column(Text)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="provider_profile")
    services = relationship(
        "ProviderService",
        back_populates="provider",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    availability = relationship(
        "ProviderAvailability",
        back_populates="provider",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    documents = relationship(
        "ProviderDocument",
        back_populates="provider",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    bookings = relationship(
        "Booking",
        back_populates="provider",
        lazy="noload",
    )


class ProviderService(TimestampMixin, Base):
    __tablename__ = "provider_services"
    __table_args__ = (
        UniqueConstraint("provider_id", "category_id",
                         name="uq_provider_category"),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    base_price_per_hour: Mapped[float | None] = mapped_column(Float)
    rating: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    reviews_count: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0")

    # Relationships
    provider = relationship("ProviderProfile", back_populates="services")
    category = relationship("Category", lazy="selectin")


class ProviderAvailability(TimestampMixin, Base):
    __tablename__ = "provider_availability"
    __table_args__ = (
        UniqueConstraint(
            "provider_id", "day_of_week", name="uq_provider_day"
        ),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Relationships
    provider = relationship("ProviderProfile", back_populates="availability")


class ProviderDocument(TimestampMixin, Base):
    __tablename__ = "provider_documents"
    __table_args__ = (
        UniqueConstraint(
            "provider_id", "document_type", name="uq_provider_doctype"
        ),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    provider = relationship("ProviderProfile", back_populates="documents")
