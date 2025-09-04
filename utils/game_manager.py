"""
Game Manager for the Enhanced Trivia System.
Handles game session tracking, timer management, and concurrent game support.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Any, Callable, Union
from utils.models import GameSession, Question, AnswerResult
from utils.question_engine import QuestionEngine
from utils.answer_processor import AnswerProcessor
import discord

logger = logging.getLogger(__name__)


class GameManager:
    """
    Manages trivia game sessions with timer support and concurrent game handling.
    Supports multiple active games across different channels with automatic cleanup.
    """

    def __init__(self, question_engine: QuestionEngine):
        """
        Initialize the Game Manager.

        Args:
            question_engine: QuestionEngine instance for question management.
        """
        self.question_engine = question_engine
        self.answer_processor = AnswerProcessor()
        self.active_games: Dict[int, GameSession] = {}  # channel_id -> GameSession
        self.game_timers: Dict[int, asyncio.Task] = {}  # channel_id -> timer task
        self.timeout_callbacks: Dict[
            int, Callable
        ] = {}  # channel_id -> callback function
        self.countdown_callbacks: Dict[
            int, Callable
        ] = {}  # channel_id -> countdown callback
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        except RuntimeError:
            # No event loop running, will start later when needed
            pass

    async def start_game(
        self,
        channel_id: int,
        user_id: int,
        difficulty: Optional[str] = None,
        is_challenge: bool = False,
        timeout_duration: int = 30,
        timeout_callback: Optional[Callable] = None,
        countdown_callback: Optional[Callable] = None,
    ) -> Optional[GameSession]:
        """
        Start a new trivia game session.

        Args:
            channel_id: Discord channel ID where the game is being played.
            user_id: Discord user ID who started the game.
            difficulty: Question difficulty ("easy", "medium", "hard"). If None, random.
            is_challenge: Whether this is a challenge game (daily/weekly).
            timeout_duration: Game timeout in seconds (default: 30).
            timeout_callback: Function to call when game times out.
            countdown_callback: Function to call for countdown notifications.

        Returns:
            GameSession object if game started successfully, None otherwise.
        """
        try:
            # Check if a game is already active in this channel
            if channel_id in self.active_games:
                logger.warning(f"Game already active in channel {channel_id}")
                return None

            # Get a question from the question engine
            question = await self.question_engine.get_question(difficulty=difficulty)
            if not question:
                logger.error(f"No question available for difficulty: {difficulty}")
                return None

            # Create game session
            game_session = GameSession(
                channel_id=channel_id,
                user_id=user_id,
                question_id=question.id,
                difficulty=question.difficulty,
                start_time=datetime.now(),
                is_challenge=is_challenge,
            )

            # Set runtime properties
            game_session.question = question
            game_session.timeout_duration = timeout_duration
            game_session.participants = {user_id}

            # Store the game session
            self.active_games[channel_id] = game_session

            # Store callbacks
            if timeout_callback:
                self.timeout_callbacks[channel_id] = timeout_callback
            if countdown_callback:
                self.countdown_callbacks[channel_id] = countdown_callback

            # Ensure cleanup task is running
            self._start_cleanup_task()

            # Start the timer
            await self._start_game_timer(channel_id, timeout_duration)

            logger.info(
                f"Started game in channel {channel_id} for user {user_id} "
                f"with difficulty {question.difficulty}"
            )
            return game_session

        except Exception as e:
            logger.error(
                f"Error starting game in channel {channel_id}: {e}", exc_info=True
            )
            # Cleanup on error
            await self._cleanup_game(channel_id)
            return None

    async def process_reaction_answer(
        self,
        channel_id: int,
        user_id: int,
        reaction: discord.Reaction,
        user: discord.User,
    ) -> Optional[AnswerResult]:
        """
        Process a reaction-based answer for an active game.

        Args:
            channel_id: Discord channel ID where the reaction was added.
            user_id: Discord user ID who reacted.
            reaction: Discord reaction object.
            user: Discord user object.

        Returns:
            AnswerResult object if answer was processed, None if no active game or invalid reaction.
        """
        try:
            # Check if there's an active game in this channel
            if channel_id not in self.active_games:
                logger.debug(f"No active game in channel {channel_id}")
                return None

            game_session = self.active_games[channel_id]

            # Check if this reaction is valid for the question type
            emoji_str = str(reaction.emoji)
            if not self.answer_processor.is_valid_reaction_for_question(
                game_session.question, emoji_str
            ):
                logger.debug(
                    f"Invalid reaction {emoji_str} for question type {game_session.question.question_type}"
                )
                return None

            # Process the reaction answer
            processed_answer = await self.answer_processor.process_reaction_answer(
                game_session.question, reaction, user
            )

            if processed_answer is None:
                logger.debug(f"Could not process reaction answer: {emoji_str}")
                return None

            # Validate and calculate result
            return await self._process_validated_answer(
                channel_id, user_id, processed_answer
            )

        except Exception as e:
            logger.error(
                f"Error processing reaction answer in channel {channel_id}: {e}",
                exc_info=True,
            )
            return None

    async def process_text_answer(
        self,
        channel_id: int,
        user_id: int,
        message: discord.Message,
    ) -> Optional[AnswerResult]:
        """
        Process a text-based answer for an active game.

        Args:
            channel_id: Discord channel ID where the message was sent.
            user_id: Discord user ID who sent the message.
            message: Discord message containing the answer.

        Returns:
            AnswerResult object if answer was processed, None if no active game or invalid answer.
        """
        try:
            # Check if there's an active game in this channel
            if channel_id not in self.active_games:
                logger.debug(f"No active game in channel {channel_id}")
                return None

            game_session = self.active_games[channel_id]

            # Process the text answer
            processed_answer = await self.answer_processor.process_text_answer(
                game_session.question, message
            )

            if processed_answer is None:
                logger.debug(f"Could not process text answer: {message.content}")
                return None

            # Validate and calculate result
            return await self._process_validated_answer(
                channel_id, user_id, processed_answer
            )

        except Exception as e:
            logger.error(
                f"Error processing text answer in channel {channel_id}: {e}",
                exc_info=True,
            )
            return None

    async def _process_validated_answer(
        self,
        channel_id: int,
        user_id: int,
        processed_answer: Any,
    ) -> Optional[AnswerResult]:
        """
        Process a validated answer and calculate the result.

        Args:
            channel_id: Discord channel ID.
            user_id: Discord user ID.
            processed_answer: The processed answer value.

        Returns:
            AnswerResult object.
        """
        try:
            game_session = self.active_games[channel_id]

            # Add user to participants
            game_session.participants.add(user_id)

            # Calculate time taken
            time_taken = (datetime.now() - game_session.start_time).total_seconds()

            # Validate the answer
            is_correct = await self.answer_processor.validate_answer(
                game_session.question, processed_answer
            )

            # Calculate points based on difficulty and time
            points_earned = 0
            if is_correct:
                base_points = game_session.question.point_value
                # Time bonus: lose 10% of points for every 5 seconds taken
                time_penalty = min(0.5, (time_taken / 5) * 0.1)  # Max 50% penalty
                points_earned = int(base_points * (1 - time_penalty))
                points_earned = max(1, points_earned)  # Minimum 1 point

            # Create answer result
            result = AnswerResult(
                is_correct=is_correct,
                points_earned=points_earned,
                time_taken=time_taken,
                explanation=game_session.question.explanation,
            )

            # End the game after processing the answer
            await self.end_game(channel_id, reason="answered")

            logger.info(
                f"Processed answer in channel {channel_id}: "
                f"user {user_id}, correct: {is_correct}, points: {points_earned}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Error processing validated answer in channel {channel_id}: {e}",
                exc_info=True,
            )
            return None

    async def end_game(self, channel_id: int, reason: str = "completed") -> None:
        """
        End an active game session.

        Args:
            channel_id: Discord channel ID of the game to end.
            reason: Reason for ending the game ("completed", "timeout", "cancelled").
        """
        try:
            if channel_id not in self.active_games:
                return

            game_session = self.active_games[channel_id]
            game_session.end_time = datetime.now()
            game_session.is_completed = True

            logger.info(f"Ending game in channel {channel_id}, reason: {reason}")

            # Cleanup the game
            await self._cleanup_game(channel_id)

        except Exception as e:
            logger.error(
                f"Error ending game in channel {channel_id}: {e}", exc_info=True
            )

    async def get_active_game(self, channel_id: int) -> Optional[GameSession]:
        """
        Get the active game session for a channel.

        Args:
            channel_id: Discord channel ID.

        Returns:
            GameSession object if active, None otherwise.
        """
        return self.active_games.get(channel_id)

    async def get_active_games_count(self) -> int:
        """
        Get the number of currently active games.

        Returns:
            Number of active games.
        """
        return len(self.active_games)

    async def get_active_channels(self) -> Set[int]:
        """
        Get set of channel IDs with active games.

        Returns:
            Set of channel IDs.
        """
        return set(self.active_games.keys())

    async def force_end_game(self, channel_id: int) -> bool:
        """
        Force end a game (admin function).

        Args:
            channel_id: Discord channel ID of the game to force end.

        Returns:
            True if game was ended, False if no active game.
        """
        if channel_id in self.active_games:
            await self.end_game(channel_id, reason="force_ended")
            return True
        return False

    async def cleanup_expired_games(self) -> int:
        """
        Clean up expired or abandoned games.

        Returns:
            Number of games cleaned up.
        """
        cleaned_count = 0
        current_time = datetime.now()
        expired_channels = []

        for channel_id, game_session in self.active_games.items():
            # Check if game has been running too long (default: 5 minutes max)
            max_duration = timedelta(minutes=5)
            if current_time - game_session.start_time > max_duration:
                expired_channels.append(channel_id)

        # Clean up expired games
        for channel_id in expired_channels:
            logger.info(f"Cleaning up expired game in channel {channel_id}")
            await self.end_game(channel_id, reason="expired")
            cleaned_count += 1

        return cleaned_count

    async def _start_game_timer(self, channel_id: int, timeout_duration: int) -> None:
        """
        Start the timer for a game session.

        Args:
            channel_id: Discord channel ID.
            timeout_duration: Timeout duration in seconds.
        """
        try:
            # Cancel existing timer if any
            if channel_id in self.game_timers:
                self.game_timers[channel_id].cancel()

            # Create and start new timer task
            timer_task = asyncio.create_task(
                self._game_timer_task(channel_id, timeout_duration)
            )
            self.game_timers[channel_id] = timer_task

        except Exception as e:
            logger.error(f"Error starting timer for channel {channel_id}: {e}")

    async def _game_timer_task(self, channel_id: int, timeout_duration: int) -> None:
        """
        Timer task that handles countdown and timeout for a game.

        Args:
            channel_id: Discord channel ID.
            timeout_duration: Timeout duration in seconds.
        """
        try:
            countdown_intervals = [20, 10]  # Send countdown at these remaining seconds

            for remaining in range(timeout_duration, 0, -1):
                await asyncio.sleep(1)

                # Check if game still exists
                if channel_id not in self.active_games:
                    return

                # Send countdown notification at specific intervals
                if remaining in countdown_intervals:
                    callback = self.countdown_callbacks.get(channel_id)
                    if callback:
                        try:
                            await callback(remaining)
                        except Exception as e:
                            logger.error(f"Error in countdown callback: {e}")

            # Game timed out
            if channel_id in self.active_games:
                logger.info(f"Game timed out in channel {channel_id}")

                # Call timeout callback
                callback = self.timeout_callbacks.get(channel_id)
                if callback:
                    try:
                        await callback()
                    except Exception as e:
                        logger.error(f"Error in timeout callback: {e}")

                # End the game
                await self.end_game(channel_id, reason="timeout")

        except asyncio.CancelledError:
            logger.debug(f"Timer cancelled for channel {channel_id}")
        except Exception as e:
            logger.error(f"Error in timer task for channel {channel_id}: {e}")

    async def _cleanup_game(self, channel_id: int) -> None:
        """
        Clean up all resources for a game session.

        Args:
            channel_id: Discord channel ID.
        """
        try:
            # Cancel timer if exists
            if channel_id in self.game_timers:
                self.game_timers[channel_id].cancel()
                del self.game_timers[channel_id]

            # Remove callbacks
            self.timeout_callbacks.pop(channel_id, None)
            self.countdown_callbacks.pop(channel_id, None)

            # Remove active game
            self.active_games.pop(channel_id, None)

            logger.debug(f"Cleaned up game resources for channel {channel_id}")

        except Exception as e:
            logger.error(f"Error cleaning up game for channel {channel_id}: {e}")

    async def _periodic_cleanup(self) -> None:
        """
        Periodic cleanup task that runs every 5 minutes.
        """
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                cleaned = await self.cleanup_expired_games()
                if cleaned > 0:
                    logger.info(f"Periodic cleanup: removed {cleaned} expired games")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    async def shutdown(self) -> None:
        """
        Shutdown the game manager and clean up all resources.
        """
        try:
            # Cancel cleanup task
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()

            # End all active games
            active_channels = list(self.active_games.keys())
            for channel_id in active_channels:
                await self.end_game(channel_id, reason="shutdown")

            # Cancel all timers
            for timer_task in self.game_timers.values():
                timer_task.cancel()

            self.game_timers.clear()
            self.timeout_callbacks.clear()
            self.countdown_callbacks.clear()

            logger.info("Game manager shutdown completed")

        except Exception as e:
            logger.error(f"Error during game manager shutdown: {e}")

    def get_expected_answer_format(self, channel_id: int) -> Optional[str]:
        """
        Get the expected answer format for an active game.

        Args:
            channel_id: Discord channel ID.

        Returns:
            String describing expected answer format, or None if no active game.
        """
        if channel_id not in self.active_games:
            return None

        game_session = self.active_games[channel_id]
        return self.answer_processor.get_expected_answer_format(game_session.question)

    def get_correct_answer_display(self, channel_id: int) -> Optional[str]:
        """
        Get a formatted display of the correct answer for an active game.

        Args:
            channel_id: Discord channel ID.

        Returns:
            Formatted correct answer string, or None if no active game.
        """
        if channel_id not in self.active_games:
            return None

        game_session = self.active_games[channel_id]
        return self.answer_processor.get_answer_display(game_session.question)

    def is_valid_reaction(self, channel_id: int, emoji_str: str) -> bool:
        """
        Check if a reaction is valid for the active game in a channel.

        Args:
            channel_id: Discord channel ID.
            emoji_str: String representation of the emoji.

        Returns:
            True if the reaction is valid for the current question.
        """
        if channel_id not in self.active_games:
            return False

        game_session = self.active_games[channel_id]
        return self.answer_processor.is_valid_reaction_for_question(
            game_session.question, emoji_str
        )

    def get_game_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active games.

        Returns:
            Dictionary containing game statistics.
        """
        stats = {
            "active_games": len(self.active_games),
            "active_timers": len(self.game_timers),
            "games_by_difficulty": {},
            "games_by_type": {"regular": 0, "challenge": 0},
        }

        for game_session in self.active_games.values():
            # Count by difficulty
            difficulty = game_session.difficulty or "unknown"
            stats["games_by_difficulty"][difficulty] = (
                stats["games_by_difficulty"].get(difficulty, 0) + 1
            )

            # Count by type
            if game_session.is_challenge:
                stats["games_by_type"]["challenge"] += 1
            else:
                stats["games_by_type"]["regular"] += 1

        return stats
