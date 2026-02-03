"""Configuration management for Catalyst Center MCP server."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings for Catalyst Center API."""

    CATALYST_CENTER_URL = os.getenv("CATALYST_CENTER_URL", "")
    CATALYST_CENTER_USERNAME = os.getenv("CATALYST_CENTER_USERNAME", "")
    CATALYST_CENTER_PASSWORD = os.getenv("CATALYST_CENTER_PASSWORD", "")
    CATALYST_CENTER_VERIFY_SSL = os.getenv("CATALYST_CENTER_VERIFY_SSL", "true").lower() == "true"

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration settings."""
        if not cls.CATALYST_CENTER_URL:
            raise ValueError("CATALYST_CENTER_URL environment variable is required")
        if not cls.CATALYST_CENTER_USERNAME:
            raise ValueError("CATALYST_CENTER_USERNAME environment variable is required")
        if not cls.CATALYST_CENTER_PASSWORD:
            raise ValueError("CATALYST_CENTER_PASSWORD environment variable is required")
