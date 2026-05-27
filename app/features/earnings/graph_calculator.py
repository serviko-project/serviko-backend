import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.bookings.models import Booking
from app.features.earnings.schemas import GraphDataPoint

class GraphCalculator:
    @staticmethod
    async def calculate_graph_data(
        db: AsyncSession, 
        provider_id: uuid.UUID, 
        filter_type: str, 
        start_date_str: str | None = None, 
        end_date_str: str | None = None
    ) -> Tuple[List[GraphDataPoint], str, date, date]:
        # Get current date in IST 
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        ist_now = datetime.now(ist_tz)
        today = ist_now.date()
        
        start_date = today
        end_date = today
        period_label = ""
        graph_data: List[GraphDataPoint] = []
        
        # Local timezone conversion 
        local_completed_at = func.timezone('Asia/Kolkata', Booking.completed_at)

        if filter_type == "Daily":
            period_label = "Today"
            start_date = today
            
            stmt_day = select(
                func.extract('hour', local_completed_at), func.coalesce(func.sum(Booking.total_price), 0.0)
            ).where(
                Booking.provider_id == provider_id,
                Booking.status == "completed",
                func.date(local_completed_at) == start_date,
            ).group_by(func.extract('hour', local_completed_at))
            
            day_result = await db.execute(stmt_day)
            day_dict = {int(row[0] or 0): float(row[1]) for row in day_result.all()}
            
            intervals = [0.0, 0.0, 0.0, 0.0]
            for hour, val in day_dict.items():
                if hour < 6: intervals[0] += val
                elif hour < 12: intervals[1] += val
                elif hour < 18: intervals[2] += val
                else: intervals[3] += val
                
            graph_data = [
                GraphDataPoint(label="12am", value=intervals[0]),
                GraphDataPoint(label="6am", value=intervals[1]),
                GraphDataPoint(label="12pm", value=intervals[2]),
                GraphDataPoint(label="6pm", value=intervals[3]),
            ]
        elif filter_type == "Weekly":
            # Monday to Sunday
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            period_label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
            
            stmt_weekly = select(
                func.date(local_completed_at).label('comp_date'), func.coalesce(func.sum(Booking.total_price), 0.0)
            ).where(
                Booking.provider_id == provider_id,
                Booking.status == "completed",
                func.date(local_completed_at) >= start_date,
                func.date(local_completed_at) <= end_date,
            ).group_by('comp_date')
            
            weekly_result = await db.execute(stmt_weekly)
            weekly_dict = {row[0]: float(row[1]) for row in weekly_result.all()}
            
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for i, day_label in enumerate(days):
                curr_date = start_date + timedelta(days=i)
                graph_data.append(GraphDataPoint(label=day_label, value=weekly_dict.get(curr_date, 0.0)))
                
        elif filter_type == "Monthly":
            start_date = today.replace(day=1)
            # Find last day of month
            if start_date.month == 12:
                next_month = start_date.replace(year=start_date.year + 1, month=1)
            else:
                next_month = start_date.replace(month=start_date.month + 1)
            end_date = next_month - timedelta(days=1)
            period_label = start_date.strftime('%b %Y')
            
            stmt_monthly = select(
                func.date(local_completed_at).label('comp_date'), func.coalesce(func.sum(Booking.total_price), 0.0)
            ).where(
                Booking.provider_id == provider_id,
                Booking.status == "completed",
                func.date(local_completed_at) >= start_date,
                func.date(local_completed_at) <= end_date,
            ).group_by('comp_date')
            
            monthly_result = await db.execute(stmt_monthly)
            monthly_dict = {row[0]: float(row[1]) for row in monthly_result.all()}
            
            weeks = [0.0, 0.0, 0.0, 0.0]
            for d, val in monthly_dict.items():
                if d.day <= 7: weeks[0] += val
                elif d.day <= 14: weeks[1] += val
                elif d.day <= 21: weeks[2] += val
                else: weeks[3] += val
                
            graph_data = [
                GraphDataPoint(label="W1", value=weeks[0]),
                GraphDataPoint(label="W2", value=weeks[1]),
                GraphDataPoint(label="W3", value=weeks[2]),
                GraphDataPoint(label="W4", value=weeks[3]),
            ]
        elif filter_type == "Yearly":
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            period_label = start_date.strftime('%Y')
            
            stmt_yearly = select(
                func.extract('month', local_completed_at).label('month'), func.coalesce(func.sum(Booking.total_price), 0.0)
            ).where(
                Booking.provider_id == provider_id,
                Booking.status == "completed",
                func.date(local_completed_at) >= start_date,
                func.date(local_completed_at) <= end_date,
            ).group_by('month')
            
            yearly_result = await db.execute(stmt_yearly)
            yearly_dict = {int(row[0]): float(row[1]) for row in yearly_result.all()}
            
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            for i, m in enumerate(months):
                graph_data.append(GraphDataPoint(label=m, value=yearly_dict.get(i + 1, 0.0)))
                
        elif filter_type == "Custom":
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            period_label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
            diff_days = (end_date - start_date).days
            
            if diff_days == 0:
                stmt_day = select(
                    func.extract('hour', local_completed_at), func.coalesce(func.sum(Booking.total_price), 0.0)
                ).where(
                    Booking.provider_id == provider_id,
                    Booking.status == "completed",
                    func.date(local_completed_at) == start_date,
                ).group_by(func.extract('hour', local_completed_at))
                
                day_result = await db.execute(stmt_day)
                day_dict = {int(row[0] or 0): float(row[1]) for row in day_result.all()}
                
                intervals = [0.0, 0.0, 0.0, 0.0]
                for hour, val in day_dict.items():
                    if hour < 6: intervals[0] += val
                    elif hour < 12: intervals[1] += val
                    elif hour < 18: intervals[2] += val
                    else: intervals[3] += val
                    
                graph_data = [
                    GraphDataPoint(label="12am", value=intervals[0]),
                    GraphDataPoint(label="6am", value=intervals[1]),
                    GraphDataPoint(label="12pm", value=intervals[2]),
                    GraphDataPoint(label="6pm", value=intervals[3]),
                ]
            elif diff_days <= 10:
                stmt_custom = select(
                    func.date(local_completed_at).label('comp_date'), func.coalesce(func.sum(Booking.total_price), 0.0)
                ).where(
                    Booking.provider_id == provider_id,
                    Booking.status == "completed",
                    func.date(local_completed_at) >= start_date,
                    func.date(local_completed_at) <= end_date,
                ).group_by('comp_date')
                
                custom_result = await db.execute(stmt_custom)
                custom_dict = {row[0]: float(row[1]) for row in custom_result.all()}
                
                for i in range(diff_days + 1):
                    curr = start_date + timedelta(days=i)
                    label = curr.strftime('%d %b')
                    graph_data.append(GraphDataPoint(label=label, value=custom_dict.get(curr, 0.0)))
            else:
                stmt_custom = select(
                    func.date(local_completed_at).label('comp_date'), func.coalesce(func.sum(Booking.total_price), 0.0)
                ).where(
                    Booking.provider_id == provider_id,
                    Booking.status == "completed",
                    func.date(local_completed_at) >= start_date,
                    func.date(local_completed_at) <= end_date,
                ).group_by('comp_date')
                
                custom_result = await db.execute(stmt_custom)
                custom_dict = {row[0]: float(row[1]) for row in custom_result.all()}
                
                num_points = 4
                points_values = [0.0] * num_points
                chunk_size = (diff_days + 1) / num_points
                
                for i in range(diff_days + 1):
                    curr = start_date + timedelta(days=i)
                    chunk_idx = min(int(i / chunk_size), num_points - 1)
                    points_values[chunk_idx] += custom_dict.get(curr, 0.0)
                
                for idx in range(num_points):
                    chunk_start_day = start_date + timedelta(days=int(idx * chunk_size))
                    label = chunk_start_day.strftime('%d %b')
                    graph_data.append(GraphDataPoint(label=label, value=points_values[idx]))
                    
        return graph_data, period_label, start_date, end_date
