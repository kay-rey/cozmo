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
        import logging

        self.logger = logging.getLogger(__name__)

        try:
            self.DISCORD_TOKEN = self._get_required_env("DISCORD_TOKEN")
            self.SPORTS_API_KEY = self._get_required_env("SPORTS_API_KEY")
            self.NEWS_CHANNEL_ID = self._get_optional_env_int("NEWS_CHANNEL_ID")

            self.logger.info("Configuration loaded successfully")
            self._validate_config()

        except Exception as e:
            self.logger.error(f"Configuration initialization failed: {e}")
            raise

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error if missing."""
        value = os.getenv(key)
        if not value:
            self.logger.error(f"Missing required environment variable: {key}")
            raise ValueError(f"Required environment variable {key} is not set")

        # Basic validation for token format
        if key == "DISCORD_TOKEN" and not self._validate_discord_token(value):
            self.logger.error("Invalid Discord token format")
            raise ValueError("Discord token appears to be invalid")

        return value

    def _get_required_env_int(self, key: str) -> int:
        """Get required integer environment variable or raise error if missing/invalid."""
        value = os.getenv(key)
        if not value:
            self.logger.error(f"Missing required environment variable: {key}")
            raise ValueError(f"Required environment variable {key} is not set")
        try:
            int_value = int(value)
            if int_value <= 0:
                raise ValueError(
                    f"Environment variable {key} must be a positive integer"
                )
            return int_value
        except ValueError as e:
            self.logger.error(f"Invalid integer value for {key}: {value}")
            raise ValueError(
                f"Environment variable {key} must be a valid positive integer"
            )

    def _get_optional_env_int(self, key: str) -> Optional[int]:
        """Get optional integer environment variable, return None if missing."""
        value = os.getenv(key)
        if not value:
            self.logger.info(f"Optional environment variable {key} not set")
            return None

        # Skip placeholder values
        if value in ["your_news_channel_id_here", "your_channel_id_here"]:
            self.logger.info(
                f"Environment variable {key} contains placeholder value, skipping"
            )
            return None

        try:
            int_value = int(value)
            if int_value <= 0:
                self.logger.warning(
                    f"Environment variable {key} must be a positive integer, got: {value}"
                )
                return None
            return int_value
        except ValueError:
            self.logger.info(
                f"Invalid integer value for {key}: {value} - treating as not set"
            )
            return None

    def _validate_discord_token(self, token: str) -> bool:
        """Basic validation for Discord token format."""
        # Discord tokens are typically 59+ characters and contain base64-like characters
        if len(token) < 50:
            return False
        # Check for basic token structure (should contain dots for JWT-like structure)
        return "." in token

    def _validate_config(self) -> None:
        """Validate the loaded configuration."""
        # Required validations
        required_validations = [
            (self.DISCORD_TOKEN, "Discord token"),
            (self.SPORTS_API_KEY, "Sports API key"),
        ]

        for value, name in required_validations:
            if not value:
                raise ValueError(f"{name} is empty or invalid")

        # Optional validations (just log warnings)
        if self.NEWS_CHANNEL_ID is None:
            self.logger.info(
                "News channel ID not configured - news features will be disabled"
            )

        self.logger.info("All configuration values validated successfully")


# Global configuration instance
config = Config()
