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

    count = 0
    for cat in categories:
        fudo_id = str(cat.get("id", cat.get("_id", "")))
        name = cat.get("name", cat.get("nombre", "Unknown"))
        if not fudo_id:
            continue

        stmt = (
            pg_insert(Category)
            .values(fudo_id=fudo_id, name=name, updated_at=datetime.utcnow())
            .on_conflict_do_update(
                index_elements=["fudo_id"],
                set_={"name": name, "updated_at": datetime.utcnow()},
            )
        )
        await db.execute(stmt)
        count += 1

    await db.commit()
    await _log_sync(db, "categories", "success", records=count)
    return count


async def sync_products(db: AsyncSession, client: FudoClient) -> int:
    """Sync products from FU.DO into the database."""
    try:
        products = await client.get_products()
    except Exception as e:
        await _log_sync(db, "products", "error", error=str(e))
        raise

    # Build category fudo_id → db id map
    result = await db.execute(select(Category.fudo_id, Category.id))
    cat_map = {row[0]: row[1] for row in result.all()}

    count = 0
    for prod in products:
        fudo_id = str(prod.get("id", prod.get("_id", "")))
        name = prod.get("name", prod.get("nombre", "Unknown"))
        price = prod.get("price", prod.get("precio", 0)) or 0
        active = prod.get("active", prod.get("activo", True))
        cat_fudo_id = str(prod.get("categoryId", prod.get("categoriaId", "")))
        category_id = cat_map.get(cat_fudo_id)

        if not fudo_id:
            continue

        stmt = (
            pg_insert(Product)
            .values(
                fudo_id=fudo_id,
                name=name,
                category_id=category_id,
                price=price,
                active=active,
                updated_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["fudo_id"],
                set_={
                    "name": name,
                    "category_id": category_id,
                    "price": price,
                    "active": active,
                    "updated_at": datetime.utcnow(),
                },
            )
        )
        await db.execute(stmt)
        count += 1

    await db.commit()
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

    # Build product fudo_id → db id map
    result = await db.execute(select(Product.fudo_id, Product.id))
    prod_map = {row[0]: row[1] for row in result.all()}

    count = 0
    for sale in sales:
        fudo_id = str(sale.get("id", sale.get("_id", "")))
        if not fudo_id:
            continue

        # Parse sale date — try multiple field names
        sale_date_raw = sale.get("date", sale.get("fecha", sale.get("createdAt", "")))
        if isinstance(sale_date_raw, str):
            try:
                # Based on user error, this can produce offset-aware datetime
                # We normalize to naive UTC (Postgres requirement for TIMESTAMP WITHOUT TIME ZONE)
                sale_date = datetime.fromisoformat(sale_date_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                sale_date = datetime.utcnow()
        elif isinstance(sale_date_raw, datetime):
            sale_date = sale_date_raw.replace(tzinfo=None)
        else:
            sale_date = datetime.utcnow()

        # Handle items within a sale (FU.DO may return sales with nested items)
        items = sale.get("items", sale.get("productos", []))
        if items:
            for item in items:
                item_fudo_id = f"{fudo_id}_{item.get('id', item.get('_id', count))}"
                prod_fudo_id = str(item.get("productId", item.get("productoId", "")))
                product_name = item.get("name", item.get("nombre", ""))
                quantity = item.get("quantity", item.get("cantidad", 1)) or 1
                unit_price = item.get("unitPrice", item.get("precioUnitario", item.get("price", 0))) or 0
                total = item.get("total", item.get("subtotal", float(unit_price) * quantity))

                stmt = (
                    pg_insert(Sale)
                    .values(
                        fudo_id=item_fudo_id,
                        product_id=prod_map.get(prod_fudo_id),
                        product_name=product_name,
                        quantity=quantity,
                        unit_price=unit_price,
                        total=total,
                        sale_date=sale_date,
                        payment_method=sale.get("paymentMethod", sale.get("metodoPago")),
                        order_number=sale.get("orderNumber", sale.get("numero")),
                    )
                    .on_conflict_do_update(
                        index_elements=["fudo_id"],
                        set_={"total": total, "quantity": quantity},
                    )
                )
                await db.execute(stmt)
                count += 1
        else:
            # Flat sale record (no nested items)
            product_name = sale.get("productName", sale.get("producto", ""))
            prod_fudo_id = str(sale.get("productId", sale.get("productoId", "")))
            quantity = sale.get("quantity", sale.get("cantidad", 1)) or 1
            unit_price = sale.get("unitPrice", sale.get("precioUnitario", sale.get("price", 0))) or 0
            total = sale.get("total", float(unit_price) * quantity)

            stmt = (
                pg_insert(Sale)
                .values(
                    fudo_id=fudo_id,
                    product_id=prod_map.get(prod_fudo_id),
                    product_name=product_name,
                    quantity=quantity,
                    unit_price=unit_price,
                    total=total,
                    sale_date=sale_date,
                    payment_method=sale.get("paymentMethod", sale.get("metodoPago")),
                    order_number=sale.get("orderNumber", sale.get("numero")),
                )
                .on_conflict_do_update(
                    index_elements=["fudo_id"],
                    set_={"total": total, "quantity": quantity},
                )
            )
            await db.execute(stmt)
            count += 1

    await db.commit()
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
