from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, case, cast, extract, func, select, Float, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Category, Product, Sale

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

PeriodType = str  # "today" | "week" | "month" | "year"


# Argentina timezone offset (UTC-3)
ARG_OFFSET = -3

def _period_range(
    period: str, 
    start_date: datetime | None = None, 
    end_date: datetime | None = None
) -> tuple[datetime, datetime]:
    """Return (start, end) datetimes for the given period or custom range."""
    # Work in UTC for all logic
    now = datetime.utcnow()
    
    # If custom dates provided, use them
    if start_date and end_date:
        # User provides local dates, we treat them as local 00:00 to 23:59
        # But for simplicity, we use them as-is
        return start_date, end_date
    elif start_date:
        return start_date, now

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now - timedelta(days=30)
    return start, now


def _previous_period_range(
    period: str, 
    start_date: datetime | None = None, 
    end_date: datetime | None = None
) -> tuple[datetime, datetime]:
    """Return the equivalent previous period for comparison."""
    if start_date and end_date:
        duration = end_date - start_date
        return start_date - duration, start_date
        
    start, end = _period_range(period)
    duration = end - start
    return start - duration, start


@router.get("/overview")
async def overview(
    period: str = Query("month", regex="^(today|week|month|year|custom)$"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """KPI overview: total revenue, order count, avg ticket, with period comparison."""
    start, end = _period_range(period, start_date, end_date)
    prev_start, prev_end = _previous_period_range(period)

    # Current period
    result = await db.execute(
        select(
            func.coalesce(func.sum(Sale.total), 0).label("revenue"),
            func.count(func.distinct(func.coalesce(Sale.order_number, Sale.fudo_id))).label("orders"),
            func.coalesce(func.sum(Sale.quantity), 0).label("items_sold"),
        ).where(Sale.sale_date.between(start, end))
    )
    current = result.one()
    curr_revenue = float(current.revenue or 0)
    curr_orders = int(current.orders or 0)

    # Compute average ticket per order (Revenue / unique orders)
    avg_ticket = curr_revenue / curr_orders if curr_orders > 0 else 0

    # Previous period
    prev_start, prev_end = _previous_period_range(period, start_date, end_date)
    prev_result = await db.execute(
        select(
            func.coalesce(func.sum(Sale.total), 0).label("revenue"),
            func.count(func.distinct(func.coalesce(Sale.order_number, Sale.fudo_id))).label("orders"),
        ).where(Sale.sale_date.between(prev_start, prev_end))
    )
    prev = prev_result.one()

    prev_revenue = float(prev.revenue or 0)
    revenue_change = (
        ((curr_revenue - prev_revenue) / prev_revenue * 100)
        if prev_revenue > 0
        else 0
    )

    prev_orders = int(prev.orders or 0)
    curr_orders = int(current.orders or 0)
    orders_change = (
        ((curr_orders - prev_orders) / prev_orders * 100)
        if prev_orders > 0
        else 0
    )

    return {
        "revenue": round(curr_revenue, 2),
        "revenue_change": round(revenue_change, 1),
        "orders": curr_orders,
        "orders_change": round(orders_change, 1),
        "avg_ticket": round(float(avg_ticket), 2),
        "items_sold": int(current.items_sold or 0),
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


@router.get("/sales-trend")
async def sales_trend(
    period: str = Query("month", regex="^(today|week|month|year|custom)$"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Revenue time series grouped by day, including 0-sale days."""
    start, end = _period_range(period, start_date, end_date)

    # Use generate_series to create a continuous list of dates
    # We cast to Date to match the grouped trend dates
    date_series = select(
        func.generate_series(
            func.date_trunc("day", start),
            func.date_trunc("day", end),
            text("interval '1 day'")
        ).label("series_date")
    ).cte("date_series")

    # Group sales by day (adjusted for Argentina time if desired, but trend is usually by UTC day)
    # Actually, let's keep trend in local Argentina day for better alignment with business hours
    sales_subq = (
        select(
            func.date_trunc("day", Sale.sale_date + text(f"interval '{ARG_OFFSET} hours'")).label("sale_day"),
            func.sum(Sale.total).label("revenue"),
            func.count(func.distinct(Sale.order_number)).label("orders"),
        )
        .where(Sale.sale_date.between(start, end))
        .group_by(text("sale_day"))
        .subquery()
    )

    result = await db.execute(
        select(
            date_series.c.series_date,
            func.coalesce(sales_subq.c.revenue, 0).label("revenue"),
            func.coalesce(sales_subq.c.orders, 0).label("orders"),
        )
        .outerjoin(sales_subq, date_series.c.series_date == sales_subq.c.sale_day)
        .order_by(date_series.c.series_date)
    )

    return [
        {
            "date": row.series_date.date().isoformat() if row.series_date else None,
            "revenue": round(float(row.revenue), 2),
            "orders": int(row.orders),
        }
        for row in result.all()
    ]


@router.get("/top-products")
async def top_products(
    period: str = Query("month", regex="^(today|week|month|year|custom)$"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Top products by revenue."""
    start, end = _period_range(period, start_date, end_date)

    # Use subquery to resolve names before grouping (most robust for Postgres)
    subq = (
        select(
            func.coalesce(Product.name, Sale.product_name).label("res_name"),
            Sale.total,
            Sale.quantity,
        )
        .outerjoin(Product, Sale.product_id == Product.id)
        .where(Sale.sale_date.between(start, end))
        .subquery()
    )

    result = await db.execute(
        select(
            subq.c.res_name.label("name"),
            func.coalesce(func.sum(subq.c.total), 0).label("revenue"),
            func.coalesce(func.sum(subq.c.quantity), 0).label("quantity"),
        )
        .group_by(subq.c.res_name)
        .order_by(func.sum(subq.c.total).desc())
        .limit(limit)
    )

    return [
        {
            "name": row.name or "Unknown",
            "revenue": round(float(row.revenue), 2),
            "quantity": int(row.quantity),
        }
        for row in result.all()
    ]


@router.get("/sales-by-category")
async def sales_by_category(
    period: str = Query("month", regex="^(today|week|month|year|custom)$"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Revenue breakdown by product category."""
    start, end = _period_range(period, start_date, end_date)

    # Use subquery for robust grouping
    subq = (
        select(
            func.coalesce(Category.name, "Sin categoría").label("res_cat"),
            Sale.total,
            Sale.quantity,
        )
        .outerjoin(Product, Sale.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(Sale.sale_date.between(start, end))
        .subquery()
    )

    result = await db.execute(
        select(
            subq.c.res_cat.label("category"),
            func.coalesce(func.sum(subq.c.total), 0).label("revenue"),
            func.coalesce(func.sum(subq.c.quantity), 0).label("quantity"),
        )
        .group_by(subq.c.res_cat)
        .order_by(func.sum(subq.c.total).desc())
    )

    return [
        {
            "category": row.category,
            "revenue": round(float(row.revenue), 2),
            "quantity": int(row.quantity),
        }
        for row in result.all()
    ]


@router.get("/hourly-distribution")
async def hourly_distribution(
    period: str = Query("month", regex="^(today|week|month|year|custom)$"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Sales aggregated by hour of day (Argentina Time)."""
    start, end = _period_range(period, start_date, end_date)

    # Use subquery for robust grouping, shifting to local Argentina time
    subq = (
        select(
            extract("hour", Sale.sale_date + text(f"interval '{ARG_OFFSET} hours'")).label("res_hour"),
            Sale.total,
            Sale.id,
        )
        .where(Sale.sale_date.between(start, end))
        .subquery()
    )

    result = await db.execute(
        select(
            subq.c.res_hour.label("hour"),
            func.coalesce(func.sum(subq.c.total), 0).label("revenue"),
            func.count(subq.c.id).label("count"),
        )
        .group_by(subq.c.res_hour)
        .order_by(subq.c.res_hour)
    )

    # Only return hours that have sales (as requested)
    return [
        {
            "hour": int(row.hour),
            "revenue": round(float(row.revenue), 2),
            "count": int(row.count),
        }
        for row in result.all()
        if row.revenue > 0 or row.count > 0
    ]


@router.get("/recent-sales")
async def recent_sales(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Latest sales transactions."""
    result = await db.execute(
        select(
            Sale.id,
            func.coalesce(Sale.order_number, Sale.fudo_id).label("order_number"),
            func.coalesce(Product.name, Sale.product_name, "Producto desconocido").label("product"),
            func.coalesce(Sale.quantity, 0).label("quantity"),
            func.coalesce(Sale.total, 0).label("total"),
            func.coalesce(Sale.payment_method, "N/A").label("payment_method"),
            Sale.sale_date,
        )
        .outerjoin(Product, Sale.product_id == Product.id)
        .order_by(Sale.sale_date.desc())
        .limit(limit)
    )

    return [
        {
            "id": row.id,
            "order_number": row.order_number,
            "product": row.product,
            "quantity": int(row.quantity),
            "total": round(float(row.total), 2),
            "payment_method": row.payment_method,
            "date": row.sale_date.isoformat() if row.sale_date else None,
        }
        for row in result.all()
    ]
