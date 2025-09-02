"""
News API integration layer for LA Galaxy RSS feed.
Handles RSS feed parsing and latest news retrieval.
"""

import asyncio
import aiohttp
import feedparser
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NewsAPIError(Exception):
    """Custom exception for News API related errors."""

    pass


class NewsAPIClient:
    """Client for LA Galaxy RSS feed with error handling and parsing."""

    def __init__(self):
        self.rss_url = "http://www.lagalaxy.com/rss/news"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _fetch_rss_content(self) -> str:
        """
        Fetch RSS feed content from LA Galaxy website.

        Returns:
            Raw RSS XML content as string

        Raises:
            NewsAPIError: If request fails after retries
        """
        session = await self._get_session()

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with session.get(self.rss_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.debug("RSS feed fetched successfully")
                        return content
                    else:
                        logger.error(
                            f"RSS request failed with status {response.status}"
                        )
                        response.raise_for_status()

            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"RSS request failed after {max_retries} attempts: {e}"
                    )
                    raise NewsAPIError(f"Failed to fetch RSS feed: {e}")

                wait_time = 2**attempt
                logger.warning(
                    f"RSS request failed, retrying in {wait_time} seconds: {e}"
                )
                await asyncio.sleep(wait_time)

        raise NewsAPIError("Maximum retry attempts exceeded")


# Global client instance
news_client = NewsAPIClient()


async def get_latest_news() -> Dict[str, str]:
    """
    Fetch the latest news article from LA Galaxy RSS feed.

    Returns:
        Dictionary containing article information with keys:
        - title: Article title
        - link: Article URL
        - published: Publication date/time
        - summary: Article summary (if available)

    Raises:
        NewsAPIError: If RSS feed cannot be fetched or parsed
    """
    try:
        # Fetch RSS content
        rss_content = await news_client._fetch_rss_content()

        # Parse RSS feed using feedparser
        feed = feedparser.parse(rss_content)

        # Check if feed was parsed successfully
        if feed.bozo and hasattr(feed, "bozo_exception"):
            logger.warning(f"RSS feed parsing warning: {feed.bozo_exception}")

        # Check if there are any entries
        if not feed.entries:
            logger.warning("No articles found in RSS feed")
            raise NewsAPIError("No news articles available")

        # Get the latest (first) article
        latest_article = feed.entries[0]

        # Extract article information
        title = latest_article.get("title", "No title available")
        link = latest_article.get("link", "")

        # Handle publication date
        published = "Unknown date"
        if (
            hasattr(latest_article, "published_parsed")
            and latest_article.published_parsed
        ):
            try:
                pub_time = datetime(*latest_article.published_parsed[:6])
                published = pub_time.strftime("%B %d, %Y at %I:%M %p")
            except (ValueError, TypeError):
                published = latest_article.get("published", "Unknown date")
        elif hasattr(latest_article, "published"):
            published = latest_article.get("published", "Unknown date")

        # Extract summary if available
        summary = latest_article.get("summary", "")
        if summary:
            # Clean up HTML tags and limit length
            import re

            summary = re.sub(r"<[^>]+>", "", summary)  # Remove HTML tags
            if len(summary) > 200:
                summary = summary[:197] + "..."

        article_data = {
            "title": title,
            "link": link,
            "published": published,
            "summary": summary,
        }

        logger.info(f"Successfully fetched latest news: {title}")
        return article_data

    except NewsAPIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching news: {e}")
        raise NewsAPIError(f"Failed to process news data: {e}")
