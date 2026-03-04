"""FU.DO General-Purpose API client.

The FU.DO API docs are at https://dev.fu.do/api (interactive Swagger UI).
This client uses the documented token-based auth (API Secret) and targets
the v1alpha1 endpoints. Endpoint paths may need adjustment once the user
confirms exact routes from the Swagger docs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.config import settings


class FudoAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"FU.DO API error {status_code}: {detail}")


async def get_api_secret_from_db_or_env() -> str:
    """Get API secret from database (if available) or fallback to env var."""
    try:
        from sqlalchemy import select
        from app.database import get_session_factory
        from app.models import APICredential
        from app.encryption import encryption_manager

        session_factory = get_session_factory()
        async with session_factory() as db:
            result = await db.execute(
                select(APICredential).order_by(APICredential.updated_at.desc()).limit(1)
            )
            cred = result.scalars().first()
            if cred:
                return encryption_manager.decrypt(cred.fudo_api_secret)
    except Exception:
        pass

    # Fallback to env var
    return settings.fudo_api_secret


class FudoClient:
    BASE_URL = settings.fudo_api_url.rstrip("/")

    # Known endpoint patterns from FU.DO OpenAPI v1alpha1.
    # Update these if the Swagger docs show different paths.
    ENDPOINTS = {
        "sales": "/v1/sales",
        "products": "/v1/products",
        "categories": "/v1/categories",
        "orders": "/v1/orders",
    }

    def __init__(self, api_secret: str | None = None):
        self.api_secret = api_secret or settings.fudo_api_secret
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers=self._auth_headers(),
        )

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_secret}",
            "Accept": "application/json",
        }

    async def _request(
        self, method: str, path: str, params: dict | None = None, json: Any = None
    ) -> Any:
        response = await self._client.request(method, path, params=params, json=json)
        if response.status_code == 401:
            raise FudoAPIError(401, "Invalid or expired API token. Regenerate in FU.DO Admin > Users.")
        if response.status_code >= 400:
            raise FudoAPIError(response.status_code, response.text)
        return response.json()

    async def get_sales(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if date_from:
            params["from"] = date_from.isoformat()
        if date_to:
            params["to"] = date_to.isoformat()
        data = await self._request("GET", self.ENDPOINTS["sales"], params=params)
        # The API may return {"data": [...]} or a bare list
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        if isinstance(data, list):
            return data
        return []

    async def get_all_sales(
        self, date_from: datetime | None = None, date_to: datetime | None = None
    ) -> list[dict]:
        """Paginate through all sales in the date range."""
        all_sales: list[dict] = []
        offset = 0
        page_size = 500
        while True:
            page = await self.get_sales(date_from, date_to, limit=page_size, offset=offset)
            if not page:
                break
            all_sales.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return all_sales

    async def get_products(self, limit: int = 1000, offset: int = 0) -> list[dict]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        data = await self._request("GET", self.ENDPOINTS["products"], params=params)
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        if isinstance(data, list):
            return data
        return []

    async def get_categories(self) -> list[dict]:
        data = await self._request("GET", self.ENDPOINTS["categories"])
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        if isinstance(data, list):
            return data
        return []

    async def health_check(self) -> bool:
        """Return True if the API responds successfully."""
        try:
            await self._request("GET", self.ENDPOINTS["products"], params={"limit": 1})
            return True
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()
