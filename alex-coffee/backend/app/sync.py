"""Data sync service — pulls data from FU.DO API and upserts into Neon PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.fudo_client import FudoClient
from app.models import Category, Product, Sale, SyncLog


async def _log_sync(
    db: AsyncSession,
    sync_type: str,
    status: str,
    records: int = 0,
    error: str | None = None,
) -> SyncLog:
    log = SyncLog(
        sync_type=sync_type,
        status=status,
        records_synced=records,
        error_message=error,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow() if status != "running" else None,
    )
    db.add(log)
    await db.commit()
    return log


async def sync_categories(db: AsyncSession, client: FudoClient) -> int:
    """Sync categories from FU.DO into the database."""
    try:
        categories = await client.get_categories()
    except Exception as e:
        await _log_sync(db, "categories", "error", error=str(e))
        raise

    if not categories:
        await _log_sync(db, "categories", "success", records=0)
        return 0

    values = []
    for cat in categories:
        fudo_id = str(cat.get("id", ""))
        name = cat.get("name", "Unknown")
        if fudo_id:
            values.append({"fudo_id": fudo_id, "name": name, "updated_at": datetime.utcnow()})

    if values:
        stmt = (
            pg_insert(Category)
            .values(values)
            .on_conflict_do_update(
                index_elements=["fudo_id"],
                set_={"name": Category.name, "updated_at": datetime.utcnow()},
            )
        )
        await db.execute(stmt)
        await db.commit()

    count = len(values)
    await _log_sync(db, "categories", "success", records=count)
    return count


async def sync_products(db: AsyncSession, client: FudoClient) -> int:
    """Sync products from FU.DO into the database."""
    try:
        products = await client.get_products()
    except Exception as e:
        await _log_sync(db, "products", "error", error=str(e))
        raise

    if not products:
        await _log_sync(db, "products", "success", records=0)
        return 0

    # Build category fudo_id → db id map
    result = await db.execute(select(Category.fudo_id, Category.id))
    cat_map = {row[0]: row[1] for row in result.all()}

    values = []
    for prod in products:
        fudo_id = str(prod.get("id", ""))
        name = prod.get("name", "Unknown")
        price = prod.get("price", 0) or 0
        active = prod.get("active", True)
        cat_fudo_id = str(prod.get("categoryId", ""))
        category_id = cat_map.get(cat_fudo_id)

        if fudo_id:
            values.append({
                "fudo_id": fudo_id,
                "name": name,
                "category_id": category_id,
                "price": price,
                "active": active,
                "updated_at": datetime.utcnow(),
            })

    if values:
        stmt = (
            pg_insert(Product)
            .values(values)
            .on_conflict_do_update(
                index_elements=["fudo_id"],
                set_={
                    "name": Product.name,
                    "category_id": Product.category_id,
                    "price": Product.price,
                    "active": Product.active,
                    "updated_at": datetime.utcnow(),
                },
            )
        )
        await db.execute(stmt)
        await db.commit()

    count = len(values)
    await _log_sync(db, "products", "success", records=count)
    return count


async def sync_sales(
    db: AsyncSession,
    client: FudoClient,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> int:
    """Sync sales from FU.DO into the database."""
    if date_from is None:
        date_from = datetime.utcnow() - timedelta(days=30)
    if date_to is None:
        date_to = datetime.utcnow()

    try:
        sales = await client.get_all_sales(date_from, date_to)
    except Exception as e:
        await _log_sync(db, "sales", "error", error=str(e))
        raise

    if not sales:
        await _log_sync(db, "sales", "success", records=0)
        return 0

    # Build product fudo_id → db id map
    result = await db.execute(select(Product.fudo_id, Product.id))
    prod_map = {row[0]: row[1] for row in result.all()}

    values = []
    for sale in sales:
        fudo_id = str(sale.get("id", ""))
        if not fudo_id:
            continue

        # Parse sale date
        sale_date_raw = sale.get("createdAt", "")
        if isinstance(sale_date_raw, str):
            try:
                sale_date = datetime.fromisoformat(sale_date_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                sale_date = datetime.utcnow()
        elif isinstance(sale_date_raw, datetime):
            sale_date = sale_date_raw.replace(tzinfo=None)
        else:
            sale_date = datetime.utcnow()

        # Handle items within a sale
        items = sale.get("items", [])
        if items:
            for item in items:
                item_fudo_id = f"{fudo_id}_{item.get('id', '0')}"
                prod_fudo_id = str(item.get("productId", ""))
                product_name = item.get("productName", "")
                quantity = item.get("quantity", 1) or 1
                unit_price = float(item.get("price", 0) or 0)
                total = float(item.get("total", unit_price * quantity) or 0)

                values.append({
                    "fudo_id": item_fudo_id,
                    "product_id": prod_map.get(prod_fudo_id),
                    "product_name": product_name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total": total,
                    "sale_date": sale_date,
                    "payment_method": sale.get("saleType"),
                    "order_number": sale.get("saleNumber", str(fudo_id)),
                })
        else:
            # Fallback for flat sale record if items missing
            total = float(sale.get("total", 0) or 0)
            values.append({
                "fudo_id": fudo_id,
                "product_id": None,
                "product_name": "Sale Total",
                "quantity": 1,
                "unit_price": total,
                "total": total,
                "sale_date": sale_date,
                "payment_method": sale.get("saleType"),
                "order_number": sale.get("saleNumber", str(fudo_id)),
            })

    # Batch insert in chunks to avoid large parameter limits
    chunk_size = 500
    for i in range(0, len(values), chunk_size):
        chunk = values[i : i + chunk_size]
        stmt = (
            pg_insert(Sale)
            .values(chunk)
            .on_conflict_do_update(
                index_elements=["fudo_id"],
                set_={
                    "total": Sale.total,
                    "quantity": Sale.quantity,
                    "product_id": Sale.product_id,
                    "product_name": Sale.product_name,
                },
            )
        )
        await db.execute(stmt)
    
    await db.commit()
    count = len(values)
    await _log_sync(db, "sales", "success", records=count)
    return count


async def run_full_sync(
    db: AsyncSession,
    days_back: int = 30,
) -> dict:
    """Run a complete sync of categories, products, and sales."""
    client = await FudoClient.create()
    try:
        cat_count = await sync_categories(db, client)
        prod_count = await sync_products(db, client)
        sale_count = await sync_sales(
            db,
            client,
            date_from=datetime.utcnow() - timedelta(days=days_back),
        )
        return {
            "status": "success",
            "categories": cat_count,
            "products": prod_count,
            "sales": sale_count,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        await client.close()
