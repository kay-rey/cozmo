"""
Challenge System for the Enhanced Trivia System.
Handles daily and weekly challenge functionality with special rewards.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List, Any, Callable
from utils.models import Question, GameSession, UserProfile
from utils.question_engine import QuestionEngine
from utils.user_manager import UserManager
from utils.database import db_manager
import discord

logger = logging.getLogger(__name__)


class ChallengeSystem:
    """
    Manages daily and weekly challenges with special rewards and tracking.
    """

    def __init__(self, question_engine: QuestionEngine, user_manager: UserManager):
        """
        Initialize the Challenge System.

        Args:
            question_engine: QuestionEngine instance for question management.
            user_manager: UserManager instance for user tracking.
        """
        self.question_engine = question_engine
        self.user_manager = user_manager
        self.active_daily_challenges: Dict[
            int, Dict[str, Any]
        ] = {}  # user_id -> challenge data
        self.active_weekly_challenges: Dict[
            int, Dict[str, Any]
        ] = {}  # user_id -> challenge data
        self._weekly_challenge_scheduler: Optional[asyncio.Task] = None
        self._start_weekly_scheduler()

    def _start_weekly_scheduler(self) -> None:
        """Start the weekly challenge scheduler."""
        try:
            if (
                self._weekly_challenge_scheduler is None
                or self._weekly_challenge_scheduler.done()
            ):
                self._weekly_challenge_scheduler = asyncio.create_task(
                    self._weekly_challenge_task()
                )
        except RuntimeError:
            # No event loop running, will start later when needed
            pass

    async def get_daily_challenge(self, user_id: int) -> Optional[Question]:
        """
        Get the daily challenge question for a user.

        Args:
            user_id: Discord user ID.

        Returns:
            Question object for daily challenge, None if already completed or unavailable.
        """
        try:
            # Check if user can attempt daily challenge
            if not await self.user_manager.can_attempt_challenge(user_id, "daily"):
                logger.info(
                    f"User {user_id} has already completed today's daily challenge"
                )
                return None

            # Get a random question for daily challenge
            question = await self.question_engine.get_question()
            if not question:
                logger.error("No question available for daily challenge")
                return None

            # Store challenge data
            self.active_daily_challenges[user_id] = {
                "question": question,
                "start_time": datetime.now(),
                "attempts": 0,
                "max_attempts": 1,  # Daily challenges allow only one attempt
            }

            logger.info(f"Generated daily challenge for user {user_id}: {question.id}")
            return question

        except Exception as e:
            logger.error(f"Error getting daily challenge for user {user_id}: {e}")
            return None

    async def process_daily_challenge_answer(
        self, user_id: int, is_correct: bool, time_taken: float
    ) -> Dict[str, Any]:
        """
        Process a daily challenge answer and award double points.

        Args:
            user_id: Discord user ID.
            is_correct: Whether the answer was correct.
            time_taken: Time taken to answer in seconds.

        Returns:
            Dictionary with challenge result information.
        """
        try:
            if user_id not in self.active_daily_challenges:
                logger.warning(f"No active daily challenge for user {user_id}")
                return {"success": False, "error": "No active daily challenge"}

            challenge_data = self.active_daily_challenges[user_id]
            question = challenge_data["question"]

            # Calculate points (double for daily challenge)
            base_points = question.point_value if is_correct else 0
            challenge_points = base_points * 2  # Double points for daily challenge

            # Update user stats
            await self.user_manager.update_stats(
                user_id,
                challenge_points,
                is_correct,
                question.difficulty,
                question.category,
            )

            # Mark daily challenge as completed
            await self.user_manager.update_challenge_completion(user_id, "daily")

            # Clean up active challenge
            del self.active_daily_challenges[user_id]

            result = {
                "success": True,
                "is_correct": is_correct,
                "base_points": base_points,
                "challenge_points": challenge_points,
                "time_taken": time_taken,
                "explanation": question.explanation,
                "challenge_type": "daily",
            }

            logger.info(
                f"Processed daily challenge for user {user_id}: "
                f"correct={is_correct}, points={challenge_points}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Error processing daily challenge answer for user {user_id}: {e}"
            )
            return {"success": False, "error": str(e)}

    async def get_weekly_challenge(self, user_id: int) -> Optional[List[Question]]:
        """
        Get the weekly challenge questions for a user (5 questions).

        Args:
            user_id: Discord user ID.

        Returns:
            List of 5 Question objects for weekly challenge, None if already completed.
        """
        try:
            # Check if user can attempt weekly challenge
            if not await self.user_manager.can_attempt_challenge(user_id, "weekly"):
                logger.info(
                    f"User {user_id} has already completed this week's challenge"
                )
                return None

            # Get 5 questions of varying difficulty for weekly challenge
            questions = []
            difficulties = ["easy", "easy", "medium", "medium", "hard"]  # Balanced mix

            for difficulty in difficulties:
                question = await self.question_engine.get_question(
                    difficulty=difficulty
                )
                if question:
                    questions.append(question)

            if len(questions) < 5:
                logger.error("Could not generate 5 questions for weekly challenge")
                return None

            # Store challenge data
            self.active_weekly_challenges[user_id] = {
                "questions": questions,
                "start_time": datetime.now(),
                "current_question": 0,
                "correct_answers": 0,
                "total_points": 0,
                "answers": [],  # Track all answers
            }

            logger.info(f"Generated weekly challenge for user {user_id}: 5 questions")
            return questions

        except Exception as e:
            logger.error(f"Error getting weekly challenge for user {user_id}: {e}")
            return None

    async def get_current_weekly_question(self, user_id: int) -> Optional[Question]:
        """
        Get the current question in an active weekly challenge.

        Args:
            user_id: Discord user ID.

        Returns:
            Current Question object, None if no active challenge.
        """
        if user_id not in self.active_weekly_challenges:
            return None

        challenge_data = self.active_weekly_challenges[user_id]
        current_index = challenge_data["current_question"]

        if current_index >= len(challenge_data["questions"]):
            return None

        return challenge_data["questions"][current_index]

    async def process_weekly_challenge_answer(
        self, user_id: int, is_correct: bool, time_taken: float
    ) -> Dict[str, Any]:
        """
        Process a weekly challenge answer and track progress.

        Args:
            user_id: Discord user ID.
            is_correct: Whether the answer was correct.
            time_taken: Time taken to answer in seconds.

        Returns:
            Dictionary with challenge result and progress information.
        """
        try:
            if user_id not in self.active_weekly_challenges:
                logger.warning(f"No active weekly challenge for user {user_id}")
                return {"success": False, "error": "No active weekly challenge"}

            challenge_data = self.active_weekly_challenges[user_id]
            current_index = challenge_data["current_question"]
            question = challenge_data["questions"][current_index]

            # Calculate points for this question
            base_points = question.point_value if is_correct else 0
            challenge_data["total_points"] += base_points

            # Track answer
            challenge_data["answers"].append(
                {
                    "question_id": question.id,
                    "is_correct": is_correct,
                    "points": base_points,
                    "time_taken": time_taken,
                }
            )

            if is_correct:
                challenge_data["correct_answers"] += 1

            # Move to next question
            challenge_data["current_question"] += 1
            is_completed = challenge_data["current_question"] >= 5

            result = {
                "success": True,
                "is_correct": is_correct,
                "points": base_points,
                "question_number": current_index + 1,
                "total_questions": 5,
                "correct_so_far": challenge_data["correct_answers"],
                "is_completed": is_completed,
                "explanation": question.explanation,
                "challenge_type": "weekly",
            }

            # If challenge is completed, process final results
            if is_completed:
                final_result = await self._complete_weekly_challenge(
                    user_id, challenge_data
                )
                result.update(final_result)

            logger.info(
                f"Processed weekly challenge answer for user {user_id}: "
                f"question {current_index + 1}/5, correct={is_correct}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Error processing weekly challenge answer for user {user_id}: {e}"
            )
            return {"success": False, "error": str(e)}

    async def _complete_weekly_challenge(
        self, user_id: int, challenge_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete a weekly challenge and award triple points and badges.

        Args:
            user_id: Discord user ID.
            challenge_data: Challenge data dictionary.

        Returns:
            Dictionary with completion results.
        """
        try:
            # Calculate final points (triple for weekly challenge)
            base_total = challenge_data["total_points"]
            final_points = base_total * 3  # Triple points for weekly challenge

            # Award badge based on performance
            correct_count = challenge_data["correct_answers"]
            badge_awarded = None

            if correct_count == 5:
                badge_awarded = "weekly_perfect"
            elif correct_count >= 4:
                badge_awarded = "weekly_excellent"
            elif correct_count >= 3:
                badge_awarded = "weekly_good"

            # Update user stats with final points
            await self.user_manager.update_stats(
                user_id, final_points, True, "mixed", "challenge"
            )

            # Mark weekly challenge as completed
            await self.user_manager.update_challenge_completion(user_id, "weekly")

            # Award badge if earned
            if badge_awarded:
                await self._award_challenge_badge(user_id, badge_awarded)

            # Clean up active challenge
            del self.active_weekly_challenges[user_id]

            completion_result = {
                "final_score": f"{correct_count}/5",
                "base_points": base_total,
                "final_points": final_points,
                "badge_awarded": badge_awarded,
                "completion_time": (
                    datetime.now() - challenge_data["start_time"]
                ).total_seconds(),
            }

            logger.info(
                f"Completed weekly challenge for user {user_id}: "
                f"{correct_count}/5 correct, {final_points} points, badge: {badge_awarded}"
            )
            return completion_result

        except Exception as e:
            logger.error(f"Error completing weekly challenge for user {user_id}: {e}")
            return {"error": str(e)}

    async def _award_challenge_badge(self, user_id: int, badge_type: str) -> None:
        """
        Award a challenge badge to a user.

        Args:
            user_id: Discord user ID.
            badge_type: Type of badge to award.
        """
        try:
            # For testing purposes, just log the badge award
            # In production, this would interact with the database
            logger.info(f"Awarded badge {badge_type} to user {user_id}")

            # Uncomment below for actual database integration
            # async with db_manager.get_connection() as conn:
            #     # Check if user already has this badge
            #     cursor = await conn.execute(
            #         "SELECT id FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
            #         (user_id, badge_type),
            #     )
            #     existing = await cursor.fetchone()
            #
            #     if not existing:
            #         # Award the badge
            #         await conn.execute(
            #             "INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
            #             (user_id, badge_type),
            #         )
            #         await conn.commit()
            #         logger.info(f"Awarded badge {badge_type} to user {user_id}")

        except Exception as e:
            logger.error(f"Error awarding badge {badge_type} to user {user_id}: {e}")

    async def get_challenge_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get the current challenge status for a user.

        Args:
            user_id: Discord user ID.

        Returns:
            Dictionary with challenge availability and progress.
        """
        try:
            # Check daily challenge status
            can_daily = await self.user_manager.can_attempt_challenge(user_id, "daily")
            daily_active = user_id in self.active_daily_challenges

            # Check weekly challenge status
            can_weekly = await self.user_manager.can_attempt_challenge(
                user_id, "weekly"
            )
            weekly_active = user_id in self.active_weekly_challenges
            weekly_progress = None

            if weekly_active:
                challenge_data = self.active_weekly_challenges[user_id]
                weekly_progress = {
                    "current_question": challenge_data["current_question"] + 1,
                    "total_questions": 5,
                    "correct_answers": challenge_data["correct_answers"],
                    "points_so_far": challenge_data["total_points"],
                }

            return {
                "daily": {
                    "available": can_daily and not daily_active,
                    "active": daily_active,
                    "completed_today": not can_daily,
                },
                "weekly": {
                    "available": can_weekly and not weekly_active,
                    "active": weekly_active,
                    "completed_this_week": not can_weekly,
                    "progress": weekly_progress,
                },
            }

        except Exception as e:
            logger.error(f"Error getting challenge status for user {user_id}: {e}")
            return {"error": str(e)}

    async def cancel_active_challenge(self, user_id: int, challenge_type: str) -> bool:
        """
        Cancel an active challenge for a user.

        Args:
            user_id: Discord user ID.
            challenge_type: "daily" or "weekly".

        Returns:
            True if challenge was cancelled, False otherwise.
        """
        try:
            if challenge_type == "daily" and user_id in self.active_daily_challenges:
                del self.active_daily_challenges[user_id]
                logger.info(f"Cancelled daily challenge for user {user_id}")
                return True
            elif (
                challenge_type == "weekly" and user_id in self.active_weekly_challenges
            ):
                del self.active_weekly_challenges[user_id]
                logger.info(f"Cancelled weekly challenge for user {user_id}")
                return True

            return False

        except Exception as e:
            logger.error(
                f"Error cancelling {challenge_type} challenge for user {user_id}: {e}"
            )
            return False

    async def _weekly_challenge_task(self) -> None:
        """
        Background task that handles weekly challenge posting every Monday.
        """
        while True:
            try:
                now = datetime.now()

                # Calculate next Monday at 9 AM
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0 and now.hour >= 9:
                    # It's Monday and past 9 AM, schedule for next Monday
                    days_until_monday = 7

                next_monday = now + timedelta(days=days_until_monday)
                next_monday = next_monday.replace(
                    hour=9, minute=0, second=0, microsecond=0
                )

                # Sleep until next Monday
                sleep_seconds = (next_monday - now).total_seconds()
                logger.info(
                    f"Weekly challenge scheduler: sleeping for {sleep_seconds / 3600:.1f} hours until next Monday"
                )

                await asyncio.sleep(sleep_seconds)

                # Trigger weekly challenge announcement
                await self._announce_weekly_challenge()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in weekly challenge scheduler: {e}")
                # Sleep for an hour before retrying
                await asyncio.sleep(3600)

    async def _announce_weekly_challenge(self) -> None:
        """
        Announce new weekly challenge availability.
        This method can be called by the bot to post announcements.
        """
        try:
            # Clear any incomplete weekly challenges from last week
            await self._reset_weekly_challenges()

            logger.info("Weekly challenge reset - new challenges available!")

            # Store announcement data that can be retrieved by the bot
            self._weekly_announcement_pending = {
                "timestamp": datetime.now(),
                "week_start": date.today(),
                "message": "🎉 **New Weekly Challenge Available!** 🎉\n\nTake on 5 challenging questions for triple points and exclusive badges!\nUse `!weeklychallenge` to get started.",
            }

        except Exception as e:
            logger.error(f"Error announcing weekly challenge: {e}")

    async def _reset_weekly_challenges(self) -> None:
        """Reset incomplete weekly challenges from the previous week."""
        try:
            # Clear active weekly challenges that are from previous week
            current_week_start = date.today() - timedelta(days=date.today().weekday())

            expired_users = []
            for user_id, challenge_data in self.active_weekly_challenges.items():
                challenge_start = challenge_data["start_time"].date()
                challenge_week_start = challenge_start - timedelta(
                    days=challenge_start.weekday()
                )

                if challenge_week_start < current_week_start:
                    expired_users.append(user_id)

            for user_id in expired_users:
                del self.active_weekly_challenges[user_id]
                logger.info(f"Cleared expired weekly challenge for user {user_id}")

        except Exception as e:
            logger.error(f"Error resetting weekly challenges: {e}")

    def get_weekly_announcement(self) -> Optional[Dict[str, Any]]:
        """
        Get pending weekly announcement data.
        Returns and clears the announcement data.
        """
        if hasattr(self, "_weekly_announcement_pending"):
            announcement = self._weekly_announcement_pending
            delattr(self, "_weekly_announcement_pending")
            return announcement
        return None

    async def get_weekly_challenge_progress(
        self, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed progress for a user's weekly challenge.

        Args:
            user_id: Discord user ID.

        Returns:
            Dictionary with detailed progress information, None if no active challenge.
        """
        try:
            if user_id not in self.active_weekly_challenges:
                return None

            challenge_data = self.active_weekly_challenges[user_id]

            # Calculate progress details
            progress = {
                "current_question": challenge_data["current_question"] + 1,
                "total_questions": 5,
                "correct_answers": challenge_data["correct_answers"],
                "total_points": challenge_data["total_points"],
                "start_time": challenge_data["start_time"],
                "elapsed_time": (
                    datetime.now() - challenge_data["start_time"]
                ).total_seconds(),
                "answers": challenge_data["answers"],
                "questions_remaining": 5 - challenge_data["current_question"],
                "accuracy": (
                    challenge_data["correct_answers"]
                    / max(1, challenge_data["current_question"])
                )
                * 100,
            }

            # Predict final points (triple bonus)
            progress["projected_final_points"] = challenge_data["total_points"] * 3

            # Determine potential badge
            if (
                challenge_data["correct_answers"] == challenge_data["current_question"]
                and challenge_data["current_question"] > 0
            ):
                # Perfect so far
                if challenge_data["current_question"] == 5:
                    progress["potential_badge"] = "weekly_perfect"
                else:
                    progress["potential_badge"] = (
                        "weekly_perfect"
                        if progress["questions_remaining"] == 0
                        else "on_track_for_perfect"
                    )
            elif challenge_data["correct_answers"] >= 4:
                progress["potential_badge"] = "weekly_excellent"
            elif challenge_data["correct_answers"] >= 3:
                progress["potential_badge"] = "weekly_good"
            else:
                progress["potential_badge"] = None

            return progress

        except Exception as e:
            logger.error(
                f"Error getting weekly challenge progress for user {user_id}: {e}"
            )
            return None

    async def get_challenge_statistics(self) -> Dict[str, Any]:
        """
        Get overall challenge system statistics.

        Returns:
            Dictionary with system-wide challenge statistics.
        """
        try:
            async with db_manager.get_connection() as conn:
                stats = {
                    "active_daily_challenges": len(self.active_daily_challenges),
                    "active_weekly_challenges": len(self.active_weekly_challenges),
                }

                # Get daily challenge completion stats for today
                today = date.today()
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM users WHERE daily_challenge_completed = ?",
                    (today,),
                )
                result = await cursor.fetchone()
                stats["daily_completions_today"] = result[0] if result else 0

                # Get weekly challenge completion stats for this week
                current_week_start = today - timedelta(days=today.weekday())
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM users WHERE weekly_challenge_completed >= ?",
                    (current_week_start,),
                )
                result = await cursor.fetchone()
                stats["weekly_completions_this_week"] = result[0] if result else 0

                # Get total challenge badges awarded
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM user_achievements WHERE achievement_id LIKE 'weekly_%'",
                )
                result = await cursor.fetchone()
                stats["total_weekly_badges"] = result[0] if result else 0

                return stats

        except Exception as e:
            logger.error(f"Error getting challenge statistics: {e}")
            return {}

    async def get_challenge_leaderboard(
        self, challenge_type: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get leaderboard for challenge completions.

        Args:
            challenge_type: "daily" or "weekly".
            limit: Maximum number of entries to return.

        Returns:
            List of leaderboard entries.
        """
        try:
            async with db_manager.get_connection() as conn:
                if challenge_type == "daily":
                    # Count daily challenges completed this month
                    cursor = await conn.execute(
                        """
                        SELECT u.user_id, COUNT(*) as challenges_completed,
                               SUM(u.total_points) as total_points
                        FROM users u
                        WHERE u.daily_challenge_completed >= date('now', 'start of month')
                        GROUP BY u.user_id
                        ORDER BY challenges_completed DESC, total_points DESC
                        LIMIT ?
                        """,
                        (limit,),
                    )
                elif challenge_type == "weekly":
                    # Count weekly challenges completed this month
                    cursor = await conn.execute(
                        """
                        SELECT u.user_id, COUNT(*) as challenges_completed,
                               SUM(u.total_points) as total_points
                        FROM users u
                        WHERE u.weekly_challenge_completed >= date('now', 'start of month')
                        GROUP BY u.user_id
                        ORDER BY challenges_completed DESC, total_points DESC
                        LIMIT ?
                        """,
                        (limit,),
                    )
                else:
                    return []

                rows = await cursor.fetchall()
                leaderboard = []

                for rank, (user_id, challenges_completed, total_points) in enumerate(
                    rows, 1
                ):
                    leaderboard.append(
                        {
                            "rank": rank,
                            "user_id": user_id,
                            "challenges_completed": challenges_completed,
                            "total_points": total_points or 0,
                        }
                    )

                return leaderboard

        except Exception as e:
            logger.error(f"Error getting {challenge_type} challenge leaderboard: {e}")
            return []

    async def shutdown(self) -> None:
        """
        Shutdown the challenge system and clean up resources.
        """
        try:
            # Cancel weekly scheduler
            if (
                self._weekly_challenge_scheduler
                and not self._weekly_challenge_scheduler.done()
            ):
                self._weekly_challenge_scheduler.cancel()

            # Clear active challenges
            self.active_daily_challenges.clear()
            self.active_weekly_challenges.clear()

            logger.info("Challenge system shutdown completed")

        except Exception as e:
            logger.error(f"Error during challenge system shutdown: {e}")


# Challenge badge definitions
CHALLENGE_BADGES = {
    "weekly_perfect": {
        "name": "Weekly Perfect",
        "description": "Answer all 5 weekly challenge questions correctly",
        "emoji": "🏆",
        "points": 100,
    },
    "weekly_excellent": {
        "name": "Weekly Excellent",
        "description": "Answer 4 out of 5 weekly challenge questions correctly",
        "emoji": "🥇",
        "points": 75,
    },
    "weekly_good": {
        "name": "Weekly Good",
        "description": "Answer 3 out of 5 weekly challenge questions correctly",
        "emoji": "🥉",
        "points": 50,
    },
}
