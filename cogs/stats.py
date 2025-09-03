"""
Stats Cog for Cozmo Discord Bot.
Provides LA Galaxy team and player statistics commands.
"""

import logging
from discord.ext import commands
import discord

from api.sports_api import (
    get_standings_hybrid,
    get_team_roster_hybrid,
    get_player_stats,
    get_match_lineup,
    SportsAPIError,
)
from api.espn_api import ESPNAPIError

logger = logging.getLogger(__name__)


class StatsCog(commands.Cog):
    """Cog for statistics-related commands and information."""

    def __init__(self, bot: commands.Bot):
        """Initialize the Stats Cog."""
        self.bot = bot
        logger.info("StatsCog initialized")

    @commands.command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync_commands(self, ctx: commands.Context, guild_id: int = None):
        """Manually sync slash commands (owner only). Use guild_id for faster server-specific sync."""
        try:
            if guild_id:
                guild = discord.Object(id=guild_id)
                synced = await self.bot.tree.sync(guild=guild)
                await ctx.send(
                    f"✅ Synced {len(synced)} slash commands to guild {guild_id}"
                )
                logger.info(
                    f"Manually synced {len(synced)} slash commands to guild {guild_id}"
                )
            else:
                synced = await self.bot.tree.sync()
                await ctx.send(f"✅ Synced {len(synced)} slash commands globally")
                logger.info(f"Manually synced {len(synced)} slash commands globally")
        except Exception as e:
            await ctx.send(f"❌ Failed to sync commands: {e}")
            logger.error(f"Failed to manually sync commands: {e}")

    @commands.command(name="listcommands", hidden=True)
    @commands.is_owner()
    async def list_commands(self, ctx: commands.Context):
        """List all registered slash commands (owner only)."""
        try:
            commands_list = []
            for command in self.bot.tree.get_commands():
                commands_list.append(f"• /{command.name} - {command.description}")

            if commands_list:
                command_text = "\n".join(commands_list)
                await ctx.send(
                    f"**Registered Slash Commands ({len(commands_list)}):**\n```\n{command_text}\n```"
                )
            else:
                await ctx.send("❌ No slash commands are currently registered")

        except Exception as e:
            await ctx.send(f"❌ Failed to list commands: {e}")
            logger.error(f"Failed to list commands: {e}")

    @discord.app_commands.command(
        name="standings", description="Display MLS teams organized by conference"
    )
    @discord.app_commands.describe(
        conference="Filter by conference (west/east). Leave empty to show both conferences."
    )
    @discord.app_commands.choices(
        conference=[
            discord.app_commands.Choice(name="Western Conference", value="west"),
            discord.app_commands.Choice(name="Eastern Conference", value="east"),
        ]
    )
    async def standings(
        self,
        interaction: discord.Interaction,
        conference: discord.app_commands.Choice[str] = None,
    ):
        logger.info(
            f"Standings slash command invoked by {interaction.user} in {interaction.guild}"
        )

        # Defer the response since we might take a moment
        await interaction.response.defer()

        try:
            # Fetch standings data using hybrid approach with timeout protection
            import asyncio

            standings_data = await asyncio.wait_for(
                get_standings_hybrid(),
                timeout=25.0,  # 25 seconds max
            )

            # Get team data first
            west_teams = standings_data.get("western_conference", [])
            east_teams = standings_data.get("eastern_conference", [])
            has_standings = standings_data.get("has_standings", False)

            # Parse conference filter
            show_west = True
            show_east = True
            if conference:
                if conference.value == "west":
                    show_east = False
                elif conference.value == "east":
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
                elif not show_east:  # Only show this message if we're only showing west
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
                elif not show_west:  # Only show this message if we're only showing east
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

            await interaction.followup.send(embed=embed)
            logger.info("Successfully sent MLS standings embed")

        except asyncio.TimeoutError:
            logger.error("Timeout error in standings command")
            embed = discord.Embed(
                title="⏰ Request Timeout",
                description="The standings request took too long. Please try again in a moment.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)

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
            await interaction.followup.send(embed=embed)

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in standings command: {e}")
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An unexpected error occurred while fetching standings. The issue has been logged.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

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

    @discord.app_commands.command(
        name="playerstats", description="Display player statistics by name"
    )
    @discord.app_commands.describe(player_name="Name of the player to search for")
    async def player_stats(self, interaction: discord.Interaction, player_name: str):
        logger.info(
            f"Player stats slash command invoked by {interaction.user} in {interaction.guild}"
        )

        # Defer the response since we might take a moment
        await interaction.response.defer()

        # Input validation
        if len(player_name.strip()) < 2:
            embed = discord.Embed(
                title="❌ Invalid Player Name",
                description="Player name must be at least 2 characters long.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)
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
            await interaction.followup.send(embed=embed)
            logger.info(
                f"Player stats command called with too long name: {player_name}"
            )
            return

        try:
            # Fetch player stats from Sports API with timeout protection
            import asyncio

            player_data = await asyncio.wait_for(
                get_player_stats(player_name),
                timeout=25.0,  # 25 seconds max
            )

            # Check if there was an error
            if player_data.get("error", False):
                embed = discord.Embed(
                    title="❌ Player Not Found",
                    description=player_data.get("message", "Unknown error occurred"),
                    color=discord.Color.orange(),
                )
                embed.add_field(
                    name="💡 Search Tips:",
                    value="• Try using just the last name\n• Check spelling\n• Try common nicknames",
                    inline=False,
                )
                await interaction.followup.send(embed=embed)
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

            await interaction.followup.send(embed=embed)
            logger.info(f"Successfully sent player stats embed for: {player_name}")

        except asyncio.TimeoutError:
            logger.error(
                f"Timeout error in player_stats command for player: {player_name}"
            )
            embed = discord.Embed(
                title="⏰ Request Timeout",
                description="The player search took too long. Please try again in a moment.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)

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
            await interaction.followup.send(embed=embed)

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in player_stats command: {e}")
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An unexpected error occurred while fetching player statistics. The issue has been logged.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    @discord.app_commands.command(
        name="roster", description="Display team roster organized by position"
    )
    @discord.app_commands.describe(team_name="Name of the team (defaults to LA Galaxy)")
    async def roster(
        self, interaction: discord.Interaction, team_name: str = "LA Galaxy"
    ):
        logger.info(
            f"Roster slash command invoked by {interaction.user} for team: {team_name}"
        )

        await interaction.response.defer()

        try:
            # Add timeout protection
            import asyncio

            roster_data = await asyncio.wait_for(
                get_team_roster_hybrid(team_name),
                timeout=25.0,  # 25 seconds max
            )

            if roster_data.get("error", False):
                embed = discord.Embed(
                    title="❌ Team Not Found",
                    description=roster_data.get("message", "Unknown error occurred"),
                    color=discord.Color.orange(),
                )
                embed.add_field(
                    name="💡 Tips:",
                    value="• Try 'LA Galaxy' for the full team name\n• Check spelling\n• Use official team names",
                    inline=False,
                )
                await interaction.followup.send(embed=embed)
                return

            # Create roster embed
            embed = discord.Embed(
                title=f"👥 {roster_data['team_name']} Roster",
                description=f"**{roster_data['total_players']} Players**"
                + (
                    f" • Stadium: {roster_data['stadium']}"
                    if roster_data.get("stadium")
                    else ""
                ),
                color=discord.Color.blue()
                if "galaxy" in roster_data["team_name"].lower()
                else discord.Color.green(),
            )

            # Set team badge/logo if available
            if roster_data.get("team_badge"):
                embed.set_thumbnail(url=roster_data["team_badge"])
            elif roster_data.get("team_logo"):
                embed.set_thumbnail(url=roster_data["team_logo"])

            # Add data source info and disclaimer if needed
            data_source = roster_data.get("source", "TheSportsDB")
            total_players = roster_data.get("total_players", 0)

            if data_source == "ESPN":
                embed.add_field(
                    name="📊 Data Source",
                    value="ESPN (Enhanced roster data)",
                    inline=True,
                )
            elif total_players < 15:  # Most MLS teams have 25+ players
                embed.add_field(
                    name="⚠️ Limited Data Available",
                    value="Partial roster shown. Trying multiple sources for complete data.",
                    inline=False,
                )

            # Group players by position for better display
            positions = roster_data.get("positions", {})

            # Define position order and emojis
            position_config = [
                ("Goalkeeper", "🥅", 3),
                ("Defender", "🛡️", 8),
                ("Midfielder", "⚽", 8),
                ("Forward", "🎯", 6),
                ("Attacker", "🎯", 6),
                ("Winger", "🏃", 4),
            ]

            players_added = 0
            max_players = 25  # Discord embed limit consideration

            for pos_name, emoji, limit in position_config:
                # Find matching positions (case insensitive, partial match)
                matching_players = []
                for pos_key, players in positions.items():
                    if pos_name.lower() in pos_key.lower():
                        matching_players.extend(players[:limit])

                if matching_players and players_added < max_players:
                    player_text = ""
                    for i, player in enumerate(matching_players[:limit]):
                        if players_added >= max_players:
                            break
                        player_text += (
                            f"**{player['name']}** ({player['nationality']})\n"
                        )
                        players_added += 1

                    if player_text:
                        embed.add_field(
                            name=f"{emoji} {pos_name}s",
                            value=player_text or "None listed",
                            inline=True,
                        )

            # Add any remaining positions not covered above
            remaining_positions = {
                k: v
                for k, v in positions.items()
                if not any(pos.lower() in k.lower() for pos, _, _ in position_config)
            }

            for pos_name, players in remaining_positions.items():
                if players_added >= max_players:
                    break
                if players:
                    player_text = ""
                    for player in players[:3]:  # Limit others to 3
                        if players_added >= max_players:
                            break
                        player_text += (
                            f"**{player['name']}** ({player['nationality']})\n"
                        )
                        players_added += 1

                    if player_text:
                        embed.add_field(
                            name=f"👤 {pos_name}",
                            value=player_text,
                            inline=True,
                        )

            # Set footer
            if "galaxy" in roster_data["team_name"].lower():
                embed.set_footer(
                    text="⭐ LA Galaxy Roster • Data from TheSportsDB",
                    icon_url="https://logos-world.net/wp-content/uploads/2020/06/LA-Galaxy-Logo.png",
                )
            else:
                embed.set_footer(text="Data from TheSportsDB")

            await interaction.followup.send(embed=embed)
            logger.info(f"Successfully sent roster embed for: {team_name}")

        except asyncio.TimeoutError:
            logger.error(f"Timeout error in roster command for team: {team_name}")
            embed = discord.Embed(
                title="⏰ Request Timeout",
                description="The roster request took too long. Please try again in a moment.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)

        except SportsAPIError as e:
            logger.error(f"Sports API error in roster command: {e}")
            embed = discord.Embed(
                title="❌ Unable to Fetch Roster",
                description="Sorry, I'm having trouble getting the team roster right now. Please try again in a few minutes.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Unexpected error in roster command: {e}")
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An unexpected error occurred while fetching the roster. The issue has been logged.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    @discord.app_commands.command(
        name="lineup", description="Display match lineup for a team"
    )
    @discord.app_commands.describe(
        match_id="Match ID (optional - uses next LA Galaxy match if not provided)"
    )
    async def lineup(self, interaction: discord.Interaction, match_id: str = None):
        logger.info(
            f"Lineup slash command invoked by {interaction.user} with match_id: {match_id}"
        )

        await interaction.response.defer()

        try:
            # Fetch lineup data with timeout protection
            import asyncio

            lineup_data = await asyncio.wait_for(
                get_match_lineup(match_id),
                timeout=25.0,  # 25 seconds max
            )

            if lineup_data.get("error", False):
                embed = discord.Embed(
                    title="❌ Lineup Not Available",
                    description=lineup_data.get("message", "Unknown error occurred"),
                    color=discord.Color.orange(),
                )

                embed.add_field(
                    name="💡 Note",
                    value="Lineup data is typically released closer to match time. Try the roster command to see all team players.",
                    inline=False,
                )
                await interaction.followup.send(embed=embed)
                return

            # Create lineup embed
            embed = discord.Embed(
                title=f"📋 Match Lineup",
                description=f"**{lineup_data['home_team']}** vs **{lineup_data['away_team']}**\n"
                f"📅 {lineup_data['match_date']} • 🕐 {lineup_data['match_time']}",
                color=discord.Color.blue(),
            )

            # Add home team lineup
            home_lineup = lineup_data.get("home_lineup", [])
            if home_lineup:
                home_text = ""
                for i, player in enumerate(home_lineup[:11], 1):  # Starting XI
                    player_name = player.get("strPlayer", "Unknown")
                    position = player.get("strPosition", "")
                    home_text += (
                        f"{i}. **{player_name}**"
                        + (f" ({position})" if position else "")
                        + "\n"
                    )

                embed.add_field(
                    name=f"🏠 {lineup_data['home_team']} Starting XI",
                    value=home_text or "Lineup not available",
                    inline=True,
                )

            # Add away team lineup
            away_lineup = lineup_data.get("away_lineup", [])
            if away_lineup:
                away_text = ""
                for i, player in enumerate(away_lineup[:11], 1):  # Starting XI
                    player_name = player.get("strPlayer", "Unknown")
                    position = player.get("strPosition", "")
                    away_text += (
                        f"{i}. **{player_name}**"
                        + (f" ({position})" if position else "")
                        + "\n"
                    )

                embed.add_field(
                    name=f"✈️ {lineup_data['away_team']} Starting XI",
                    value=away_text or "Lineup not available",
                    inline=True,
                )

            # Add venue info
            if lineup_data.get("venue"):
                embed.add_field(
                    name="🏟️ Venue",
                    value=lineup_data["venue"],
                    inline=False,
                )

            # Set footer
            embed.set_footer(text="Data from TheSportsDB")

            await interaction.followup.send(embed=embed)
            logger.info(
                f"Successfully sent lineup embed for match: {match_id or 'next LA Galaxy match'}"
            )

        except asyncio.TimeoutError:
            logger.error(
                f"Timeout error in lineup command for match: {match_id or 'next LA Galaxy match'}"
            )
            embed = discord.Embed(
                title="⏰ Request Timeout",
                description="The lineup request took too long. Please try again in a moment.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)

        except SportsAPIError as e:
            logger.error(f"Sports API error in lineup command: {e}")
            embed = discord.Embed(
                title="❌ Unable to Fetch Lineup",
                description="Sorry, I'm having trouble getting the match lineup right now. Please try again in a few minutes.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Unexpected error in lineup command: {e}")
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An unexpected error occurred while fetching the lineup. The issue has been logged.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    cog = StatsCog(bot)
    await bot.add_cog(cog)

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"StatsCog added to bot and synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")
        logger.info("StatsCog added to bot (slash commands not synced)")
