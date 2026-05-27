import uuid
from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.base_model import Base, TimestampMixin

class Bookmark(TimestampMixin, Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "service_id", name="uq_user_service_bookmark"),
        Index("ix_bookmarks_user_id", "user_id"),
        Index("ix_bookmarks_service_id", "service_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_services.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="bookmarks", lazy="noload")
    service = relationship("ProviderService", back_populates="bookmarks", lazy="joined")
