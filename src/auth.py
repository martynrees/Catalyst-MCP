"""Authentication handler for Cisco Catalyst Center API."""
import base64
import httpx
from .config import Config


class CatalystCenterAuth:
    """Handles authentication with Cisco Catalyst Center."""

    def __init__(self) -> None:
        """Initialize authentication handler."""
        self.base_url: str = Config.CATALYST_CENTER_URL.rstrip("/")
        self.username: str = Config.CATALYST_CENTER_USERNAME
        self.password: str = Config.CATALYST_CENTER_PASSWORD
        self.verify_ssl: bool = Config.CATALYST_CENTER_VERIFY_SSL
        self._token: str | None = None

    def _create_basic_auth_header(self) -> str:
        """Create Basic Authentication header value."""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def get_token(self) -> str:
        """Obtain authentication token from Catalyst Center.

        Authenticates using Basic Authentication and retrieves a token
        that is valid for 1 hour. Tokens are cached after first retrieval.

        Returns:
            Authentication token string valid for 1 hour.

        Raises:
            httpx.HTTPError: If authentication request fails.
            ValueError: If response doesn't contain a valid token.
        """
        if self._token:
            return self._token

        url = f"{self.base_url}/dna/system/api/v1/auth/token"
        headers = {
            "Content-Type": "application/json",
            "Authorization": self._create_basic_auth_header()
        }

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self._token = data.get("Token")

            if not self._token:
                raise ValueError("No token returned from authentication endpoint")

            return self._token

    def clear_token(self) -> None:
        """Clear cached authentication token."""
        self._token = None

    async def get_auth_headers(self) -> dict[str, str]:
        """
        Get headers with authentication token.

        Returns:
            dict: Headers including X-Auth-Token
        """
        token = await self.get_token()
        return {
            "X-Auth-Token": token,
            "Content-Type": "application/json"
        }
