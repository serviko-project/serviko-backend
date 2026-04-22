from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import Base, TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    title: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    icon: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
