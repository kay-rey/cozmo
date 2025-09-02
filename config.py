"""
Configuration management for Cozmo Discord bot.
Handles environment variable loading and validation.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for centralized environment variable management."""

    def __init__(self):
        """Initialize configuration with environment variables."""
        self.DISCORD_TOKEN = self._get_required_env("DISCORD_TOKEN")
        self.SPORTS_API_KEY = self._get_required_env("SPORTS_API_KEY")
        self.NEWS_CHANNEL_ID = self._get_required_env_int("NEWS_CHANNEL_ID")

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error if missing."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    def _get_required_env_int(self, key: str) -> int:
        """Get required integer environment variable or raise error if missing/invalid."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Environment variable {key} must be a valid integer")


# Global configuration instance
config = Config()
