"""
Matchday Cog for Cozmo Discord Bot.
Provides LA Galaxy match information commands.
"""

import logging
from discord.ext import commands
import discord

from api.sports_api import get_next_match, SportsAPIError

logger = logging.getLogger(__name__)


class MatchdayCog(commands.Cog):
    """Cog for match-related commands and information."""

    def __init__(self, bot: commands.Bot):
        """Initialize the Matchday Cog."""
        self.bot = bot
        logger.info("MatchdayCog initialized")

    @commands.command(name="nextmatch", aliases=["next", "match"])
    async def next_match(self, ctx: commands.Context):
        """
        Display information about LA Galaxy's next upcoming match.

        Usage: !nextmatch
        """
        logger.info(f"Next match command invoked by {ctx.author} in {ctx.guild}")

        # Send typing indicator to show the bot is working
        async with ctx.typing():
            try:
                # Fetch next match data from Sports API
                match_info = await get_next_match()

                if match_info is None:
                    # No upcoming matches found
                    embed = discord.Embed(
                        title="🏆 LA Galaxy Schedule",
                        description="No upcoming matches are currently scheduled. Check back later for updates!",
                        color=discord.Color.blue(),
                    )
                    embed.set_footer(text="Go Galaxy! ⭐")
                    await ctx.send(embed=embed)
                    logger.info("No upcoming matches found")
                else:
                    # Send the formatted match information
                    await ctx.send(match_info)
                    logger.info("Successfully sent next match information")

            except SportsAPIError as e:
                # Handle Sports API specific errors
                logger.error(f"Sports API error in next_match command: {e}")
                embed = discord.Embed(
                    title="❌ Unable to Fetch Match Information",
                    description="Sorry, I'm having trouble getting the latest match information right now. Please try again in a few minutes.",
                    color=discord.Color.red(),
                )
                embed.add_field(
                    name="What you can do:",
                    value="• Try the command again in a few minutes\n• Check the official LA Galaxy website for match schedules",
                    inline=False,
                )
                await ctx.send(embed=embed)

            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error in next_match command: {e}")
                embed = discord.Embed(
                    title="❌ Something Went Wrong",
                    description="An unexpected error occurred while fetching match information. The issue has been logged.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)

    @next_match.error
    async def next_match_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Error handler for the next_match command."""
        logger.error(f"Command error in next_match: {error}")

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ Please wait {error.retry_after:.1f} seconds before using this command again."
            )
        else:
            embed = discord.Embed(
                title="❌ Command Error",
                description="There was an error processing your request. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(MatchdayCog(bot))
    logger.info("MatchdayCog added to bot")
