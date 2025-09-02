"""
Stats Cog for Cozmo Discord Bot.
Provides LA Galaxy team and player statistics commands.
"""

import logging
from discord.ext import commands
import discord

from api.sports_api import get_standings, get_player_stats, SportsAPIError

logger = logging.getLogger(__name__)


class StatsCog(commands.Cog):
    """Cog for statistics-related commands and information."""

    def __init__(self, bot: commands.Bot):
        """Initialize the Stats Cog."""
        self.bot = bot
        logger.info("StatsCog initialized")

    @commands.command(name="standings", aliases=["table", "league"])
    async def standings(self, ctx: commands.Context):
        """
        Display current MLS standings.

        Usage: !standings
        """
        logger.info(f"Standings command invoked by {ctx.author} in {ctx.guild}")

        # Send typing indicator to show the bot is working
        async with ctx.typing():
            try:
                # Fetch standings data from Sports API
                standings_info = await get_standings()

                # Send the formatted standings information
                await ctx.send(standings_info)
                logger.info("Successfully sent MLS standings")

            except SportsAPIError as e:
                # Handle Sports API specific errors
                logger.error(f"Sports API error in standings command: {e}")
                embed = discord.Embed(
                    title="❌ Unable to Fetch Standings",
                    description="Sorry, I'm having trouble getting the latest MLS standings right now. Please try again in a few minutes.",
                    color=discord.Color.red(),
                )
                embed.add_field(
                    name="What you can do:",
                    value="• Try the command again in a few minutes\n• Check the official MLS website for current standings",
                    inline=False,
                )
                await ctx.send(embed=embed)

            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error in standings command: {e}")
                embed = discord.Embed(
                    title="❌ Something Went Wrong",
                    description="An unexpected error occurred while fetching standings. The issue has been logged.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)

    @commands.command(name="playerstats", aliases=["player", "stats"])
    async def player_stats(self, ctx: commands.Context, *, player_name: str = None):
        """
        Display player statistics by name.

        Usage: !playerstats <player_name>
        Example: !playerstats Riqui Puig
        """
        logger.info(f"Player stats command invoked by {ctx.author} in {ctx.guild}")

        # Input validation - check if player name is provided
        if not player_name:
            embed = discord.Embed(
                title="❌ Missing Player Name",
                description="Please provide a player name to search for.",
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="Usage:",
                value="`!playerstats <player_name>`\n\n**Examples:**\n• `!playerstats Riqui Puig`\n• `!playerstats Chicharito`\n• `!playerstats Dejan Joveljic`",
                inline=False,
            )
            await ctx.send(embed=embed)
            logger.info("Player stats command called without player name")
            return

        # Additional input validation - check for reasonable length
        if len(player_name.strip()) < 2:
            embed = discord.Embed(
                title="❌ Invalid Player Name",
                description="Player name must be at least 2 characters long.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
            logger.info(
                f"Player stats command called with too short name: {player_name}"
            )
            return

        if len(player_name.strip()) > 50:
            embed = discord.Embed(
                title="❌ Invalid Player Name",
                description="Player name is too long. Please use a shorter search term.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
            logger.info(
                f"Player stats command called with too long name: {player_name}"
            )
            return

        # Send typing indicator to show the bot is working
        async with ctx.typing():
            try:
                # Fetch player stats from Sports API
                player_info = await get_player_stats(player_name)

                # Send the formatted player information
                await ctx.send(player_info)
                logger.info(f"Successfully sent player stats for: {player_name}")

            except SportsAPIError as e:
                # Handle Sports API specific errors
                logger.error(f"Sports API error in player_stats command: {e}")
                embed = discord.Embed(
                    title="❌ Unable to Fetch Player Statistics",
                    description="Sorry, I'm having trouble getting player statistics right now. Please try again in a few minutes.",
                    color=discord.Color.red(),
                )
                embed.add_field(
                    name="What you can do:",
                    value="• Try the command again in a few minutes\n• Check the spelling of the player name\n• Try searching with just the last name",
                    inline=False,
                )
                await ctx.send(embed=embed)

            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error in player_stats command: {e}")
                embed = discord.Embed(
                    title="❌ Something Went Wrong",
                    description="An unexpected error occurred while fetching player statistics. The issue has been logged.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)

    @standings.error
    async def standings_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Error handler for the standings command."""
        logger.error(f"Command error in standings: {error}")

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ Please wait {error.retry_after:.1f} seconds before using this command again."
            )
        else:
            embed = discord.Embed(
                title="❌ Command Error",
                description="There was an error processing your standings request. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @player_stats.error
    async def player_stats_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Error handler for the player_stats command."""
        logger.error(f"Command error in player_stats: {error}")

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ Please wait {error.retry_after:.1f} seconds before using this command again."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            # This shouldn't happen due to our manual validation, but just in case
            embed = discord.Embed(
                title="❌ Missing Player Name",
                description="Please provide a player name to search for.",
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="Usage:",
                value="`!playerstats <player_name>`",
                inline=False,
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Command Error",
                description="There was an error processing your player stats request. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(StatsCog(bot))
    logger.info("StatsCog added to bot")
