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
        logger = logging.getLogger(__name__)
        logger.info("Setting up Cozmo bot...")

        # Load all cogs from the cogs directory
        cogs_dir = Path("cogs")
        if not cogs_dir.exists():
            logger.error("Cogs directory not found - bot will have no functionality")
            return

        loaded_cogs = 0
        failed_cogs = 0

        for cog_file in cogs_dir.glob("*.py"):
            if cog_file.name != "__init__.py":
                cog_name = f"cogs.{cog_file.stem}"
                try:
                    await self.load_extension(cog_name)
                    logger.info(f"Successfully loaded cog: {cog_name}")
                    loaded_cogs += 1
                except commands.ExtensionNotFound:
                    logger.error(f"Cog not found: {cog_name}")
                    failed_cogs += 1
                except commands.ExtensionAlreadyLoaded:
                    logger.warning(f"Cog already loaded: {cog_name}")
                except commands.ExtensionFailed as e:
                    logger.error(f"Failed to load cog {cog_name}: {e}", exc_info=True)
                    failed_cogs += 1
                except Exception as e:
                    logger.error(
                        f"Unexpected error loading cog {cog_name}: {e}", exc_info=True
                    )
                    failed_cogs += 1

        logger.info(f"Cog loading complete: {loaded_cogs} loaded, {failed_cogs} failed")

        if loaded_cogs == 0:
            logger.error(
                "No cogs were loaded successfully - bot will have no functionality"
            )

    async def on_ready(self) -> None:
        """Event handler called when the bot is ready and connected to Discord."""
        logger = logging.getLogger(__name__)
        print("Cozmo is online and ready to cheer for the Galaxy!")
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Log guild information
        for guild in self.guilds:
            logger.info(
                f"Connected to guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})"
            )

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Global error handler for all command errors."""
        logger = logging.getLogger(__name__)

        # Log the error with context
        logger.error(
            f"Command error in {ctx.command.name if ctx.command else 'unknown'} "
            f"by {ctx.author} in {ctx.guild.name if ctx.guild else 'DM'}: {error}",
            exc_info=True,
        )

        # Handle specific error types
        if isinstance(error, commands.CommandNotFound):
            # Don't respond to unknown commands to avoid spam
            return
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("❌ This command is currently disabled.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ This command cannot be used in private messages.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await ctx.send(
                f"❌ I need the following permissions to run this command: {missing_perms}"
            )
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ Command is on cooldown. Try again in {error.retry_after:.1f} seconds."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"❌ Missing required argument: `{error.param.name}`. Use `!help {ctx.command.name}` for usage info."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"❌ Invalid argument provided. Use `!help {ctx.command.name}` for usage info."
            )
        else:
            # Generic error message for unexpected errors
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An unexpected error occurred. The issue has been logged and will be investigated.",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="What you can do:",
                value="• Try the command again in a few moments\n• Check your command syntax\n• Contact support if the issue persists",
                inline=False,
            )
            await ctx.send(embed=embed)

    async def on_error(self, event: str, *args, **kwargs) -> None:
        """Global error handler for non-command errors."""
        logger = logging.getLogger(__name__)
        logger.error(f"Unhandled error in event {event}", exc_info=True)


async def main():
    """Main function to run the bot."""
    # Set up comprehensive logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Configure logging with both file and console handlers
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler("logs/cozmo.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    # Set specific log levels for different components
    logging.getLogger("discord").setLevel(logging.WARNING)  # Reduce Discord.py noise
    logging.getLogger("aiohttp").setLevel(logging.WARNING)  # Reduce aiohttp noise

    logger = logging.getLogger(__name__)
    logger.info("Starting Cozmo Discord Bot...")

    # Create and run the bot
    bot = CozmoBot()

    try:
        logger.info("Attempting to connect to Discord...")
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except discord.LoginFailure as e:
        logger.error(f"Failed to login to Discord - check your token: {e}")
    except discord.ConnectionClosed as e:
        logger.error(f"Discord connection closed unexpectedly: {e}")
    except Exception as e:
        logger.error(f"Bot encountered an unexpected error: {e}", exc_info=True)
    finally:
        logger.info("Shutting down bot...")
        try:
            # Close API client sessions
            from api.sports_api import sports_client
            from api.news_api import news_client

            await sports_client.close()
            await news_client.close()

            await bot.close()
            logger.info("Bot shutdown complete")
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")


if __name__ == "__main__":
    asyncio.run(main())
