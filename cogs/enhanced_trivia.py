"""
Enhanced Trivia Cog for the Enhanced Trivia System.
Provides trivia commands with challenge system integration.
"""

import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime, date
from typing import Optional, Dict, Any
from utils.game_manager import GameManager
from utils.user_manager import user_manager
from utils.question_engine import QuestionEngine
from utils.challenge_system import ChallengeSystem
from utils.database import db_manager

logger = logging.getLogger(__name__)


class EnhancedTriviaCog(commands.Cog):
    """Enhanced trivia cog with challenge system support."""

    def __init__(self, bot):
        self.bot = bot
        self.question_engine = None
        self.game_manager = None
        self.challenge_system = None
        logger.info("EnhancedTriviaCog initialized")

    async def cog_load(self):
        """Initialize components when cog is loaded."""
        try:
            # Initialize database
            await db_manager.initialize_database()

            # Initialize question engine
            self.question_engine = QuestionEngine()

            # Initialize game manager
            self.game_manager = GameManager(self.question_engine, self.bot)

            # Initialize challenge system
            self.challenge_system = ChallengeSystem(self.question_engine, user_manager)

            logger.info("Enhanced trivia system components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced trivia components: {e}")
            raise

    async def cog_unload(self):
        """Clean up when cog is unloaded."""
        try:
            if self.game_manager:
                await self.game_manager.shutdown()
            if self.challenge_system:
                await self.challenge_system.shutdown()
            logger.info("Enhanced trivia system components shut down")
        except Exception as e:
            logger.error(f"Error during enhanced trivia shutdown: {e}")

    @commands.command(name="trivia")
    async def trivia(self, ctx, difficulty: str = None):
        """Start a trivia game with optional difficulty selection."""
        try:
            user_id = ctx.author.id
            channel_id = ctx.channel.id

            # Validate difficulty if provided
            valid_difficulties = ["easy", "medium", "hard"]
            if difficulty and difficulty.lower() not in valid_difficulties:
                embed = discord.Embed(
                    title="❌ Invalid Difficulty",
                    description=f"Please choose from: {', '.join(valid_difficulties)}",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Normalize difficulty
            if difficulty:
                difficulty = difficulty.lower()

            # Check if there's already an active game in this channel
            if await self.game_manager.get_active_game(channel_id):
                embed = discord.Embed(
                    title="🎮 Game Already Active",
                    description="There's already a trivia game active in this channel! Finish it first.",
                    color=discord.Color.orange(),
                )
                await ctx.send(embed=embed)
                return

            # Get user preferences if no difficulty specified
            if not difficulty:
                user_profile = await user_manager.get_or_create_user(user_id)
                if user_profile.preferred_difficulty:
                    difficulty = user_profile.preferred_difficulty

            # Start the game
            game_session = await self.game_manager.start_game(
                channel_id=channel_id,
                user_id=user_id,
                difficulty=difficulty,
                timeout_duration=30,
                timeout_callback=lambda: self._handle_trivia_timeout(ctx),
                countdown_callback=lambda remaining: self._handle_countdown(
                    ctx, remaining
                ),
            )

            if not game_session:
                embed = discord.Embed(
                    title="❌ Failed to Start Game",
                    description="Unable to start trivia game. Please try again.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Create and send question embed
            embed = await self._create_trivia_embed(game_session.question)
            message = await ctx.send(embed=embed)

            # Add reactions for multiple choice questions
            if game_session.question.question_type == "multiple_choice":
                reactions = ["🇦", "🇧", "🇨", "🇩"]
                for i, reaction in enumerate(
                    reactions[: len(game_session.question.options)]
                ):
                    await message.add_reaction(reaction)

            logger.info(
                f"Started trivia game for user {user_id} in channel {channel_id}"
            )

        except Exception as e:
            logger.error(f"Error in trivia command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while starting the trivia game. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="triviastats", aliases=["stats"])
    async def trivia_stats(self, ctx, user: discord.Member = None):
        """Show comprehensive user trivia statistics."""
        try:
            target_user = user or ctx.author
            user_id = target_user.id

            # Get user statistics
            user_stats = await user_manager.get_user_stats(user_id)
            user_profile = user_stats.user_profile

            # Create stats embed
            embed = discord.Embed(
                title=f"📊 Trivia Statistics",
                description=f"Stats for **{target_user.display_name}**",
                color=0x00BFFF,
            )

            # Basic stats
            embed.add_field(
                name="🎯 Performance",
                value=f"**Points:** {user_profile.total_points:,}\n"
                f"**Accuracy:** {user_profile.accuracy_percentage:.1f}%\n"
                f"**Questions:** {user_profile.questions_answered:,}",
                inline=True,
            )

            # Streaks
            embed.add_field(
                name="🔥 Streaks",
                value=f"**Current:** {user_profile.current_streak}\n"
                f"**Best:** {user_profile.best_streak}\n"
                f"**Rank:** #{user_stats.current_rank or 'Unranked'}",
                inline=True,
            )

            # Achievements
            embed.add_field(
                name="🏆 Achievements",
                value=f"**Unlocked:** {user_stats.achievements_count}\n"
                f"**Last Played:** {user_profile.last_played.strftime('%m/%d/%Y') if user_profile.last_played else 'Never'}",
                inline=True,
            )

            # Difficulty breakdown
            if user_stats.difficulty_breakdown:
                difficulty_text = ""
                for difficulty, stats in user_stats.difficulty_breakdown.items():
                    accuracy = stats.get("accuracy", 0)
                    difficulty_text += f"**{difficulty.title()}:** {accuracy:.1f}% ({stats.get('correct', 0)}/{stats.get('total', 0)})\n"

                embed.add_field(
                    name="📈 By Difficulty",
                    value=difficulty_text or "No data yet",
                    inline=False,
                )

            # Recent performance
            if user_stats.recent_performance:
                recent_icons = [
                    "✅" if correct else "❌"
                    for correct in user_stats.recent_performance[:10]
                ]
                embed.add_field(
                    name="📋 Recent Performance (Last 10)",
                    value="".join(recent_icons) or "No recent games",
                    inline=False,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in triviastats command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while getting trivia statistics. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    # Note: achievements command is handled by achievement_commands.py cog

    @commands.command(name="triviareport", aliases=["report"])
    async def trivia_report(self, ctx):
        """Show performance breakdown by category and difficulty."""
        try:
            user_id = ctx.author.id

            # Get comprehensive user statistics
            user_stats = await user_manager.get_user_stats(user_id)
            user_preferences = await user_manager.get_user_preferences(user_id)

            embed = discord.Embed(
                title="📈 Trivia Performance Report",
                description=f"Detailed analysis for **{ctx.author.display_name}**",
                color=0x9932CC,
            )

            # Overall performance
            user_profile = user_stats.user_profile
            embed.add_field(
                name="📊 Overall Performance",
                value=f"**Total Points:** {user_profile.total_points:,}\n"
                f"**Questions Answered:** {user_profile.questions_answered:,}\n"
                f"**Accuracy:** {user_profile.accuracy_percentage:.1f}%\n"
                f"**Current Rank:** #{user_stats.current_rank or 'Unranked'}",
                inline=True,
            )

            # Difficulty breakdown
            if user_stats.difficulty_breakdown:
                difficulty_text = ""
                for difficulty in ["easy", "medium", "hard"]:
                    if difficulty in user_stats.difficulty_breakdown:
                        stats = user_stats.difficulty_breakdown[difficulty]
                        accuracy = stats.get("accuracy", 0)
                        points = stats.get("points", 0)
                        difficulty_text += f"**{difficulty.title()}:** {accuracy:.1f}% - {points} pts\n"
                    else:
                        difficulty_text += f"**{difficulty.title()}:** No data\n"

                embed.add_field(
                    name="🎯 By Difficulty",
                    value=difficulty_text,
                    inline=True,
                )

            # Category performance
            if user_stats.points_per_category:
                category_text = ""
                sorted_categories = sorted(
                    user_stats.points_per_category.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
                for category, points in sorted_categories[:5]:
                    category_text += f"**{category.title()}:** {points} pts\n"

                embed.add_field(
                    name="📚 Top Categories",
                    value=category_text or "No category data",
                    inline=True,
                )

            # Personalized insights
            insights = []

            # Preferred difficulty
            if user_preferences.get("preferred_difficulty"):
                insights.append(
                    f"🎯 Preferred difficulty: **{user_preferences['preferred_difficulty'].title()}**"
                )

            # Weak areas
            if user_preferences.get("weak_areas"):
                weak_areas = ", ".join(user_preferences["weak_areas"][:3])
                insights.append(f"📖 Areas to improve: {weak_areas}")

            # Next goals
            if user_preferences.get("next_goals"):
                next_goal = user_preferences["next_goals"][0]
                insights.append(f"🎯 Next goal: {next_goal}")

            if insights:
                embed.add_field(
                    name="💡 Insights & Recommendations",
                    value="\n".join(insights),
                    inline=False,
                )

            # Recent performance trend
            if user_stats.recent_performance:
                recent_correct = sum(user_stats.recent_performance)
                recent_total = len(user_stats.recent_performance)
                recent_accuracy = (recent_correct / recent_total) * 100

                trend_emoji = (
                    "📈"
                    if recent_accuracy > user_profile.accuracy_percentage
                    else "📉"
                    if recent_accuracy < user_profile.accuracy_percentage
                    else "➡️"
                )

                embed.add_field(
                    name="📋 Recent Trend",
                    value=f"{trend_emoji} Last {recent_total} games: {recent_accuracy:.1f}% accuracy",
                    inline=False,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in triviareport command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while generating the trivia report. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="dailychallenge", aliases=["daily"])
    async def daily_challenge(self, ctx):
        """Start a daily challenge with double point rewards."""
        try:
            user_id = ctx.author.id
            channel_id = ctx.channel.id

            # Check if user can attempt daily challenge
            status = await self.challenge_system.get_challenge_status(user_id)

            if not status["daily"]["available"]:
                if status["daily"]["completed_today"]:
                    embed = discord.Embed(
                        title="✅ Daily Challenge Complete",
                        description="You've already completed today's daily challenge! Come back tomorrow for a new one.",
                        color=discord.Color.green(),
                    )
                    embed.add_field(
                        name="💡 Tip",
                        value="Try the weekly challenge or regular trivia while you wait!",
                        inline=False,
                    )
                elif status["daily"]["active"]:
                    embed = discord.Embed(
                        title="🎮 Daily Challenge Active",
                        description="You already have an active daily challenge! Complete it first.",
                        color=discord.Color.orange(),
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Daily Challenge Unavailable",
                        description="Daily challenge is not available right now. Please try again later.",
                        color=discord.Color.red(),
                    )
                await ctx.send(embed=embed)
                return

            # Check if there's already an active game in this channel
            if await self.game_manager.get_active_game(channel_id):
                embed = discord.Embed(
                    title="🎮 Game Already Active",
                    description="There's already a trivia game active in this channel! Finish it first.",
                    color=discord.Color.orange(),
                )
                await ctx.send(embed=embed)
                return

            # Get daily challenge question
            question = await self.challenge_system.get_daily_challenge(user_id)
            if not question:
                embed = discord.Embed(
                    title="❌ Challenge Unavailable",
                    description="Unable to generate daily challenge question. Please try again later.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Start the challenge game
            game_session = await self.game_manager.start_game(
                channel_id=channel_id,
                user_id=user_id,
                difficulty=question.difficulty,
                is_challenge=True,
                timeout_duration=45,  # Longer timeout for challenges
                timeout_callback=lambda: self._handle_challenge_timeout(
                    ctx, user_id, "daily"
                ),
                countdown_callback=lambda remaining: self._handle_countdown(
                    ctx, remaining
                ),
            )

            if not game_session:
                embed = discord.Embed(
                    title="❌ Failed to Start Challenge",
                    description="Unable to start daily challenge. Please try again.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Create and send challenge embed
            embed = await self._create_challenge_embed(question, "daily")
            message = await ctx.send(embed=embed)

            # Add reactions for multiple choice questions
            if question.question_type == "multiple_choice":
                reactions = ["🇦", "🇧", "🇨", "🇩"]
                for i, reaction in enumerate(reactions[: len(question.options)]):
                    await message.add_reaction(reaction)

            logger.info(
                f"Started daily challenge for user {user_id} in channel {channel_id}"
            )

        except Exception as e:
            logger.error(f"Error in daily challenge command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while starting the daily challenge. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="weeklychallenge", aliases=["weekly"])
    async def weekly_challenge(self, ctx):
        """Start a weekly challenge with 5 questions and triple point rewards."""
        try:
            user_id = ctx.author.id
            channel_id = ctx.channel.id

            # Check if user can attempt weekly challenge
            status = await self.challenge_system.get_challenge_status(user_id)

            if not status["weekly"]["available"]:
                if status["weekly"]["completed_this_week"]:
                    embed = discord.Embed(
                        title="✅ Weekly Challenge Complete",
                        description="You've already completed this week's challenge! New challenges are posted every Monday.",
                        color=discord.Color.green(),
                    )
                elif status["weekly"]["active"]:
                    progress = status["weekly"]["progress"]
                    embed = discord.Embed(
                        title="🎮 Weekly Challenge In Progress",
                        description=f"You're currently on question {progress['current_question']}/5 of this week's challenge!",
                        color=discord.Color.orange(),
                    )
                    embed.add_field(
                        name="Progress",
                        value=f"✅ Correct: {progress['correct_answers']}\n💰 Points: {progress['points_so_far']}",
                        inline=True,
                    )
                    embed.add_field(
                        name="Next Step",
                        value="Continue your challenge in any channel!",
                        inline=True,
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Weekly Challenge Unavailable",
                        description="Weekly challenge is not available right now. Please try again later.",
                        color=discord.Color.red(),
                    )
                await ctx.send(embed=embed)
                return

            # Check if there's already an active game in this channel
            if await self.game_manager.get_active_game(channel_id):
                embed = discord.Embed(
                    title="🎮 Game Already Active",
                    description="There's already a trivia game active in this channel! Finish it first.",
                    color=discord.Color.orange(),
                )
                await ctx.send(embed=embed)
                return

            # Get weekly challenge questions (first time) or current question (continuing)
            current_question = await self.challenge_system.get_current_weekly_question(
                user_id
            )

            if not current_question:
                # Start new weekly challenge
                questions = await self.challenge_system.get_weekly_challenge(user_id)
                if not questions:
                    embed = discord.Embed(
                        title="❌ Challenge Unavailable",
                        description="Unable to generate weekly challenge questions. Please try again later.",
                        color=discord.Color.red(),
                    )
                    await ctx.send(embed=embed)
                    return
                current_question = questions[0]

            # Start the challenge game
            game_session = await self.game_manager.start_game(
                channel_id=channel_id,
                user_id=user_id,
                difficulty=current_question.difficulty,
                is_challenge=True,
                timeout_duration=60,  # Longer timeout for weekly challenges
                timeout_callback=lambda: self._handle_challenge_timeout(
                    ctx, user_id, "weekly"
                ),
                countdown_callback=lambda remaining: self._handle_countdown(
                    ctx, remaining
                ),
            )

            if not game_session:
                embed = discord.Embed(
                    title="❌ Failed to Start Challenge",
                    description="Unable to start weekly challenge. Please try again.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Create and send challenge embed
            embed = await self._create_challenge_embed(current_question, "weekly")
            message = await ctx.send(embed=embed)

            # Add reactions for multiple choice questions
            if current_question.question_type == "multiple_choice":
                reactions = ["🇦", "🇧", "🇨", "🇩"]
                for i, reaction in enumerate(
                    reactions[: len(current_question.options)]
                ):
                    await message.add_reaction(reaction)

            logger.info(
                f"Started weekly challenge for user {user_id} in channel {channel_id}"
            )

        except Exception as e:
            logger.error(f"Error in weekly challenge command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while starting the weekly challenge. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    async def _create_challenge_embed(
        self, question, challenge_type: str
    ) -> discord.Embed:
        """Create an embed for a challenge question."""
        # Determine colors and titles
        if challenge_type == "daily":
            color = 0xFFD700  # Gold
            title = "🌟 Daily Challenge"
            reward_text = "Double Points!"
        else:  # weekly
            color = 0x9932CC  # Purple
            title = "👑 Weekly Challenge"
            reward_text = "Triple Points!"

        embed = discord.Embed(
            title=title,
            description=question.question_text,
            color=color,
        )

        # Add difficulty and category info
        embed.add_field(
            name="📊 Info",
            value=f"**Difficulty:** {question.difficulty.title()}\n**Category:** {question.category.title()}",
            inline=True,
        )

        embed.add_field(
            name="🎁 Reward",
            value=reward_text,
            inline=True,
        )

        # Add options for multiple choice
        if question.question_type == "multiple_choice" and question.options:
            options_text = ""
            reactions = ["🇦", "🇧", "🇨", "🇩"]
            for i, option in enumerate(question.options):
                options_text += f"{reactions[i]} {option}\n"

            embed.add_field(
                name="Options",
                value=options_text,
                inline=False,
            )
            embed.set_footer(text="React with 🇦, 🇧, 🇨, or 🇩 to answer!")
        elif question.question_type == "true_false":
            embed.set_footer(text="Type 'true' or 'false' to answer!")
        else:
            embed.set_footer(text="Type your answer!")

        return embed

    async def _handle_challenge_timeout(self, ctx, user_id: int, challenge_type: str):
        """Handle challenge timeout."""
        try:
            # Cancel the active challenge
            await self.challenge_system.cancel_active_challenge(user_id, challenge_type)

            embed = discord.Embed(
                title="⏰ Challenge Timed Out",
                description=f"Your {challenge_type} challenge has timed out. You can try again tomorrow!"
                if challenge_type == "daily"
                else "Your weekly challenge question has timed out. You can continue later!",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error handling challenge timeout: {e}")

    async def _handle_trivia_timeout(self, ctx):
        """Handle trivia game timeout."""
        try:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description="The trivia question has timed out. Try again with `!trivia`!",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error handling trivia timeout: {e}")

    async def _create_trivia_embed(self, question) -> discord.Embed:
        """Create an embed for a trivia question."""
        embed = discord.Embed(
            title="🏆 LA Galaxy Trivia",
            description=question.question_text,
            color=0x00274C,  # LA Galaxy navy blue
        )

        # Add difficulty and category info
        embed.add_field(
            name="📊 Info",
            value=f"**Difficulty:** {question.difficulty.title()}\n"
            f"**Category:** {question.category.title()}\n"
            f"**Points:** {question.point_value}",
            inline=True,
        )

        # Add options for multiple choice
        if question.question_type == "multiple_choice" and question.options:
            options_text = ""
            reactions = ["🇦", "🇧", "🇨", "🇩"]
            for i, option in enumerate(question.options):
                options_text += f"{reactions[i]} {option}\n"

            embed.add_field(
                name="Options",
                value=options_text,
                inline=False,
            )
            embed.set_footer(text="React with 🇦, 🇧, 🇨, or 🇩 to answer!")
        elif question.question_type == "true_false":
            embed.set_footer(text="Type 'true' or 'false' to answer!")
        else:
            embed.set_footer(text="Type your answer!")

        return embed

    async def _handle_countdown(self, ctx, remaining: int):
        """Handle countdown notifications."""
        try:
            if remaining == 20:
                await ctx.send("⏰ 20 seconds remaining!")
            elif remaining == 10:
                await ctx.send("⏰ 10 seconds remaining!")
        except Exception as e:
            logger.error(f"Error in countdown handler: {e}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle trivia answer reactions for both regular games and challenges."""
        try:
            # Ignore bot reactions
            if user.bot:
                return

            channel_id = reaction.message.channel.id
            user_id = user.id

            # Check if there's an active game in this channel
            game_session = await self.game_manager.get_active_game(channel_id)
            if not game_session:
                return

            # Process the reaction answer
            result = await self.game_manager.process_reaction_answer(
                channel_id, user_id, reaction, user
            )

            if result:
                if game_session.is_challenge:
                    await self._handle_challenge_result(
                        reaction.message.channel, user, result, game_session
                    )
                else:
                    await self._handle_trivia_result(
                        reaction.message.channel, user, result, game_session
                    )

        except Exception as e:
            logger.error(f"Error handling reaction: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle text-based answers for both regular games and challenges."""
        try:
            # Ignore bot messages
            if message.author.bot:
                return

            # Skip if it's a command
            if message.content.startswith("!"):
                return

            channel_id = message.channel.id
            user_id = message.author.id

            # Check if there's an active game in this channel
            game_session = await self.game_manager.get_active_game(channel_id)
            if not game_session:
                return

            # Process the text answer
            result = await self.game_manager.process_text_answer(
                channel_id, user_id, message
            )

            if result:
                if game_session.is_challenge:
                    await self._handle_challenge_result(
                        message.channel, message.author, result, game_session
                    )
                else:
                    await self._handle_trivia_result(
                        message.channel, message.author, result, game_session
                    )

        except Exception as e:
            logger.error(f"Error handling text answer: {e}", exc_info=True)

    @commands.command(name="challengeprogress", aliases=["progress"])
    async def challenge_progress(self, ctx):
        """Display current challenge progress and status."""
        try:
            user_id = ctx.author.id

            # Get challenge status
            status = await self.challenge_system.get_challenge_status(user_id)

            embed = discord.Embed(
                title="📊 Challenge Progress",
                description=f"Challenge status for **{ctx.author.display_name}**",
                color=0x00BFFF,  # Deep sky blue
            )

            # Daily challenge status
            daily_status = (
                "✅ Completed"
                if status["daily"]["completed_today"]
                else "🎯 Available"
                if status["daily"]["available"]
                else "🎮 Active"
            )
            embed.add_field(
                name="🌟 Daily Challenge",
                value=f"Status: {daily_status}\nReward: Double points",
                inline=True,
            )

            # Weekly challenge status
            if status["weekly"]["active"] and status["weekly"]["progress"]:
                progress = status["weekly"]["progress"]
                weekly_status = f"🎮 In Progress ({progress['current_question']}/5)"
                weekly_details = f"Correct: {progress['correct_answers']}\nPoints: {progress['points_so_far']}"

                # Get detailed progress
                detailed_progress = (
                    await self.challenge_system.get_weekly_challenge_progress(user_id)
                )
                if detailed_progress:
                    accuracy = detailed_progress["accuracy"]
                    potential_badge = detailed_progress.get("potential_badge", "None")
                    weekly_details += f"\nAccuracy: {accuracy:.1f}%\nPotential Badge: {potential_badge.replace('_', ' ').title() if potential_badge else 'None'}"

            elif status["weekly"]["completed_this_week"]:
                weekly_status = "✅ Completed"
                weekly_details = "Come back next Monday!"
            else:
                weekly_status = "🎯 Available"
                weekly_details = "5 questions, triple points!"

            embed.add_field(
                name="👑 Weekly Challenge",
                value=f"Status: {weekly_status}\n{weekly_details}",
                inline=True,
            )

            # Add tips
            tips = []
            if status["daily"]["available"]:
                tips.append("Use `!dailychallenge` for double points!")
            if status["weekly"]["available"]:
                tips.append("Use `!weeklychallenge` for triple points!")
            if not tips:
                tips.append("Great job completing your challenges!")

            embed.add_field(
                name="💡 Tips",
                value="\n".join(tips),
                inline=False,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in challenge progress command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while getting challenge progress. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    # @commands.command(name="leaderboard", aliases=["lb", "top"])
    # Disabled - handled by leaderboard_commands.py cog
    async def leaderboard_disabled(self, ctx, period: str = "all"):
        """Display the trivia leaderboard."""
        try:
            from utils.leaderboard_manager import leaderboard_manager

            # Validate period
            valid_periods = ["all", "weekly", "monthly"]
            if period.lower() not in valid_periods:
                embed = discord.Embed(
                    title="❌ Invalid Period",
                    description=f"Please choose from: {', '.join(valid_periods)}",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            period = "all_time" if period.lower() == "all" else period.lower()

            # Get leaderboard entries
            entries = await leaderboard_manager.get_leaderboard(
                period=period, limit=10, user_context=ctx.author.id
            )

            if not entries:
                embed = discord.Embed(
                    title="📊 Leaderboard",
                    description="No leaderboard data available yet. Play some trivia to get started!",
                    color=0x00BFFF,
                )
                await ctx.send(embed=embed)
                return

            # Create leaderboard embed
            period_title = period.replace("_", " ").title()
            embed = discord.Embed(
                title=f"🏆 {period_title} Leaderboard",
                color=0xFFD700,
            )

            leaderboard_text = ""
            for entry in entries[:10]:  # Top 10 only
                rank_emoji = (
                    "🥇"
                    if entry.rank == 1
                    else "🥈"
                    if entry.rank == 2
                    else "🥉"
                    if entry.rank == 3
                    else f"{entry.rank}."
                )

                # Try to get actual username from bot
                try:
                    user = self.bot.get_user(entry.user_id)
                    username = user.display_name if user else f"User#{entry.user_id}"
                except:
                    username = f"User#{entry.user_id}"

                leaderboard_text += f"{rank_emoji} **{username}**\n"
                leaderboard_text += f"   💰 {entry.total_points:,} pts | 🎯 {entry.accuracy_percentage:.1f}% | 🔥 {entry.current_streak}\n\n"

            embed.description = leaderboard_text

            # Add user's position if not in top 10
            user_entry = next((e for e in entries if e.user_id == ctx.author.id), None)
            if user_entry and user_entry.rank > 10:
                embed.add_field(
                    name="Your Position",
                    value=f"#{user_entry.rank} - {user_entry.total_points:,} pts ({user_entry.accuracy_percentage:.1f}%)",
                    inline=False,
                )

            embed.set_footer(text=f"Use !myrank to see your detailed position")

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while getting the leaderboard. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    # @commands.command(name="myrank", aliases=["rank"])
    # Disabled - handled by leaderboard_commands.py cog
    async def my_rank_disabled(self, ctx):
        """Show user's current rank and nearby positions."""
        try:
            from utils.leaderboard_manager import leaderboard_manager

            user_id = ctx.author.id

            # Get user's rank for different periods
            all_time_rank = await leaderboard_manager.get_user_rank(user_id, "all_time")
            weekly_rank = await leaderboard_manager.get_user_rank(user_id, "weekly")
            monthly_rank = await leaderboard_manager.get_user_rank(user_id, "monthly")

            # Get user stats
            user_stats = await user_manager.get_user_stats(user_id)
            user_profile = user_stats.user_profile

            embed = discord.Embed(
                title="📊 Your Ranking",
                description=f"Ranking information for **{ctx.author.display_name}**",
                color=0x00BFFF,
            )

            # All-time ranking
            if all_time_rank:
                rank, total = all_time_rank
                embed.add_field(
                    name="🏆 All-Time",
                    value=f"**Rank:** #{rank} of {total}\n**Points:** {user_profile.total_points:,}",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="🏆 All-Time",
                    value="**Rank:** Unranked\n**Points:** 0",
                    inline=True,
                )

            # Weekly ranking
            if weekly_rank:
                rank, total = weekly_rank
                embed.add_field(
                    name="📅 This Week",
                    value=f"**Rank:** #{rank} of {total}",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="📅 This Week",
                    value="**Rank:** Unranked",
                    inline=True,
                )

            # Monthly ranking
            if monthly_rank:
                rank, total = monthly_rank
                embed.add_field(
                    name="📆 This Month",
                    value=f"**Rank:** #{rank} of {total}",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="📆 This Month",
                    value="**Rank:** Unranked",
                    inline=True,
                )

            # Performance summary
            embed.add_field(
                name="📈 Performance",
                value=f"**Accuracy:** {user_profile.accuracy_percentage:.1f}%\n"
                f"**Current Streak:** {user_profile.current_streak}\n"
                f"**Best Streak:** {user_profile.best_streak}",
                inline=False,
            )

            # Get nearby ranks for context
            if all_time_rank:
                nearby_entries = await leaderboard_manager.get_nearby_ranks(
                    user_id, "all_time", context_size=2
                )

                if nearby_entries:
                    nearby_text = ""
                    for entry in nearby_entries:
                        if entry.user_id == user_id:
                            nearby_text += (
                                f"**#{entry.rank} YOU - {entry.total_points:,} pts**\n"
                            )
                        else:
                            try:
                                user = self.bot.get_user(entry.user_id)
                                username = (
                                    user.display_name
                                    if user
                                    else f"User#{entry.user_id}"
                                )
                            except:
                                username = f"User#{entry.user_id}"
                            nearby_text += f"#{entry.rank} {username} - {entry.total_points:,} pts\n"

                    embed.add_field(
                        name="🎯 Nearby Rankings",
                        value=nearby_text,
                        inline=False,
                    )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in myrank command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while getting your rank. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="triviaconfig", aliases=["tconfig"])
    @commands.has_permissions(administrator=True)
    async def trivia_config(self, ctx, setting: str = None, *, value: str = None):
        """View or update trivia configuration settings (Admin only)."""
        try:
            # If no arguments, show current configuration
            if not setting:
                embed = discord.Embed(
                    title="⚙️ Trivia Configuration",
                    description="Current trivia system settings",
                    color=0x9932CC,
                )

                # Default settings (these could be stored in database in a full implementation)
                settings = {
                    "timeout": "30 seconds",
                    "easy_points": "10 points",
                    "medium_points": "20 points",
                    "hard_points": "30 points",
                    "daily_challenge_multiplier": "2x points",
                    "weekly_challenge_multiplier": "3x points",
                    "countdown_intervals": "20s, 10s",
                }

                settings_text = ""
                for key, val in settings.items():
                    settings_text += f"**{key.replace('_', ' ').title()}:** {val}\n"

                embed.add_field(
                    name="Current Settings",
                    value=settings_text,
                    inline=False,
                )

                embed.add_field(
                    name="Usage",
                    value="Use `!triviaconfig <setting> <value>` to update settings\n"
                    "Available settings: timeout, easy_points, medium_points, hard_points",
                    inline=False,
                )

                await ctx.send(embed=embed)
                return

            # Validate setting name
            valid_settings = ["timeout", "easy_points", "medium_points", "hard_points"]
            if setting.lower() not in valid_settings:
                embed = discord.Embed(
                    title="❌ Invalid Setting",
                    description=f"Valid settings: {', '.join(valid_settings)}",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # If no value provided, show current value
            if not value:
                embed = discord.Embed(
                    title=f"⚙️ {setting.replace('_', ' ').title()}",
                    description=f"Current value: **{self._get_config_value(setting)}**",
                    color=0x9932CC,
                )
                await ctx.send(embed=embed)
                return

            # Update setting
            success = await self._update_config_setting(setting, value)

            if success:
                embed = discord.Embed(
                    title="✅ Setting Updated",
                    description=f"**{setting.replace('_', ' ').title()}** has been updated to: **{value}**",
                    color=discord.Color.green(),
                )
            else:
                embed = discord.Embed(
                    title="❌ Update Failed",
                    description=f"Failed to update **{setting}**. Please check the value format.",
                    color=discord.Color.red(),
                )

            await ctx.send(embed=embed)

        except commands.MissingPermissions:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in triviaconfig command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while managing trivia configuration.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="resetstats")
    @commands.has_permissions(administrator=True)
    async def reset_stats(self, ctx, user: discord.Member):
        """Reset a user's trivia statistics (Admin only)."""
        try:
            user_id = user.id

            # Confirmation embed
            embed = discord.Embed(
                title="⚠️ Confirm Statistics Reset",
                description=f"Are you sure you want to reset **{user.display_name}**'s trivia statistics?\n\n"
                "This will reset:\n"
                "• Total points\n"
                "• Questions answered/correct\n"
                "• Streaks\n"
                "• Achievements\n"
                "• Challenge completions\n\n"
                "**This action cannot be undone!**",
                color=discord.Color.orange(),
            )

            embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")

            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

            def check(reaction, reaction_user):
                return (
                    reaction_user == ctx.author
                    and str(reaction.emoji) in ["✅", "❌"]
                    and reaction.message.id == message.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )

                if str(reaction.emoji) == "✅":
                    # Perform the reset
                    success = await user_manager.reset_user_stats(user_id)

                    if success:
                        embed = discord.Embed(
                            title="✅ Statistics Reset",
                            description=f"Successfully reset **{user.display_name}**'s trivia statistics.",
                            color=discord.Color.green(),
                        )
                    else:
                        embed = discord.Embed(
                            title="❌ Reset Failed",
                            description=f"Failed to reset **{user.display_name}**'s statistics. Please try again.",
                            color=discord.Color.red(),
                        )
                else:
                    embed = discord.Embed(
                        title="❌ Reset Cancelled",
                        description="Statistics reset has been cancelled.",
                        color=discord.Color.blue(),
                    )

                await message.edit(embed=embed)
                await message.clear_reactions()

            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Timeout",
                    description="Reset confirmation timed out. No changes were made.",
                    color=discord.Color.orange(),
                )
                await message.edit(embed=embed)
                await message.clear_reactions()

        except commands.MissingPermissions:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in resetstats command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while resetting user statistics.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="addquestion", aliases=["addq"])
    @commands.has_permissions(administrator=True)
    async def add_question(self, ctx):
        """Add a custom trivia question through guided process (Admin only)."""
        try:
            user_id = ctx.author.id

            embed = discord.Embed(
                title="📝 Add Custom Question",
                description="Let's create a new trivia question! I'll guide you through the process.\n\n"
                "**Step 1:** What's the question text?",
                color=0x9932CC,
            )
            embed.set_footer(text="Type your response or 'cancel' to stop")

            await ctx.send(embed=embed)

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            # Step 1: Get question text
            try:
                msg = await self.bot.wait_for("message", timeout=120.0, check=check)
                if msg.content.lower() == "cancel":
                    await ctx.send("❌ Question creation cancelled.")
                    return
                question_text = msg.content
            except asyncio.TimeoutError:
                await ctx.send("⏰ Question creation timed out.")
                return

            # Step 2: Get question type
            embed = discord.Embed(
                title="📝 Add Custom Question",
                description=f"**Question:** {question_text}\n\n"
                "**Step 2:** What type of question is this?\n"
                "1. Multiple Choice (A, B, C, D)\n"
                "2. True/False\n"
                "3. Fill in the Blank",
                color=0x9932CC,
            )
            embed.set_footer(text="Type 1, 2, or 3")

            await ctx.send(embed=embed)

            try:
                msg = await self.bot.wait_for("message", timeout=60.0, check=check)
                if msg.content.lower() == "cancel":
                    await ctx.send("❌ Question creation cancelled.")
                    return

                type_map = {
                    "1": "multiple_choice",
                    "2": "true_false",
                    "3": "fill_blank",
                }
                if msg.content not in type_map:
                    await ctx.send("❌ Invalid choice. Question creation cancelled.")
                    return

                question_type = type_map[msg.content]
            except asyncio.TimeoutError:
                await ctx.send("⏰ Question creation timed out.")
                return

            # Step 3: Get options (for multiple choice) or correct answer
            options = None
            if question_type == "multiple_choice":
                embed = discord.Embed(
                    title="📝 Add Custom Question",
                    description=f"**Question:** {question_text}\n"
                    f"**Type:** Multiple Choice\n\n"
                    "**Step 3:** Provide 4 options separated by semicolons (;)\n"
                    "Example: Option A; Option B; Option C; Option D",
                    color=0x9932CC,
                )
                await ctx.send(embed=embed)

                try:
                    msg = await self.bot.wait_for("message", timeout=120.0, check=check)
                    if msg.content.lower() == "cancel":
                        await ctx.send("❌ Question creation cancelled.")
                        return

                    options = [opt.strip() for opt in msg.content.split(";")]
                    if len(options) != 4:
                        await ctx.send(
                            "❌ Please provide exactly 4 options. Question creation cancelled."
                        )
                        return
                except asyncio.TimeoutError:
                    await ctx.send("⏰ Question creation timed out.")
                    return

            # Step 4: Get correct answer
            if question_type == "multiple_choice":
                embed = discord.Embed(
                    title="📝 Add Custom Question",
                    description=f"**Question:** {question_text}\n"
                    f"**Options:** {', '.join(options)}\n\n"
                    "**Step 4:** Which option is correct? (A, B, C, or D)",
                    color=0x9932CC,
                )
                await ctx.send(embed=embed)

                try:
                    msg = await self.bot.wait_for("message", timeout=60.0, check=check)
                    if msg.content.lower() == "cancel":
                        await ctx.send("❌ Question creation cancelled.")
                        return

                    answer_map = {"a": 0, "b": 1, "c": 2, "d": 3}
                    if msg.content.lower() not in answer_map:
                        await ctx.send(
                            "❌ Invalid answer choice. Question creation cancelled."
                        )
                        return

                    correct_answer = answer_map[msg.content.lower()]
                except asyncio.TimeoutError:
                    await ctx.send("⏰ Question creation timed out.")
                    return
            else:
                embed = discord.Embed(
                    title="📝 Add Custom Question",
                    description=f"**Question:** {question_text}\n"
                    f"**Type:** {question_type.replace('_', ' ').title()}\n\n"
                    "**Step 4:** What's the correct answer?",
                    color=0x9932CC,
                )
                await ctx.send(embed=embed)

                try:
                    msg = await self.bot.wait_for("message", timeout=120.0, check=check)
                    if msg.content.lower() == "cancel":
                        await ctx.send("❌ Question creation cancelled.")
                        return
                    correct_answer = msg.content
                except asyncio.TimeoutError:
                    await ctx.send("⏰ Question creation timed out.")
                    return

            # Step 5: Get difficulty
            embed = discord.Embed(
                title="📝 Add Custom Question",
                description="**Step 5:** What difficulty level?\n"
                "1. Easy (10 points)\n"
                "2. Medium (20 points)\n"
                "3. Hard (30 points)",
                color=0x9932CC,
            )
            await ctx.send(embed=embed)

            try:
                msg = await self.bot.wait_for("message", timeout=60.0, check=check)
                if msg.content.lower() == "cancel":
                    await ctx.send("❌ Question creation cancelled.")
                    return

                difficulty_map = {"1": "easy", "2": "medium", "3": "hard"}
                if msg.content not in difficulty_map:
                    await ctx.send(
                        "❌ Invalid difficulty. Question creation cancelled."
                    )
                    return

                difficulty = difficulty_map[msg.content]
            except asyncio.TimeoutError:
                await ctx.send("⏰ Question creation timed out.")
                return

            # Step 6: Get category
            embed = discord.Embed(
                title="📝 Add Custom Question",
                description="**Step 6:** What category does this question belong to?\n"
                "Examples: history, players, matches, general, stats",
                color=0x9932CC,
            )
            await ctx.send(embed=embed)

            try:
                msg = await self.bot.wait_for("message", timeout=60.0, check=check)
                if msg.content.lower() == "cancel":
                    await ctx.send("❌ Question creation cancelled.")
                    return
                category = msg.content.lower()
            except asyncio.TimeoutError:
                await ctx.send("⏰ Question creation timed out.")
                return

            # Optional: Get explanation
            embed = discord.Embed(
                title="📝 Add Custom Question",
                description="**Step 7 (Optional):** Provide an explanation for the answer.\n"
                "Type 'skip' to skip this step.",
                color=0x9932CC,
            )
            await ctx.send(embed=embed)

            try:
                msg = await self.bot.wait_for("message", timeout=60.0, check=check)
                explanation = (
                    None if msg.content.lower() in ["skip", "cancel"] else msg.content
                )
            except asyncio.TimeoutError:
                explanation = None

            # Create question data
            question_data = {
                "question_text": question_text,
                "question_type": question_type,
                "difficulty": difficulty,
                "category": category,
                "correct_answer": correct_answer,
                "options": options,
                "explanation": explanation,
            }

            # Add the question
            success = await self.question_engine.add_custom_question(question_data)

            if success:
                embed = discord.Embed(
                    title="✅ Question Added Successfully",
                    description=f"**Question:** {question_text}\n"
                    f"**Type:** {question_type.replace('_', ' ').title()}\n"
                    f"**Difficulty:** {difficulty.title()}\n"
                    f"**Category:** {category.title()}",
                    color=discord.Color.green(),
                )
            else:
                embed = discord.Embed(
                    title="❌ Failed to Add Question",
                    description="There was an error adding the question to the database.",
                    color=discord.Color.red(),
                )

            await ctx.send(embed=embed)

        except commands.MissingPermissions:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in addquestion command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while adding the question.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    def _get_config_value(self, setting: str) -> str:
        """Get current configuration value for a setting."""
        # In a full implementation, these would be stored in database
        defaults = {
            "timeout": "30 seconds",
            "easy_points": "10 points",
            "medium_points": "20 points",
            "hard_points": "30 points",
        }
        return defaults.get(setting, "Unknown")

    async def _update_config_setting(self, setting: str, value: str) -> bool:
        """Update a configuration setting."""
        try:
            # In a full implementation, this would update the database
            # For now, we'll just validate the input format

            if setting == "timeout":
                # Validate timeout format (should be a number)
                try:
                    timeout_value = int(
                        value.replace("s", "").replace("seconds", "").strip()
                    )
                    if 10 <= timeout_value <= 300:  # 10 seconds to 5 minutes
                        return True
                except ValueError:
                    pass
                return False

            elif setting.endswith("_points"):
                # Validate points format
                try:
                    points_value = int(
                        value.replace("points", "").replace("pts", "").strip()
                    )
                    if 1 <= points_value <= 100:  # 1 to 100 points
                        return True
                except ValueError:
                    pass
                return False

            return False

        except Exception as e:
            logger.error(f"Error updating config setting {setting}: {e}")
            return False

    async def _handle_challenge_result(self, channel, user, result, game_session):
        """Handle the result of a challenge answer."""
        try:
            user_id = user.id

            # Determine challenge type based on active challenges
            challenge_type = None
            if user_id in self.challenge_system.active_daily_challenges:
                challenge_type = "daily"
            elif user_id in self.challenge_system.active_weekly_challenges:
                challenge_type = "weekly"

            if not challenge_type:
                logger.warning(f"Could not determine challenge type for user {user_id}")
                return

            # Process challenge-specific result
            if challenge_type == "daily":
                challenge_result = (
                    await self.challenge_system.process_daily_challenge_answer(
                        user_id, result.is_correct, result.time_taken
                    )
                )
            else:  # weekly
                challenge_result = (
                    await self.challenge_system.process_weekly_challenge_answer(
                        user_id, result.is_correct, result.time_taken
                    )
                )

            if not challenge_result.get("success"):
                logger.error(f"Challenge processing failed: {challenge_result}")
                return

            # Create result embed
            embed = await self._create_result_embed(user, result, challenge_result)
            await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error handling challenge result: {e}", exc_info=True)

    async def _create_result_embed(
        self, user, result, challenge_result
    ) -> discord.Embed:
        """Create an embed for challenge results."""
        challenge_type = challenge_result["challenge_type"]

        if result.is_correct:
            color = discord.Color.green()
            title = "🎉 Correct!"
            description = f"**{user.display_name}** got it right!"
        else:
            color = discord.Color.red()
            title = "❌ Incorrect!"
            description = f"Sorry **{user.display_name}**, that's not right."

        embed = discord.Embed(title=title, description=description, color=color)

        # Add points information
        if challenge_type == "daily":
            embed.add_field(
                name="💰 Points Earned",
                value=f"{challenge_result['challenge_points']} points (2x bonus!)",
                inline=True,
            )
        else:  # weekly
            embed.add_field(
                name="💰 Points This Question",
                value=f"{challenge_result['points']} points",
                inline=True,
            )

            if challenge_result.get("is_completed"):
                # Weekly challenge completed
                embed.add_field(
                    name="🏆 Challenge Complete!",
                    value=f"Final Score: {challenge_result['final_score']}\nTotal Points: {challenge_result['final_points']} (3x bonus!)",
                    inline=False,
                )

                if challenge_result.get("badge_awarded"):
                    badge_name = (
                        challenge_result["badge_awarded"].replace("_", " ").title()
                    )
                    embed.add_field(
                        name="🏅 Badge Earned",
                        value=badge_name,
                        inline=True,
                    )
            else:
                # Show weekly progress
                embed.add_field(
                    name="📊 Progress",
                    value=f"Question {challenge_result['question_number']}/{challenge_result['total_questions']}\nCorrect: {challenge_result['correct_so_far']}",
                    inline=True,
                )

        # Add explanation if available
        if result.explanation:
            embed.add_field(
                name="💡 Explanation",
                value=result.explanation,
                inline=False,
            )

        return embed

    async def _handle_trivia_result(self, channel, user, result, game_session):
        """Handle the result of a regular trivia answer."""
        try:
            user_id = user.id

            # Update user statistics
            await user_manager.update_stats(
                user_id=user_id,
                points=result.points_earned,
                is_correct=result.is_correct,
                difficulty=game_session.difficulty,
                category=game_session.question.category
                if hasattr(game_session, "question")
                else "general",
            )

            # Check for achievements
            from utils.achievement_system import achievement_system

            user_profile = await user_manager.get_or_create_user(user_id)

            achievement_context = {
                "current_streak": user_profile.current_streak,
                "total_points": user_profile.total_points,
                "questions_answered": user_profile.questions_answered,
                "questions_correct": user_profile.questions_correct,
            }

            new_achievements = await achievement_system.check_achievements(
                user_id, achievement_context
            )

            # Create result embed
            if result.is_correct:
                color = discord.Color.green()
                title = "🎉 Correct!"
                description = f"**{user.display_name}** got it right!"
            else:
                color = discord.Color.red()
                title = "❌ Incorrect!"
                description = f"Sorry **{user.display_name}**, that's not right."

            embed = discord.Embed(title=title, description=description, color=color)

            # Add points information
            if result.is_correct:
                embed.add_field(
                    name="💰 Points Earned",
                    value=f"{result.points_earned} points",
                    inline=True,
                )

                # Add streak info
                if user_profile.current_streak > 1:
                    embed.add_field(
                        name="🔥 Streak",
                        value=f"{user_profile.current_streak} in a row!",
                        inline=True,
                    )

            # Add explanation if available
            if result.explanation:
                embed.add_field(
                    name="💡 Explanation",
                    value=result.explanation,
                    inline=False,
                )

            # Add achievement notifications
            if new_achievements:
                achievement_text = ""
                for achievement in new_achievements:
                    achievement_text += f"{achievement.emoji} **{achievement.name}** (+{achievement.reward_points} pts)\n"

                embed.add_field(
                    name="🏆 Achievement Unlocked!",
                    value=achievement_text,
                    inline=False,
                )

            await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error handling trivia result: {e}", exc_info=True)


async def setup(bot):
    """Set up the enhanced trivia cog."""
    await bot.add_cog(EnhancedTriviaCog(bot))
    logger.info("EnhancedTriviaCog added to bot")
