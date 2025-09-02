"""
News Cog for LA Galaxy Discord bot.
Handles news commands and automated news checking with duplicate prevention.
"""

import os
import asyncio
import logging
from typing import Optional
from discord.ext import commands, tasks
import discord

from api.news_api import get_latest_news, NewsAPIError
from config import NEWS_CHANNEL_ID

logger = logging.getLogger(__name__)


class NewsCog(commands.Cog):
    """Cog for handling LA Galaxy news functionality."""

    def __init__(self, bot):
        self.bot = bot
        self.last_article_file = "data/last_article.txt"

        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)

        # Initialize last article file if it doesn't exist
        self._initialize_last_article_file()

    def _initialize_last_article_file(self):
        """Initialize the last article tracking file if it doesn't exist."""
        try:
            if not os.path.exists(self.last_article_file):
                with open(self.last_article_file, "w", encoding="utf-8") as f:
                    f.write("")
                logger.info("Created last_article.txt file")
        except IOError as e:
            logger.error(f"Failed to initialize last article file: {e}")

    def _read_last_article_url(self) -> Optional[str]:
        """
        Read the last posted article URL from file.

        Returns:
            The last article URL or None if file doesn't exist or is empty
        """
        try:
            if os.path.exists(self.last_article_file):
                with open(self.last_article_file, "r", encoding="utf-8") as f:
                    url = f.read().strip()
                    return url if url else None
            return None
        except IOError as e:
            logger.error(f"Failed to read last article URL: {e}")
            return None

    def _write_last_article_url(self, url: str) -> bool:
        """
        Write the last posted article URL to file.

        Args:
            url: The article URL to store

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.last_article_file, "w", encoding="utf-8") as f:
                f.write(url)
            logger.info(f"Updated last article URL: {url}")
            return True
        except IOError as e:
            logger.error(f"Failed to write last article URL: {e}")
            return False

    def _is_duplicate_article(self, article_url: str) -> bool:
        """
        Check if the article URL is a duplicate of the last posted article.

        Args:
            article_url: The URL to check

        Returns:
            True if this is a duplicate, False if it's new
        """
        last_url = self._read_last_article_url()
        return last_url == article_url if last_url else False

    @commands.command(name="news")
    async def news_command(self, ctx):
        """
        Fetch and display the latest LA Galaxy news article.

        Usage: !news
        """
        try:
            # Fetch the latest news article
            article = await get_latest_news()

            # Format the news output for Discord
            title = article.get("title", "No title available")
            link = article.get("link", "")
            published = article.get("published", "Unknown date")

            # Create formatted message
            if link:
                message = f"**Latest LA Galaxy News:**\n\n**{title}**\n{link}\n\n*Published: {published}*"
            else:
                message = f"**Latest LA Galaxy News:**\n\n**{title}**\n\n*Published: {published}*"

            # Send the message
            await ctx.send(message)
            logger.info(
                f"News command executed successfully in channel {ctx.channel.id}"
            )

        except NewsAPIError as e:
            error_message = "Sorry, I couldn't fetch the latest news right now. Please try again later."
            await ctx.send(error_message)
            logger.error(f"News API error in news command: {e}")

        except Exception as e:
            error_message = "An unexpected error occurred while fetching news."
            await ctx.send(error_message)
            logger.error(f"Unexpected error in news command: {e}")

    @tasks.loop(minutes=20)
    async def check_for_news(self):
        """
        Background task that checks for new LA Galaxy news every 20 minutes.
        Posts new articles to the designated news channel if they haven't been posted before.
        """
        try:
            # Fetch the latest news article
            article = await get_latest_news()
            article_url = article.get("link", "")

            # Skip if no URL available
            if not article_url:
                logger.warning(
                    "No URL found in latest article, skipping duplicate check"
                )
                return

            # Check if this is a duplicate article
            if self._is_duplicate_article(article_url):
                logger.debug("Article already posted, skipping")
                return

            # Get the news channel
            news_channel = self.bot.get_channel(NEWS_CHANNEL_ID)
            if not news_channel:
                logger.error(f"News channel with ID {NEWS_CHANNEL_ID} not found")
                return

            # Format the news message
            title = article.get("title", "No title available")
            published = article.get("published", "Unknown date")

            message = f"🚨 **New LA Galaxy News!** 🚨\n\n**{title}**\n{article_url}\n\n*Published: {published}*"

            # Post the news to the channel
            await news_channel.send(message)

            # Update the last article URL to prevent duplicates
            if self._write_last_article_url(article_url):
                logger.info(f"Posted new article and updated tracking: {title}")
            else:
                logger.warning("Posted article but failed to update tracking file")

        except NewsAPIError as e:
            logger.error(f"News API error in automated check: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in automated news check: {e}")

    @check_for_news.before_loop
    async def before_check_for_news(self):
        """Wait for the bot to be ready before starting the news checking loop."""
        await self.bot.wait_until_ready()
        logger.info("Starting automated news checking every 20 minutes")

    async def cog_load(self):
        """Start the news checking task when the cog is loaded."""
        self.check_for_news.start()

    async def cog_unload(self):
        """Stop the news checking task when the cog is unloaded."""
        self.check_for_news.cancel()


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(NewsCog(bot))
