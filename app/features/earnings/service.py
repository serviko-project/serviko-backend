import uuid
from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy import func, select, union_all, literal_column, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ValidationException
from app.features.bookings.models import Booking
from app.features.providers.models import ProviderProfile, ProviderService
from app.features.categories.models import Category
from app.features.users.models import User
from app.features.earnings.models import Withdrawal
from app.features.earnings.graph_calculator import GraphCalculator
from app.features.earnings.schemas import (
    EarningsSummaryResponse,
    GraphDataPoint,
    TransactionResponse,
    CashOutRequest,
    CashOutResponse
)


class EarningsService:
    @staticmethod
    async def get_provider_earnings_summary(
        db: AsyncSession, provider_id: uuid.UUID, filter_type: str = "Weekly",
        start_date_str: str | None = None, end_date_str: str | None = None
    ) -> EarningsSummaryResponse:

        # Calculate total earnings from completed bookings
        stmt_balance = select(func.coalesce(func.sum(Booking.total_price), 0.0)).where(
            Booking.provider_id == provider_id,
            Booking.status == "completed"
        )
        balance_result = await db.execute(stmt_balance)
        total_earnings = float(balance_result.scalar() or 0.0)

        # Calculate total withdrawals
        stmt_withdrawal = select(func.coalesce(func.sum(Withdrawal.amount), 0.0)).where(
            Withdrawal.provider_id == provider_id
        )
        withdrawal_result = await db.execute(stmt_withdrawal)
        total_withdrawals = float(withdrawal_result.scalar() or 0.0)

        available_balance = max(0.0, total_earnings - total_withdrawals)

        # Get graph data and dates
        graph_data, period_label, start_date, end_date = await GraphCalculator.calculate_graph_data(
            db, provider_id, filter_type, start_date_str, end_date_str
        )

        # Period Earnings
        stmt_period = select(func.coalesce(func.sum(Booking.total_price), 0.0)).where(
            Booking.provider_id == provider_id,
            Booking.status == "completed",
            func.date(Booking.completed_at) >= start_date,
            func.date(Booking.completed_at) <= end_date,
        )
        period_result = await db.execute(stmt_period)
        period_earnings = float(period_result.scalar() or 0.0)

        # Recent transactions
        stmt_transactions = select(Booking).where(
            Booking.provider_id == provider_id,
            Booking.status == "completed"
        ).options(
            selectinload(Booking.customer),
            selectinload(Booking.service).selectinload(
                ProviderService.category)
        ).order_by(Booking.completed_at.desc().nullslast()).limit(5)

        tx_result = await db.execute(stmt_transactions)
        recent_bookings = tx_result.scalars().all()

        # Recent withdrawals
        stmt_withdrawals = select(Withdrawal).where(
            Withdrawal.provider_id == provider_id
        ).order_by(Withdrawal.created_at.desc()).limit(5)

        tx_withdrawal_result = await db.execute(stmt_withdrawals)
        recent_withdrawals = tx_withdrawal_result.scalars().all()

        raw_transactions = []
        for b in recent_bookings:
            service_name = b.service.category.title if b.service and b.service.category else "Service"
            customer_name = b.customer.full_name if b.customer and b.customer.full_name else "Customer"
            title = f"{service_name} - {customer_name}"

            raw_transactions.append({
                "date": b.completed_at or b.scheduled_date,
                "resp": TransactionResponse(
                    id=str(b.id),
                    title=title,
                    date_str=b.completed_at.strftime(
                        '%b %d, %Y') if b.completed_at else b.scheduled_date.strftime('%b %d, %Y'),
                    amount=float(b.total_price),
                    is_credit=True
                )
            })

        for w in recent_withdrawals:
            raw_transactions.append({
                "date": w.created_at,
                "resp": TransactionResponse(
                    id=str(w.id),
                    title=f"Cash Out - {w.upi_id}",
                    date_str=w.created_at.strftime('%b %d, %Y'),
                    amount=float(w.amount),
                    is_credit=False
                )
            })

        # Sort and take top 5
        raw_transactions.sort(key=lambda x: x["date"], reverse=True)
        recent_transactions = [t["resp"] for t in raw_transactions[:5]]

        return EarningsSummaryResponse(
            available_balance=available_balance,
            period_label=period_label,
            period_earnings=period_earnings,
            filter=filter_type,
            graph_data=graph_data,
            recent_transactions=recent_transactions
        )

    @staticmethod
    async def create_cash_out(
        db: AsyncSession, provider_id: uuid.UUID, request: CashOutRequest
    ) -> CashOutResponse:
        # Validate minimum amount
        if request.amount < 100:
            raise ValidationException("Minimum cash out amount is ₹100")

        stmt_lock = select(ProviderProfile.id).where(
            ProviderProfile.id == provider_id).with_for_update()
        lock_result = await db.execute(stmt_lock)
        if not lock_result.scalar():
            raise ValidationException("Provider profile not found")

        # Calculate available balance
        stmt_balance = select(func.coalesce(func.sum(Booking.total_price), 0.0)).where(
            Booking.provider_id == provider_id,
            Booking.status == "completed"
        )
        balance_result = await db.execute(stmt_balance)
        total_earnings = float(balance_result.scalar() or 0.0)

        stmt_withdrawal = select(func.coalesce(func.sum(Withdrawal.amount), 0.0)).where(
            Withdrawal.provider_id == provider_id
        )
        withdrawal_result = await db.execute(stmt_withdrawal)
        total_withdrawals = float(withdrawal_result.scalar() or 0.0)

        available_balance = total_earnings - total_withdrawals

        if request.amount > available_balance:
            raise ValidationException(
                "Insufficient available balance for cash out")

        withdrawal = Withdrawal(
            provider_id=provider_id,
            amount=request.amount,
            upi_id=request.upi_id,
            status="completed"
        )
        db.add(withdrawal)
        await db.commit()
        await db.refresh(withdrawal)

        return CashOutResponse(
            status="success",
            message="Cash out processed successfully",
            withdrawal_id=str(withdrawal.id)
        )

    @staticmethod
    async def get_provider_transactions(
        db: AsyncSession, provider_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[List[TransactionResponse], int]:
        skip = (page - 1) * limit

        # Total counts
        stmt_booking_count = select(func.count(Booking.id)).where(
            Booking.provider_id == provider_id,
            Booking.status == "completed"
        )
        booking_count = await db.scalar(stmt_booking_count) or 0

        stmt_withdrawal_count = select(func.count(Withdrawal.id)).where(
            Withdrawal.provider_id == provider_id
        )
        withdrawal_count = await db.scalar(stmt_withdrawal_count) or 0

        total = booking_count + withdrawal_count

        booking_query = select(
            cast(Booking.id, String).label("id"),
            (func.coalesce(Category.title, "Service") + " - " +
             func.coalesce(User.full_name, "Customer")).label("title"),
            Booking.completed_at.label("date"),
            Booking.total_price.label("amount"),
            literal_column("true").label("is_credit")
        ).select_from(Booking)\
         .join(ProviderService, Booking.service_id == ProviderService.id)\
         .join(Category, ProviderService.category_id == Category.id)\
         .join(User, Booking.customer_id == User.id)\
         .where(
             Booking.provider_id == provider_id,
             Booking.status == "completed"
        )

        withdrawal_query = select(
            cast(Withdrawal.id, String).label("id"),
            ("Cash Out - " + Withdrawal.upi_id).label("title"),
            Withdrawal.created_at.label("date"),
            Withdrawal.amount.label("amount"),
            literal_column("false").label("is_credit")
        ).where(
            Withdrawal.provider_id == provider_id
        )

        union_stmt = union_all(
            booking_query, withdrawal_query).alias("tx_union")
        stmt = select(
            union_stmt.c.id,
            union_stmt.c.title,
            union_stmt.c.date,
            union_stmt.c.amount,
            union_stmt.c.is_credit
        ).order_by(union_stmt.c.date.desc()).limit(limit).offset(skip)

        result = await db.execute(stmt)
        rows = result.all()

        transactions = []
        for r in rows:
            transactions.append(
                TransactionResponse(
                    id=r.id,
                    title=r.title,
                    date_str=r.date.strftime('%b %d, %Y') if r.date else "",
                    amount=float(r.amount),
                    is_credit=bool(r.is_credit)
                )
            )
        return transactions, total
