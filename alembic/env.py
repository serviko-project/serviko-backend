import asyncio
import os
import sys
from logging.config import fileConfig

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.base_model import Base
from app.core.config import get_settings

# Import all models so Alembic can detect them
from app.features.auth.otp_session_model import PasswordResetSession, RecoveryRateLimit
from app.features.categories.models import Category
from app.features.category_requests.models import CategoryRequest
from app.features.providers.models import (
    ProviderAvailability,
    ProviderDocument,
    ProviderProfile,
    ProviderService,
)
from app.features.users.models import User
from app.features.bookings.models import Booking
from app.features.payments.models import Payment
from app.features.support.models import FAQ, PrivacyPolicy
from app.features.reviews.models import Review
from app.features.promo_codes.models import PromoCode
from app.features.earnings.models import Withdrawal


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from app settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
