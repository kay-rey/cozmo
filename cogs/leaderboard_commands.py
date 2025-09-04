"""
Leaderboard and ranking commands for the Enhanced Trivia System.
Provides Discord commands for viewing leaderboards and user rankings.
"""

import discord
from discord.ext import commands
import logging
from typing import Optional, List
from utils.leaderboard_manager import leaderboard_manager
from utils.models import LeaderboardEntry
from datetime import datetime

logger = logging.getLogger(__name__)


class LeaderboardCommands(commands.Cog):
    """Discord commands for leaderboard and ranking functionality."""

    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_manager = leaderboard_manager

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard_command(self, ctx, period: str = "all_time", page: int = 1):
        """
        Display the leaderboard for specified period.

        Usage: !leaderboard [period] [page]
        Periods: all_time, weekly, monthly
        """
        try:
            # Validate period
            valid_periods = ["all_time", "weekly", "monthly"]
            if period.lower() not in valid_periods:
                await ctx.send(
                    f"❌ Invalid period. Use one of: {', '.join(valid_periods)}"
                )
                return

            # Validate page
            if page < 1:
                page = 1

            # Calculate pagination
            entries_per_page = 10
            offset = (page - 1) * entries_per_page

            # Get leaderboard entries
            entries = await self.leaderboard_manager.get_leaderboard(
                period=period.lower(),
                limit=entries_per_page,
                offset=offset,
                user_context=ctx.author.id,
            )

            if not entries:
                await ctx.send("📊 No leaderboard data available for this period.")
                return

            # Create embed
            embed = await self._create_leaderboard_embed(
                entries, period.lower(), page, ctx.author.id
            )

            # Add pagination buttons if needed
            view = (
                LeaderboardView(
                    period.lower(), page, ctx.author.id, self.leaderboard_manager
                )
                if len(entries) == entries_per_page
                else None
            )

            await ctx.send(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await ctx.send("❌ An error occurred while fetching the leaderboard.")

    @commands.command(name="myrank", aliases=["rank", "position"])
    async def my_rank_command(self, ctx, period: str = "all_time"):
        """
        Show your current rank and nearby players.

        Usage: !myrank [period]
        Periods: all_time, weekly, monthly
        """
        try:
            # Validate period
            valid_periods = ["all_time", "weekly", "monthly"]
            if period.lower() not in valid_periods:
                await ctx.send(
                    f"❌ Invalid period. Use one of: {', '.join(valid_periods)}"
                )
                return

            user_id = ctx.author.id

            # Get user's rank
            rank_info = await self.leaderboard_manager.get_user_rank(
                user_id, period.lower()
            )

            if not rank_info:
                await ctx.send(
                    f"📊 You don't have a rank in the {period} leaderboard yet. "
                    "Play some trivia to get started!"
                )
                return

            user_rank, total_participants = rank_info

            # Get nearby ranks for context
            nearby_entries = await self.leaderboard_manager.get_nearby_ranks(
                user_id, period.lower(), context_size=3
            )

            # Get rank change if available
            rank_change = await self.leaderboard_manager.get_rank_change(
                user_id, period.lower()
            )

            # Create embed
            embed = await self._create_rank_embed(
                ctx.author,
                user_rank,
                total_participants,
                nearby_entries,
                period.lower(),
                rank_change,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in myrank command: {e}")
            await ctx.send("❌ An error occurred while fetching your rank.")

    async def _create_leaderboard_embed(
        self, entries: List[LeaderboardEntry], period: str, page: int, user_id: int
    ) -> discord.Embed:
        """Create a formatted leaderboard embed."""

        # Period display names
        period_names = {
            "all_time": "All Time",
            "weekly": "This Week",
            "monthly": "This Month",
        }

        period_display = period_names.get(period, period.title())

        embed = discord.Embed(
            title=f"🏆 {period_display} Leaderboard",
            color=discord.Color.gold(),
            timestamp=datetime.now(),
        )

        # Add leaderboard entries
        leaderboard_text = ""
        user_in_list = False

        for entry in entries:
            # Medal emojis for top 3
            if entry.rank == 1:
                rank_display = "🥇"
            elif entry.rank == 2:
                rank_display = "🥈"
            elif entry.rank == 3:
                rank_display = "🥉"
            else:
                rank_display = f"#{entry.rank}"

            # Highlight current user
            if entry.user_id == user_id:
                user_in_list = True
                rank_display = f"**{rank_display}**"
                username = f"**{entry.username}**"
            else:
                username = entry.username

            # Format entry
            leaderboard_text += (
                f"{rank_display} {username}\n"
                f"   📊 {entry.total_points:,} pts • "
                f"{entry.accuracy_percentage:.1f}% accuracy • "
                f"🔥 {entry.current_streak} streak\n\n"
            )

        embed.description = leaderboard_text

        # Add footer with page info
        embed.set_footer(
            text=f"Page {page} • Your rank is highlighted in bold"
            if user_in_list
            else f"Page {page} • Use !myrank to see your position"
        )

        return embed

    async def _create_rank_embed(
        self,
        user: discord.User,
        rank: int,
        total_participants: int,
        nearby_entries: List[LeaderboardEntry],
        period: str,
        rank_change: Optional[int],
    ) -> discord.Embed:
        """Create a formatted rank display embed."""

        period_names = {
            "all_time": "All Time",
            "weekly": "This Week",
            "monthly": "This Month",
        }

        period_display = period_names.get(period, period.title())

        # Determine rank emoji
        if rank == 1:
            rank_emoji = "🥇"
        elif rank == 2:
            rank_emoji = "🥈"
        elif rank == 3:
            rank_emoji = "🥉"
        else:
            rank_emoji = "📊"

        embed = discord.Embed(
            title=f"{rank_emoji} Your {period_display} Rank",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        # Main rank info
        percentile = (1 - (rank - 1) / total_participants) * 100

        rank_text = f"**Rank #{rank}** out of {total_participants:,} players\n"
        rank_text += f"Top {percentile:.1f}% of all players\n"

        # Add rank change if available
        if rank_change is not None:
            if rank_change > 0:
                rank_text += f"📈 Up {rank_change} positions from last week!\n"
            elif rank_change < 0:
                rank_text += f"📉 Down {abs(rank_change)} positions from last week\n"
            else:
                rank_text += f"➡️ No change from last week\n"

        embed.add_field(name="Your Position", value=rank_text, inline=False)

        # Add nearby players context
        if nearby_entries:
            nearby_text = ""
            for entry in nearby_entries:
                if entry.rank == rank:
                    # This is the user
                    nearby_text += f"**#{entry.rank} {user.display_name} (You)**\n"
                    nearby_text += f"   📊 {entry.total_points:,} pts • {entry.accuracy_percentage:.1f}% accuracy\n\n"
                else:
                    nearby_text += f"#{entry.rank} {entry.username}\n"
                    nearby_text += f"   📊 {entry.total_points:,} pts • {entry.accuracy_percentage:.1f}% accuracy\n\n"

            embed.add_field(name="Players Near You", value=nearby_text, inline=False)

        embed.set_footer(text=f"Use !leaderboard {period} to see the full rankings")

        return embed


class LeaderboardView(discord.ui.View):
    """Interactive view for leaderboard pagination."""

    def __init__(
        self, period: str, current_page: int, user_id: int, leaderboard_manager
    ):
        super().__init__(timeout=300)  # 5 minute timeout
        self.period = period
        self.current_page = current_page
        self.user_id = user_id
        self.leaderboard_manager = leaderboard_manager

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Go to previous page."""
        if self.current_page <= 1:
            await interaction.response.send_message(
                "You're already on the first page!", ephemeral=True
            )
            return

        self.current_page -= 1
        await self._update_leaderboard(interaction)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Go to next page."""
        self.current_page += 1
        await self._update_leaderboard(interaction)

    @discord.ui.button(label="🏠 My Rank", style=discord.ButtonStyle.primary)
    async def show_my_rank(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Show user's rank details."""
        try:
            rank_info = await self.leaderboard_manager.get_user_rank(
                interaction.user.id, self.period
            )

            if not rank_info:
                await interaction.response.send_message(
                    f"You don't have a rank in the {self.period} leaderboard yet!",
                    ephemeral=True,
                )
                return

            user_rank, total_participants = rank_info
            nearby_entries = await self.leaderboard_manager.get_nearby_ranks(
                interaction.user.id, self.period, context_size=2
            )

            # Create a quick rank summary
            percentile = (1 - (user_rank - 1) / total_participants) * 100
            rank_text = (
                f"Your {self.period.replace('_', ' ').title()} Rank: **#{user_rank}**\n"
                f"Out of {total_participants:,} players (Top {percentile:.1f}%)"
            )

            await interaction.response.send_message(rank_text, ephemeral=True)

        except Exception as e:
            logger.error(f"Error showing user rank: {e}")
            await interaction.response.send_message(
                "Error fetching your rank information.", ephemeral=True
            )

    async def _update_leaderboard(self, interaction: discord.Interaction):
        """Update the leaderboard display."""
        try:
            entries_per_page = 10
            offset = (self.current_page - 1) * entries_per_page

            entries = await self.leaderboard_manager.get_leaderboard(
                period=self.period,
                limit=entries_per_page,
                offset=offset,
                user_context=self.user_id,
            )

            if not entries:
                await interaction.response.send_message(
                    "No more entries to display.", ephemeral=True
                )
                self.current_page -= 1  # Revert page change
                return

            # Create new embed
            embed = await self._create_leaderboard_embed(
                entries, self.period, self.current_page, self.user_id
            )

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Error updating leaderboard: {e}")
            await interaction.response.send_message(
                "Error updating leaderboard.", ephemeral=True
            )

    async def _create_leaderboard_embed(
        self, entries: List[LeaderboardEntry], period: str, page: int, user_id: int
    ) -> discord.Embed:
        """Create a formatted leaderboard embed (duplicate of method above for view)."""

        period_names = {
            "all_time": "All Time",
            "weekly": "This Week",
            "monthly": "This Month",
        }

        period_display = period_names.get(period, period.title())

        embed = discord.Embed(
            title=f"🏆 {period_display} Leaderboard",
            color=discord.Color.gold(),
            timestamp=datetime.now(),
        )

        leaderboard_text = ""
        user_in_list = False

        for entry in entries:
            if entry.rank == 1:
                rank_display = "🥇"
            elif entry.rank == 2:
                rank_display = "🥈"
            elif entry.rank == 3:
                rank_display = "🥉"
            else:
                rank_display = f"#{entry.rank}"

            if entry.user_id == user_id:
                user_in_list = True
                rank_display = f"**{rank_display}**"
                username = f"**{entry.username}**"
            else:
                username = entry.username

            leaderboard_text += (
                f"{rank_display} {username}\n"
                f"   📊 {entry.total_points:,} pts • "
                f"{entry.accuracy_percentage:.1f}% accuracy • "
                f"🔥 {entry.current_streak} streak\n\n"
            )

        embed.description = leaderboard_text
        embed.set_footer(
            text=f"Page {page} • Your rank is highlighted in bold"
            if user_in_list
            else f"Page {page} • Use !myrank to see your position"
        )

        return embed

    async def on_timeout(self):
        """Handle view timeout."""
        # Disable all buttons when view times out
        for item in self.children:
            item.disabled = True


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(LeaderboardCommands(bot))
