"""
Cozmo Discord Bot - Main Entry Point
A Discord bot for LA Galaxy fans providing match info, stats, news, and trivia.
"""

import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands

from config import config


class CozmoBot(commands.Bot):
    """Main bot class for Cozmo Discord bot."""

    def __init__(self):
        """Initialize the bot with proper intents and configuration."""
        # Set up Discord intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required for reading message content
        intents.reactions = True  # Required for trivia reaction handling

        # Initialize bot with command prefix and intents
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,  # We'll implement custom help if needed
        )

    async def setup_hook(self) -> None:
        """
        Setup hook called when the bot is starting up.
        Loads all cogs from the cogs directory.
        """
        logging.info("Setting up Cozmo bot...")

        # Load all cogs from the cogs directory
        cogs_dir = Path("cogs")
        if cogs_dir.exists():
            for cog_file in cogs_dir.glob("*.py"):
                if cog_file.name != "__init__.py":
                    cog_name = f"cogs.{cog_file.stem}"
                    try:
                        await self.load_extension(cog_name)
                        logging.info(f"Loaded cog: {cog_name}")
                    except Exception as e:
                        logging.error(f"Failed to load cog {cog_name}: {e}")
        else:
            logging.warning("Cogs directory not found")

    async def on_ready(self) -> None:
        """Event handler called when the bot is ready and connected to Discord."""
        print("Cozmo is online and ready to cheer for the Galaxy!")
        logging.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logging.info(f"Connected to {len(self.guilds)} guilds")


async def main():
    """Main function to run the bot."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run the bot
    bot = CozmoBot()

    try:
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested")
    except Exception as e:
        logging.error(f"Bot encountered an error: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
