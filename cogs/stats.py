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
    async def standings(self, ctx: commands.Context, conference: str = None):
        """
        Display current MLS standings organized by Eastern and Western conferences.

        Usage: !standings [west|east]
        Examples:
        - !standings (shows both conferences)
        - !standings west (shows only Western Conference where LA Galaxy plays)
        - !standings east (shows only Eastern Conference)
        """
        logger.info(f"Standings command invoked by {ctx.author} in {ctx.guild}")

        # Send typing indicator to show the bot is working
        async with ctx.typing():
            try:
                # Fetch standings data from Sports API
                standings_data = await get_standings()

                # Get team data first
                west_teams = standings_data.get("western_conference", [])
                east_teams = standings_data.get("eastern_conference", [])
                has_standings = standings_data.get("has_standings", False)

                # Parse conference filter
                show_west = True
                show_east = True
                if conference:
                    conference = conference.lower()
                    if conference in ["west", "western", "w"]:
                        show_east = False
                    elif conference in ["east", "eastern", "e"]:
                        show_west = False

                # Create main embed
                embed = discord.Embed(
                    title="🏆 MLS Standings",
                    description=f"**{standings_data.get('season', 'Current')} Season**",
                    color=discord.Color.blue(),
                )

                # Update title and description based on conference filter
                if not show_east:
                    embed.title = "🏆 MLS Western Conference Standings"
                    embed.description = f"**{standings_data.get('season', 'Current')} Season** • LA Galaxy's Conference ⭐"
                elif not show_west:
                    embed.title = "🏆 MLS Eastern Conference Standings"
                    embed.description = (
                        f"**{standings_data.get('season', 'Current')} Season**"
                    )

                # Log the data for debugging
                logger.info(f"Western Conference teams: {len(west_teams)}")
                logger.info(f"Eastern Conference teams: {len(east_teams)}")
                logger.info(f"Has standings data: {has_standings}")
                logger.info(f"Show west: {show_west}, Show east: {show_east}")
                logger.info(f"Raw standings data keys: {list(standings_data.keys())}")

                # Log first few teams for debugging
                if west_teams:
                    logger.info(f"First west team: {west_teams[0]}")
                if east_teams:
                    logger.info(f"First east team: {east_teams[0]}")

                # Debug: Show what we actually got
                if not west_teams and not east_teams:
                    debug_info = f"No team data found.\n"
                    debug_info += f"Available keys: {list(standings_data.keys())}\n"
                    debug_info += f"Season: {standings_data.get('season', 'Unknown')}\n"
                    debug_info += (
                        f"Total teams: {standings_data.get('total_teams', 'Unknown')}"
                    )

                    embed.add_field(
                        name="🔍 Debug Info",
                        value=debug_info,
                        inline=False,
                    )

                # Western Conference
                if show_west:
                    if west_teams:
                        west_text = self._format_conference_standings(
                            west_teams, has_standings, True
                        )
                        embed.add_field(
                            name=f"🌅 Western Conference ({len(west_teams)} teams)",
                            value=west_text or "No teams found",
                            inline=show_east,  # Side by side if showing both
                        )
                    elif (
                        not show_east
                    ):  # Only show this message if we're only showing west
                        embed.add_field(
                            name="🌅 Western Conference",
                            value="No Western Conference data available",
                            inline=False,
                        )

                # Eastern Conference
                if show_east:
                    if east_teams:
                        east_text = self._format_conference_standings(
                            east_teams, has_standings, False
                        )
                        embed.add_field(
                            name=f"🌇 Eastern Conference ({len(east_teams)} teams)",
                            value=east_text or "No teams found",
                            inline=show_west,  # Side by side if showing both
                        )
                    elif (
                        not show_west
                    ):  # Only show this message if we're only showing east
                        embed.add_field(
                            name="🌇 Eastern Conference",
                            value="No Eastern Conference data available",
                            inline=False,
                        )

                # Add spacing field if showing both conferences
                if show_west and show_east:
                    embed.add_field(name="\u200b", value="\u200b", inline=True)

                # Add informational note
                note = standings_data.get("note", "")
                if note:
                    embed.add_field(
                        name="ℹ️ Note",
                        value=note
                        + "\n\nFor live standings, visit [MLS.com](https://www.mlssoccer.com/standings/)",
                        inline=False,
                    )
                elif has_standings:
                    embed.add_field(
                        name="📊 Legend",
                        value="**pts** = Points • **GP** = Games Played • **GD** = Goal Difference",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="ℹ️ Note",
                        value="For live standings, visit [MLS.com](https://www.mlssoccer.com/standings/)",
                        inline=False,
                    )

                # Set footer
                embed.set_footer(
                    text="⭐ LA Galaxy is in the Western Conference • Data from TheSportsDB",
                    icon_url="https://logos-world.net/wp-content/uploads/2020/06/LA-Galaxy-Logo.png",
                )

                await ctx.send(embed=embed)
                logger.info("Successfully sent MLS standings embed")

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

    def _format_conference_standings(
        self, teams: list, has_standings: bool, is_western: bool
    ) -> str:
        """Format conference standings for display."""
        if not teams:
            return "No teams found"

        text = ""
        for i, team in enumerate(teams, 1):
            name = team["name"]

            # Highlight LA Galaxy if in western conference
            if is_western and "galaxy" in name.lower():
                name = f"**⭐ {name}**"

            if has_standings:
                # Format with actual standings data
                points = team["points"]
                played = team["played"]
                gd = team["goal_difference"]
                gd_str = f"+{gd}" if int(gd) > 0 else str(gd)

                text += f"`{i:2}.` {name}\n"
                text += f"     {points}pts • {played}GP • {gd_str}GD\n"
            else:
                # Format as simple team list
                text += f"`{i:2}.` {name}\n"

            # Discord field value limit is 1024 characters
            if len(text) > 900:
                text += f"... and {len(teams) - i} more teams"
                break

        return text

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
                player_data = await get_player_stats(player_name)

                # Check if there was an error
                if player_data.get("error", False):
                    embed = discord.Embed(
                        title="❌ Player Not Found",
                        description=player_data.get(
                            "message", "Unknown error occurred"
                        ),
                        color=discord.Color.orange(),
                    )
                    embed.add_field(
                        name="💡 Search Tips:",
                        value="• Try using just the last name\n• Check spelling\n• Try common nicknames",
                        inline=False,
                    )
                    await ctx.send(embed=embed)
                    return

                # Create rich embed with player information
                embed = discord.Embed(
                    title=f"⚽ {player_data['name']}",
                    color=discord.Color.blue()
                    if player_data["is_galaxy_player"]
                    else discord.Color.green(),
                )

                # Set player image if available
                if player_data["cutout_image"]:
                    embed.set_image(url=player_data["cutout_image"])
                elif player_data["thumb_image"]:
                    embed.set_thumbnail(url=player_data["thumb_image"])

                # Add basic info fields
                embed.add_field(
                    name="🏟️ Team",
                    value=player_data["team"],
                    inline=True,
                )
                embed.add_field(
                    name="🏃 Position",
                    value=player_data["position"],
                    inline=True,
                )
                embed.add_field(
                    name="🌍 Nationality",
                    value=player_data["nationality"],
                    inline=True,
                )

                # Add birth info if available
                if player_data["birth_date"] or player_data["age"]:
                    birth_info = []
                    if player_data["birth_date"]:
                        birth_info.append(player_data["birth_date"])
                    if player_data["age"]:
                        birth_info.append(f"({player_data['age']})")
                    if player_data["birth_location"]:
                        birth_info.append(f"in {player_data['birth_location']}")

                    embed.add_field(
                        name="🎂 Born",
                        value=" ".join(birth_info),
                        inline=True,
                    )

                # Add stats if available
                if player_data["goals"] != "N/A" or player_data["assists"] != "N/A":
                    stats_value = []
                    if player_data["goals"] != "N/A":
                        stats_value.append(f"⚽ Goals: {player_data['goals']}")
                    if player_data["assists"] != "N/A":
                        stats_value.append(f"🎯 Assists: {player_data['assists']}")

                    embed.add_field(
                        name="📊 Season Stats",
                        value="\n".join(stats_value)
                        if stats_value
                        else "No stats available",
                        inline=True,
                    )

                # Add status
                embed.add_field(
                    name="📋 Status",
                    value=player_data["status"],
                    inline=True,
                )

                # Add description if available
                if (
                    player_data["description"]
                    and player_data["description"] != "No description available"
                ):
                    embed.add_field(
                        name="📝 About",
                        value=player_data["description"],
                        inline=False,
                    )

                # Add footer with Galaxy indicator
                if player_data["is_galaxy_player"]:
                    embed.set_footer(
                        text="⭐ LA Galaxy Player",
                        icon_url="https://logos-world.net/wp-content/uploads/2020/06/LA-Galaxy-Logo.png",
                    )
                else:
                    embed.set_footer(text="ℹ️ Not currently with LA Galaxy")

                await ctx.send(embed=embed)
                logger.info(f"Successfully sent player stats embed for: {player_name}")

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
