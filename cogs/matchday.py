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
    @commands.cooldown(1, 3, commands.BucketType.user)  # 1 use per 3 seconds per user
    async def next_match(self, ctx: commands.Context):
        """
        Display information about LA Galaxy's next upcoming match.

        Usage: !nextmatch
        """
        logger.info(
            f"Next match command invoked by {ctx.author} in {ctx.guild} - Command: {ctx.invoked_with}"
        )

        # Send typing indicator to show the bot is working
        async with ctx.typing():
            try:
                # Fetch next match data from Sports API with timeout protection
                import asyncio

                match_data = await asyncio.wait_for(
                    get_next_match(),
                    timeout=25.0,  # 25 seconds max
                )

                if match_data is None:
                    # No upcoming matches found
                    embed = discord.Embed(
                        title="🏆 LA Galaxy Schedule",
                        description="No upcoming matches are currently scheduled. Check back later for updates!",
                        color=discord.Color.blue(),
                    )
                    embed.set_footer(
                        text="Go Galaxy! ⭐",
                        icon_url="https://logos-world.net/wp-content/uploads/2020/06/LA-Galaxy-Logo.png",
                    )
                    await ctx.send(embed=embed)
                    logger.info("No upcoming matches found")
                else:
                    # Create rich embed for match information
                    embed = discord.Embed(
                        title="🏆 Next LA Galaxy Match",
                        description=f"**{match_data['competition']}**",
                        color=discord.Color.gold(),
                    )

                    # Set main match info
                    match_title = (
                        f"LA Galaxy {match_data['match_type']} {match_data['opponent']}"
                    )
                    embed.add_field(
                        name="⚽ Match",
                        value=match_title,
                        inline=False,
                    )

                    # Add date and time
                    embed.add_field(
                        name="📅 Date",
                        value=match_data["date"],
                        inline=True,
                    )
                    embed.add_field(
                        name="🕐 Time",
                        value=match_data["time"],
                        inline=True,
                    )
                    embed.add_field(
                        name="🏟️ Venue",
                        value=match_data["venue"],
                        inline=True,
                    )

                    # Add season/round info if available
                    if match_data["season"] or match_data["round"]:
                        extra_info = []
                        if match_data["season"]:
                            extra_info.append(f"Season: {match_data['season']}")
                        if match_data["round"]:
                            extra_info.append(f"Round: {match_data['round']}")

                        embed.add_field(
                            name="📊 Details",
                            value=" • ".join(extra_info),
                            inline=False,
                        )

                    # Set team badge as thumbnail if available
                    if match_data["galaxy_badge"]:
                        embed.set_thumbnail(url=match_data["galaxy_badge"])

                    # Add home/away indicator
                    location_emoji = "🏠" if match_data["is_home"] else "✈️"
                    location_text = (
                        "Home Game" if match_data["is_home"] else "Away Game"
                    )
                    embed.add_field(
                        name=f"{location_emoji} Location",
                        value=location_text,
                        inline=True,
                    )

                    # Set footer with data source
                    data_source = match_data.get("source", "TheSportsDB")
                    embed.set_footer(
                        text=f"Go Galaxy! ⭐ • Data from {data_source}",
                        icon_url="https://logos-world.net/wp-content/uploads/2020/06/LA-Galaxy-Logo.png",
                    )

                    await ctx.send(embed=embed)
                    logger.info("Successfully sent next match embed")

            except asyncio.TimeoutError:
                logger.error("Timeout error in next_match command")
                embed = discord.Embed(
                    title="⏰ Request Timeout",
                    description="The match information request took too long. Please try again in a moment.",
                    color=discord.Color.orange(),
                )
                await ctx.send(embed=embed)

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
