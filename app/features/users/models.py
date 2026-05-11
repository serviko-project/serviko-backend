from sqlalchemy import Boolean, Date, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str | None] = mapped_column(String(100))
    phone_number: Mapped[str | None] = mapped_column(String(20))
    date_of_birth: Mapped[str | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))
    profile_image_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # Relationships
    provider_profile = relationship(
        "ProviderProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
