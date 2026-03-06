import asyncio
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session_factory, init_db
from app.sync import sync_sales, sync_categories, sync_products
from app.fudo_client import FudoClient

async def load_historical_data(start_date_str: str = "2025-01-01"):
    print(f"Starting historical data load from {start_date_str}...")
    
    # Initialize DB (create tables if they don't exist)
    await init_db()
    
    start_date = datetime.fromisoformat(start_date_str)
    end_date = datetime.utcnow()
    
    session_factory = get_session_factory()
    
    async with session_factory() as db:
        client = await FudoClient.create()
        try:
            print("Syncing categories and products first...")
            await sync_categories(db, client)
            await sync_products(db, client)
            
            # Sync sales in chunks of 30 days to avoid timeouts or memory issues
            current_start = start_date
            while current_start < end_date:
                current_end = min(current_start + timedelta(days=30), end_date)
                print(f"Syncing sales from {current_start.date()} to {current_end.date()}...")
                
                count = await sync_sales(db, client, date_from=current_start, date_to=current_end)
                print(f"Synced {count} records for this period.")
                
                current_start = current_end
                
            print("Historical data load completed successfully.")
        except Exception as e:
            print(f"Error during historical data load: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await client.close()

if __name__ == "__main__":
    asyncio.run(load_historical_data())
