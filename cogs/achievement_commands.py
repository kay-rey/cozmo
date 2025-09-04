"""
Achievement Commands Cog for the Enhanced Trivia System.
Provides Discord commands for viewing and managing achievements.
"""

import discord
from discord.ext import commands
import logging
from typing import Optional

from utils.achievement_system import achievement_system
from utils.achievement_notifications import notification_system
from utils.achievement_integration import achievement_integration

logger = logging.getLogger(__name__)


class AchievementCommandsCog(commands.Cog):
    """Discord commands for achievement functionality."""

    def __init__(self, bot):
        self.bot = bot
        self.achievement_system = achievement_system
        self.notification_system = notification_system
        self.achievement_integration = achievement_integration
        logger.info("AchievementCommandsCog initialized")

    @commands.command(name="achievements")
    async def achievements(
        self, ctx, user: Optional[discord.Member] = None, page: int = 1
    ):
        """
        Display a user's achievements.

        Usage:
        !achievements - Show your achievements
        !achievements @user - Show another user's achievements
        !achievements @user 2 - Show page 2 of another user's achievements
        """
        try:
            target_user = user or ctx.author

            if page < 1:
                page = 1

            # Get user achievements
            user_achievements = await self.achievement_system.get_user_achievements(
                target_user.id
            )

            # Create the embed
            per_page = 5
            embed = self.notification_system.create_achievements_list_embed(
                target_user, user_achievements, page, per_page
            )

            # Send the message
            message = await ctx.send(embed=embed)

            # Add navigation reactions if needed
            total_pages = (len(user_achievements) + per_page - 1) // per_page
            if total_pages > 1:
                await self.notification_system.add_navigation_reactions(
                    message, total_pages
                )

            logger.info(
                f"Displayed achievements for {target_user.display_name} (page {page})"
            )

        except Exception as e:
            logger.error(f"Error in achievements command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to retrieve achievements. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="achievementstats", aliases=["astats"])
    async def achievement_stats(self, ctx, user: Optional[discord.Member] = None):
        """
        Display comprehensive achievement statistics for a user.

        Usage:
        !achievementstats - Show your achievement statistics
        !astats @user - Show another user's achievement statistics
        """
        try:
            target_user = user or ctx.author

            # Get achievement statistics
            stats = await self.achievement_system.get_user_achievement_stats(
                target_user.id
            )

            if not stats:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to retrieve achievement statistics.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Create the embed
            embed = discord.Embed(
                title=f"🏆 {target_user.display_name}'s Achievement Statistics",
                color=0xFFD700,  # Gold
                timestamp=discord.utils.utcnow(),
            )

            # Overall stats
            embed.add_field(
                name="📊 Overall Progress",
                value=f"**{stats['unlocked_count']}** / **{stats['total_achievements']}** achievements unlocked\n"
                f"**{stats['completion_percentage']:.1f}%** completion rate\n"
                f"**{stats['total_bonus_points']}** bonus points earned",
                inline=False,
            )

            # Category breakdown
            if stats.get("category_stats"):
                category_text = ""
                for category, category_data in stats["category_stats"].items():
                    total = category_data["total"]
                    unlocked = category_data["unlocked"]
                    percentage = (unlocked / total) * 100 if total > 0 else 0
                    category_text += f"**{category.title()}**: {unlocked}/{total} ({percentage:.0f}%)\n"

                embed.add_field(
                    name="📂 By Category",
                    value=category_text or "No categories available",
                    inline=True,
                )

            # Recent achievements
            if stats.get("recent_achievements"):
                recent_text = ""
                for achievement_data in stats["recent_achievements"][:3]:  # Show last 3
                    if achievement_data.achievement:
                        achievement = achievement_data.achievement
                        unlock_date = achievement_data.unlocked_at.strftime("%m/%d")
                        recent_text += f"{achievement.emoji} **{achievement.name}** ({unlock_date})\n"

                if recent_text:
                    embed.add_field(
                        name="🆕 Recent Achievements", value=recent_text, inline=True
                    )

            embed.set_thumbnail(
                url=target_user.avatar.url
                if target_user.avatar
                else target_user.default_avatar.url
            )

            await ctx.send(embed=embed)
            logger.info(f"Displayed achievement stats for {target_user.display_name}")

        except Exception as e:
            logger.error(f"Error in achievement stats command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to retrieve achievement statistics. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="achievementprogress", aliases=["aprogress"])
    async def achievement_progress(self, ctx, *, achievement_name: str = None):
        """
        Show progress towards a specific achievement.

        Usage:
        !achievementprogress Hot Streak - Show progress towards Hot Streak achievement
        !aprogress galaxy expert - Show progress towards Galaxy Expert achievement
        """
        try:
            if not achievement_name:
                embed = discord.Embed(
                    title="❓ Achievement Progress",
                    description="Please specify an achievement name.\n\nExample: `!aprogress Hot Streak`",
                    color=discord.Color.blue(),
                )
                await ctx.send(embed=embed)
                return

            # Find achievement by name (case insensitive)
            achievement = None
            achievement_name_lower = achievement_name.lower()

            for ach in await self.achievement_system.get_all_achievements():
                if ach.name.lower() == achievement_name_lower:
                    achievement = ach
                    break

            if not achievement:
                embed = discord.Embed(
                    title="❌ Achievement Not Found",
                    description=f"Could not find an achievement named '{achievement_name}'.\n\n"
                    f"Use `!achievements` to see available achievements.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Get progress
            progress = await self.achievement_system.get_achievement_progress(
                ctx.author.id, achievement.id
            )

            if not progress:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to retrieve achievement progress.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Create progress embed
            embed = self.notification_system.create_achievement_progress_embed(
                ctx.author, achievement, progress.current_value, progress.required_value
            )

            await ctx.send(embed=embed)
            logger.info(
                f"Displayed progress for achievement {achievement.name} for {ctx.author.display_name}"
            )

        except Exception as e:
            logger.error(f"Error in achievement progress command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to retrieve achievement progress. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="achievementcategories", aliases=["acategories"])
    async def achievement_categories(self, ctx, user: Optional[discord.Member] = None):
        """
        Show achievement progress by category.

        Usage:
        !achievementcategories - Show your progress by category
        !acategories @user - Show another user's progress by category
        """
        try:
            target_user = user or ctx.author

            # Get achievement statistics
            stats = await self.achievement_system.get_user_achievement_stats(
                target_user.id
            )

            if not stats or not stats.get("category_stats"):
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to retrieve category statistics.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Create category progress embed
            embed = self.notification_system.create_achievement_categories_embed(
                target_user, stats["category_stats"]
            )

            await ctx.send(embed=embed)
            logger.info(
                f"Displayed achievement categories for {target_user.display_name}"
            )

        except Exception as e:
            logger.error(f"Error in achievement categories command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to retrieve achievement categories. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="allachievements", aliases=["listachievements"])
    async def all_achievements(self, ctx, category: str = None, page: int = 1):
        """
        List all available achievements, optionally filtered by category.

        Usage:
        !allachievements - Show all achievements
        !listachievements streaks - Show achievements in the 'streaks' category
        !allachievements points 2 - Show page 2 of points achievements
        """
        try:
            if page < 1:
                page = 1

            # Get achievements
            if category:
                achievements = (
                    await self.achievement_system.get_achievements_by_category(
                        category.lower()
                    )
                )
                if not achievements:
                    embed = discord.Embed(
                        title="❌ Category Not Found",
                        description=f"No achievements found in category '{category}'.\n\n"
                        f"Available categories: streaks, dedication, points, participation, accuracy, difficulty, challenges",
                        color=discord.Color.red(),
                    )
                    await ctx.send(embed=embed)
                    return
            else:
                achievements = await self.achievement_system.get_all_achievements()

            # Pagination
            per_page = 5
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_achievements = achievements[start_idx:end_idx]

            # Create embed
            title = f"🏆 All Achievements"
            if category:
                title += f" - {category.title()} Category"

            embed = discord.Embed(
                title=title,
                description=f"Showing {len(page_achievements)} of {len(achievements)} achievements",
                color=0xFFD700,
                timestamp=discord.utils.utcnow(),
            )

            for achievement in page_achievements:
                embed.add_field(
                    name=f"{achievement.emoji} {achievement.name}",
                    value=f"{achievement.description}\n💰 **{achievement.reward_points}** points | 📂 {achievement.category}",
                    inline=False,
                )

            # Add pagination info
            total_pages = (len(achievements) + per_page - 1) // per_page
            if total_pages > 1:
                embed.set_footer(
                    text=f"Page {page} of {total_pages} • Use reactions to navigate"
                )

            message = await ctx.send(embed=embed)

            # Add navigation reactions if needed
            if total_pages > 1:
                await self.notification_system.add_navigation_reactions(
                    message, total_pages
                )

            logger.info(
                f"Displayed all achievements (category: {category}, page: {page})"
            )

        except Exception as e:
            logger.error(f"Error in all achievements command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to retrieve achievements. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle navigation reactions for paginated achievement displays."""
        try:
            # Ignore bot reactions
            if user.bot:
                return

            # Check if this is a navigation reaction
            if str(reaction.emoji) not in ["⬅️", "➡️"]:
                return

            # Check if the message is from this bot and has achievement embeds
            if reaction.message.author != self.bot.user:
                return

            embed = reaction.message.embeds[0] if reaction.message.embeds else None
            if not embed or "Achievement" not in embed.title:
                return

            # Extract current page from footer
            footer_text = embed.footer.text if embed.footer else ""
            if "Page" not in footer_text:
                return

            try:
                # Parse current page and total pages
                page_info = footer_text.split("Page ")[1].split(" of ")
                current_page = int(page_info[0])
                total_pages = int(page_info[1].split(" •")[0])

                # Calculate new page
                if str(reaction.emoji) == "⬅️" and current_page > 1:
                    new_page = current_page - 1
                elif str(reaction.emoji) == "➡️" and current_page < total_pages:
                    new_page = current_page + 1
                else:
                    return  # No page change needed

                # Remove user's reaction
                try:
                    await reaction.remove(user)
                except discord.Forbidden:
                    pass  # Ignore if we can't remove reactions

                # This is a simplified navigation - in a full implementation,
                # we'd need to store the original command context and parameters
                # For now, we'll just indicate that navigation is available
                logger.info(
                    f"Navigation reaction detected: {reaction.emoji} by {user.display_name}"
                )

            except (ValueError, IndexError):
                # Failed to parse page info
                return

        except Exception as e:
            logger.error(f"Error handling achievement navigation reaction: {e}")

    @achievements.error
    async def achievements_error(self, ctx, error):
        """Error handler for achievements command."""
        logger.error(f"Error in achievements command: {error}")
        embed = discord.Embed(
            title="❌ Command Error",
            description="There was an error retrieving achievements. Please try again.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    @achievement_stats.error
    async def achievement_stats_error(self, ctx, error):
        """Error handler for achievement stats command."""
        logger.error(f"Error in achievement stats command: {error}")
        embed = discord.Embed(
            title="❌ Command Error",
            description="There was an error retrieving achievement statistics. Please try again.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AchievementCommandsCog(bot))
    logger.info("AchievementCommandsCog added to bot")
