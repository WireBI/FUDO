from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, case, cast, extract, func, select, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Category, Product, Sale

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

PeriodType = str  # "today" | "week" | "month" | "year"


def _period_range(period: str) -> tuple[datetime, datetime]:
    """Return (start, end) datetimes for the given period."""
    now = datetime.utcnow()
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


def _previous_period_range(period: str) -> tuple[datetime, datetime]:
    """Return the equivalent previous period for comparison."""
    start, end = _period_range(period)
    duration = end - start
    return start - duration, start


@router.get("/overview")
async def overview(
    period: str = Query("month", regex="^(today|week|month|year)$"),
    db: AsyncSession = Depends(get_db),
):
    """KPI overview: total revenue, order count, avg ticket, with period comparison."""
    start, end = _period_range(period)
    prev_start, prev_end = _previous_period_range(period)

    # Current period
    result = await db.execute(
        select(
            func.coalesce(func.sum(Sale.total), 0).label("revenue"),
            func.count(func.distinct(Sale.order_number)).label("orders"),
            func.coalesce(func.avg(Sale.total), 0).label("avg_item"),
            func.coalesce(func.sum(Sale.quantity), 0).label("items_sold"),
        ).where(Sale.sale_date.between(start, end))
    )
    current = result.one()

    # Compute average ticket per order
    order_totals = await db.execute(
        select(func.sum(Sale.total).label("order_total"))
        .where(Sale.sale_date.between(start, end))
        .group_by(Sale.order_number)
    )
    order_totals_list = [float(r[0]) for r in order_totals.all()]
    avg_ticket = sum(order_totals_list) / len(order_totals_list) if order_totals_list else 0

    # Previous period
    prev_result = await db.execute(
        select(
            func.coalesce(func.sum(Sale.total), 0).label("revenue"),
            func.count(func.distinct(Sale.order_number)).label("orders"),
        ).where(Sale.sale_date.between(prev_start, prev_end))
    )
    prev = prev_result.one()

    prev_revenue = float(prev.revenue)
    curr_revenue = float(current.revenue)
    revenue_change = (
        ((curr_revenue - prev_revenue) / prev_revenue * 100)
        if prev_revenue > 0
        else 0
    )

    prev_orders = int(prev.orders)
    curr_orders = int(current.orders)
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
        "avg_ticket": round(avg_ticket, 2),
        "items_sold": int(current.items_sold),
        "period": period,
    }


@router.get("/sales-trend")
async def sales_trend(
    period: str = Query("month", regex="^(today|week|month|year)$"),
    db: AsyncSession = Depends(get_db),
):
    """Revenue time series grouped by day."""
    start, end = _period_range(period)

    result = await db.execute(
        select(
            func.date_trunc("day", Sale.sale_date).label("date"),
            func.sum(Sale.total).label("revenue"),
            func.count(func.distinct(Sale.order_number)).label("orders"),
        )
        .where(Sale.sale_date.between(start, end))
        .group_by(func.date_trunc("day", Sale.sale_date))
        .order_by(func.date_trunc("day", Sale.sale_date))
    )

    return [
        {
            "date": row.date.isoformat() if row.date else None,
            "revenue": round(float(row.revenue), 2),
            "orders": int(row.orders),
        }
        for row in result.all()
    ]


@router.get("/top-products")
async def top_products(
    period: str = Query("month", regex="^(today|week|month|year)$"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Top products by revenue."""
    start, end = _period_range(period)

    result = await db.execute(
        select(
            func.coalesce(Product.name, Sale.product_name).label("name"),
            func.sum(Sale.total).label("revenue"),
            func.sum(Sale.quantity).label("quantity"),
        )
        .outerjoin(Product, Sale.product_id == Product.id)
        .where(Sale.sale_date.between(start, end))
        .group_by(func.coalesce(Product.name, Sale.product_name))
        .order_by(func.sum(Sale.total).desc())
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
    period: str = Query("month", regex="^(today|week|month|year)$"),
    db: AsyncSession = Depends(get_db),
):
    """Revenue breakdown by product category."""
    start, end = _period_range(period)

    result = await db.execute(
        select(
            func.coalesce(Category.name, "Sin categoría").label("category"),
            func.sum(Sale.total).label("revenue"),
            func.sum(Sale.quantity).label("quantity"),
        )
        .outerjoin(Product, Sale.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(Sale.sale_date.between(start, end))
        .group_by(func.coalesce(Category.name, "Sin categoría"))
        .order_by(func.sum(Sale.total).desc())
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
    period: str = Query("month", regex="^(today|week|month|year)$"),
    db: AsyncSession = Depends(get_db),
):
    """Sales aggregated by hour of day."""
    start, end = _period_range(period)

    result = await db.execute(
        select(
            extract("hour", Sale.sale_date).label("hour"),
            func.sum(Sale.total).label("revenue"),
            func.count(Sale.id).label("count"),
        )
        .where(Sale.sale_date.between(start, end))
        .group_by(extract("hour", Sale.sale_date))
        .order_by(extract("hour", Sale.sale_date))
    )

    # Fill all 24 hours
    hourly = {int(r.hour): {"revenue": round(float(r.revenue), 2), "count": int(r.count)} for r in result.all()}
    return [
        {"hour": h, "revenue": hourly.get(h, {}).get("revenue", 0), "count": hourly.get(h, {}).get("count", 0)}
        for h in range(24)
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
            Sale.order_number,
            func.coalesce(Product.name, Sale.product_name).label("product"),
            Sale.quantity,
            Sale.total,
            Sale.payment_method,
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
            "product": row.product or "Unknown",
            "quantity": row.quantity,
            "total": round(float(row.total), 2),
            "payment_method": row.payment_method,
            "date": row.sale_date.isoformat() if row.sale_date else None,
        }
        for row in result.all()
    ]
