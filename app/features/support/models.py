from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import Base, TimestampMixin

# Model for FAQs
class FAQ(TimestampMixin, Base):
    __tablename__ = "faqs"

    question: Mapped[str] = mapped_column(String(255), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)

# Model for Privacy Policy
class PrivacyPolicy(TimestampMixin, Base):
    __tablename__ = "privacy_policies"

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)
