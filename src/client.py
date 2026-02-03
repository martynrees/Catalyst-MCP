"""HTTP client for Cisco Catalyst Center API."""
import httpx
from typing import Any
from .auth import CatalystCenterAuth
from .config import Config


class CatalystCenterClient:
    """Client for making requests to Catalyst Center API."""

    def __init__(self) -> None:
        """Initialize API client."""
        self.base_url: str = Config.CATALYST_CENTER_URL.rstrip("/")
        self.verify_ssl: bool = Config.CATALYST_CENTER_VERIFY_SSL
        self.auth: CatalystCenterAuth = CatalystCenterAuth()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        retry_auth: bool = True
    ) -> dict[str, Any]:
        """
        Make authenticated request to Catalyst Center API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., '/dna/intent/api/v1/client-health')
            params: Query parameters
            json: JSON request body
            retry_auth: Whether to retry on auth failure

        Returns:
            dict: Response JSON data

        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = await self.auth.get_auth_headers()

        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # If 401 Unauthorized and we haven't retried yet, clear token and retry
                if e.response.status_code == 401 and retry_auth:
                    self.auth.clear_token()
                    return await self._make_request(
                        method=method,
                        endpoint=endpoint,
                        params=params,
                        json=json,
                        retry_auth=False
                    )
                raise

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make GET request."""
        return await self._make_request("GET", endpoint, params=params)

    async def post(self, endpoint: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make POST request."""
        return await self._make_request("POST", endpoint, json=json)
