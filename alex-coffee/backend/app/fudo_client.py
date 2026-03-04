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


async def get_credentials_from_db_or_env() -> tuple[str | None, str | None]:
    """Get API ID and secret from database (if available) or fallback to env var."""
    api_id = None
    api_secret = None
    try:
        from sqlalchemy import select
        from app.database import get_session_factory
        from app.models import APICredential
        from app.encryption import get_encryption_manager

        session_factory = get_session_factory()
        async with session_factory() as db:
            result = await db.execute(
                select(APICredential).order_by(APICredential.updated_at.desc()).limit(1)
            )
            cred = result.scalars().first()
            if cred:
                encryption_manager = get_encryption_manager()
                api_id = cred.fudo_api_id
                api_secret = encryption_manager.decrypt(cred.fudo_api_secret)
                return api_id, api_secret
    except Exception:
        pass

    # Fallback to env var
    return settings.fudo_api_id or api_id, settings.fudo_api_secret or api_secret


class FudoClient:
    BASE_URL = settings.fudo_api_url.rstrip("/")
    AUTH_URL = "https://auth.fu.do/api"

    # Known endpoint patterns from FU.DO OpenAPI v1alpha1.
    ENDPOINTS = {
        "sales": "/v1/sales",
        "products": "/v1/products",
        "categories": "/v1/categories",
        "orders": "/v1/orders",
    }

    def __init__(self, api_id: str | None = None, api_secret: str | None = None):
        # Use provided or fallback to env
        self.api_id = api_id or settings.fudo_api_id
        self.api_secret = api_secret or settings.fudo_api_secret
        
        self._token = None
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
        )

    @classmethod
    async def create(cls, api_id: str | None = None, api_secret: str | None = None) -> FudoClient:
        """Factory method to create a FudoClient with DB credentials if none provided."""
        if not api_id or not api_secret:
            db_id, db_secret = await get_credentials_from_db_or_env()
            api_id = api_id or db_id
            api_secret = api_secret or db_secret
            
        return cls(api_id=api_id, api_secret=api_secret)

    async def _authenticate(self) -> str:
        """Exchange Client ID and Secret for a Bearer token."""
        if not self.api_id or not self.api_secret:
            raise FudoAPIError(401, "Missing Fudo API ID or Secret. Please configure them in the Admin Panel.")
        
        async with httpx.AsyncClient(timeout=10.0) as auth_client:
            payload = {
                "apiKey": self.api_id,
                "apiSecret": self.api_secret
            }
            try:
                # Based on FU.DO docs, token exchange is at https://auth.fu.do/api
                response = await auth_client.post(self.AUTH_URL, json=payload)
                if response.status_code == 401:
                    raise FudoAPIError(401, "Invalid Client Id or Secret. Check FU.DO Admin.")
                response.raise_for_status()
                data = response.json()
                self._token = data.get("token")
                if not self._token:
                    raise FudoAPIError(500, "Auth server returned 200 but no token.")
                return self._token
            except httpx.HTTPError as e:
                raise FudoAPIError(500, f"Failed to reach Fudo Auth server: {str(e)}")

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _request(
        self, method: str, path: str, params: dict | None = None, json: Any = None, _retry: bool = True
    ) -> Any:
        if not self._token:
            await self._authenticate()

        response = await self._client.request(
            method, path, params=params, json=json, headers=self._get_headers()
        )
        
        # Handle expired token
        if response.status_code == 401 and _retry:
            await self._authenticate()
            return await self._request(method, path, params=params, json=json, _retry=False)
            
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
