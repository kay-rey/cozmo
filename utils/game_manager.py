"""
Game Manager for the Enhanced Trivia System.
Handles game session tracking, timer management, and concurrent game support.
Enhanced with comprehensive error handling, Discord permission management, and cleanup mechanisms.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Any, Callable, Union, List
from utils.models import GameSession, Question, AnswerResult
from utils.question_engine import QuestionEngine
from utils.answer_processor import AnswerProcessor
import discord
from functools import wraps

logger = logging.getLogger(__name__)


class GameError(Exception):
    """Base exception for game-related errors."""

    pass


class GamePermissionError(GameError):
    """Exception raised when bot lacks required Discord permissions."""

    pass


class GameStateError(GameError):
    """Exception raised when game state is invalid or corrupted."""

    pass


class GameConcurrencyError(GameError):
    """Exception raised when concurrent game conflicts occur."""

    pass


def handle_game_errors(func: Callable):
    """Decorator to handle common game errors with user-friendly messages."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except discord.Forbidden as e:
            logger.error(f"Discord permission error in {func.__name__}: {e}")
            raise GamePermissionError(f"Missing Discord permissions: {e}")
        except discord.NotFound as e:
            logger.warning(f"Discord resource not found in {func.__name__}: {e}")
            # Clean up any related game state
            if hasattr(self, "_cleanup_on_not_found"):
                await self._cleanup_on_not_found(args, kwargs)
            raise GameError(f"Discord resource not found: {e}")
        except discord.HTTPException as e:
            logger.error(f"Discord HTTP error in {func.__name__}: {e}")
            raise GameError(f"Discord communication error: {e}")
        except asyncio.CancelledError:
            logger.debug(f"Operation cancelled in {func.__name__}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise GameError(f"Unexpected game error: {e}")

    return wrapper


class GameManager:
    """
    Manages trivia game sessions with timer support and concurrent game handling.
    Enhanced with comprehensive error handling, permission management, and cleanup mechanisms.
    """

    def __init__(
        self, question_engine: QuestionEngine, bot: Optional[discord.Client] = None
    ):
        """
        Initialize the Game Manager.

        Args:
            question_engine: QuestionEngine instance for question management.
            bot: Discord bot instance for permission checking.
        """
        self.question_engine = question_engine
        self.answer_processor = AnswerProcessor()
        self.bot = bot

        # Game state management
        self.active_games: Dict[int, GameSession] = {}  # channel_id -> GameSession
        self.game_timers: Dict[int, asyncio.Task] = {}  # channel_id -> timer task
        self.timeout_callbacks: Dict[
            int, Callable
        ] = {}  # channel_id -> callback function
        self.countdown_callbacks: Dict[
            int, Callable
        ] = {}  # channel_id -> countdown callback

        # Concurrency control
        self._game_locks: Dict[int, asyncio.Lock] = {}  # channel_id -> lock
        self._global_lock = asyncio.Lock()

        # Error tracking and recovery
        self._error_count = 0
        self._last_error_time: Optional[datetime] = None
        self._max_errors_per_hour = 50
        self._inaccessible_channels: Set[int] = set()
        self._channel_check_interval = timedelta(minutes=30)
        self._last_channel_check: Optional[datetime] = None

        # Cleanup and maintenance
        self._cleanup_task: Optional[asyncio.Task] = None
        self._maintenance_task: Optional[asyncio.Task] = None
        self._start_background_tasks()

    def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            if self._maintenance_task is None or self._maintenance_task.done():
                self._maintenance_task = asyncio.create_task(
                    self._periodic_maintenance()
                )
        except RuntimeError:
            # No event loop running, will start later when needed
            logger.debug("Background tasks will start when event loop is available")

    async def _get_channel_lock(self, channel_id: int) -> asyncio.Lock:
        """Get or create a lock for a specific channel to prevent race conditions."""
        async with self._global_lock:
            if channel_id not in self._game_locks:
                self._game_locks[channel_id] = asyncio.Lock()
            return self._game_locks[channel_id]

    async def _check_channel_permissions(self, channel_id: int) -> bool:
        """Check if bot has required permissions in a channel."""
        if not self.bot:
            return True  # Assume permissions are OK if no bot instance

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return False

            # Check required permissions
            permissions = channel.permissions_for(channel.guild.me)
            required_perms = [
                "send_messages",
                "embed_links",
                "add_reactions",
                "read_message_history",
                "use_external_emojis",
            ]

            missing_perms = [
                perm for perm in required_perms if not getattr(permissions, perm)
            ]

            if missing_perms:
                logger.warning(
                    f"Missing permissions in channel {channel_id}: {missing_perms}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking permissions for channel {channel_id}: {e}")
            return False

    def _record_error(self, error_type: str = "general"):
        """Record an error for monitoring and rate limiting."""
        current_time = datetime.now()
        self._error_count += 1
        self._last_error_time = current_time

        # Reset error count if it's been more than an hour
        if self._last_error_time and current_time - self._last_error_time > timedelta(
            hours=1
        ):
            self._error_count = 1

        # Log warning if error rate is high
        if self._error_count > self._max_errors_per_hour / 2:
            logger.warning(
                f"High error rate detected: {self._error_count} errors in the last hour"
            )

    async def _cleanup_on_not_found(self, args, kwargs):
        """Clean up game state when Discord resources are not found."""
        # Extract channel_id from args if possible
        channel_id = None
        if args and isinstance(args[0], int):
            channel_id = args[0]
        elif "channel_id" in kwargs:
            channel_id = kwargs["channel_id"]

        if channel_id:
            logger.info(f"Cleaning up game state for inaccessible channel {channel_id}")
            self._inaccessible_channels.add(channel_id)
            await self._cleanup_game(channel_id)

    async def _validate_game_state(self, channel_id: int) -> bool:
        """Validate that game state is consistent and accessible."""
        try:
            if channel_id not in self.active_games:
                return False

            game_session = self.active_games[channel_id]

            # Check if game has required attributes
            if not hasattr(game_session, "question") or not game_session.question:
                logger.warning(f"Game in channel {channel_id} missing question data")
                return False

            # Check if channel is accessible
            if channel_id in self._inaccessible_channels:
                logger.warning(f"Channel {channel_id} marked as inaccessible")
                return False

            # Check if game has been running too long
            max_duration = timedelta(minutes=10)  # Extended from 5 to 10 minutes
            if datetime.now() - game_session.start_time > max_duration:
                logger.warning(
                    f"Game in channel {channel_id} has been running too long"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating game state for channel {channel_id}: {e}")
            return False

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        except RuntimeError:
            # No event loop running, will start later when needed
            pass

    @handle_game_errors
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
        Start a new trivia game session with comprehensive error handling.

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

        Raises:
            GamePermissionError: If bot lacks required permissions.
            GameConcurrencyError: If there's a conflict with existing games.
            GameError: For other game-related errors.
        """
        # Use channel-specific lock to prevent race conditions
        channel_lock = await self._get_channel_lock(channel_id)

        async with channel_lock:
            try:
                # Check if channel is accessible and we have permissions
                if channel_id in self._inaccessible_channels:
                    raise GameError(f"Channel {channel_id} is currently inaccessible")

                if not await self._check_channel_permissions(channel_id):
                    self._inaccessible_channels.add(channel_id)
                    raise GamePermissionError(
                        "I don't have the required permissions in this channel. "
                        "Please ensure I can send messages, add reactions, and embed links."
                    )

                # Check if a game is already active in this channel
                if channel_id in self.active_games:
                    existing_game = self.active_games[channel_id]
                    # Check if existing game is still valid
                    if await self._validate_game_state(channel_id):
                        raise GameConcurrencyError(
                            f"A trivia game is already active in this channel. "
                            f"Started {(datetime.now() - existing_game.start_time).seconds} seconds ago."
                        )
                    else:
                        # Clean up invalid game state
                        logger.info(
                            f"Cleaning up invalid game state in channel {channel_id}"
                        )
                        await self._cleanup_game(channel_id)

                # Get a question from the question engine
                try:
                    question = await self.question_engine.get_question(
                        difficulty=difficulty
                    )
                    if not question:
                        raise GameError(
                            f"No questions available for difficulty '{difficulty or 'any'}'. "
                            "Please try again or contact an administrator."
                        )
                except Exception as e:
                    logger.error(f"Failed to get question: {e}")
                    raise GameError(
                        "Failed to load trivia question. Please try again in a moment."
                    )

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

                # Store callbacks with error handling wrappers
                if timeout_callback:
                    self.timeout_callbacks[channel_id] = self._wrap_callback(
                        timeout_callback, "timeout"
                    )
                if countdown_callback:
                    self.countdown_callbacks[channel_id] = self._wrap_callback(
                        countdown_callback, "countdown"
                    )

                # Ensure background tasks are running
                self._start_background_tasks()

                # Start the timer
                await self._start_game_timer(channel_id, timeout_duration)

                # Remove channel from inaccessible list if it was there
                self._inaccessible_channels.discard(channel_id)

                logger.info(
                    f"Started game in channel {channel_id} for user {user_id} "
                    f"with difficulty {question.difficulty}"
                )
                return game_session

            except (GameError, GamePermissionError, GameConcurrencyError):
                # Re-raise game-specific errors
                raise
            except Exception as e:
                self._record_error("start_game")
                logger.error(
                    f"Unexpected error starting game in channel {channel_id}: {e}",
                    exc_info=True,
                )
                # Cleanup on error
                await self._cleanup_game(channel_id)
                raise GameError(f"Failed to start trivia game: {str(e)}")

    def _wrap_callback(self, callback: Callable, callback_type: str) -> Callable:
        """Wrap callback functions with error handling."""

        async def wrapped_callback(*args, **kwargs):
            try:
                return await callback(*args, **kwargs)
            except discord.Forbidden as e:
                logger.error(f"Permission error in {callback_type} callback: {e}")
                # Don't re-raise, just log the error
            except discord.NotFound as e:
                logger.warning(f"Resource not found in {callback_type} callback: {e}")
                # Don't re-raise, just log the error
            except Exception as e:
                logger.error(f"Error in {callback_type} callback: {e}", exc_info=True)
                # Don't re-raise callback errors to avoid breaking game flow

        return wrapped_callback

    @handle_game_errors
    async def process_reaction_answer(
        self,
        channel_id: int,
        user_id: int,
        reaction: discord.Reaction,
        user: discord.User,
    ) -> Optional[AnswerResult]:
        """
        Process a reaction-based answer for an active game with error handling.

        Args:
            channel_id: Discord channel ID where the reaction was added.
            user_id: Discord user ID who reacted.
            reaction: Discord reaction object.
            user: Discord user object.

        Returns:
            AnswerResult object if answer was processed, None if no active game or invalid reaction.
        """
        # Use channel-specific lock to prevent race conditions
        channel_lock = await self._get_channel_lock(channel_id)

        async with channel_lock:
            try:
                # Check if there's an active game in this channel
                if channel_id not in self.active_games:
                    logger.debug(f"No active game in channel {channel_id}")
                    return None

                # Validate game state
                if not await self._validate_game_state(channel_id):
                    logger.warning(
                        f"Invalid game state in channel {channel_id}, cleaning up"
                    )
                    await self._cleanup_game(channel_id)
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
                try:
                    processed_answer = (
                        await self.answer_processor.process_reaction_answer(
                            game_session.question, reaction, user
                        )
                    )

                    if processed_answer is None:
                        logger.debug(f"Could not process reaction answer: {emoji_str}")
                        return None
                except Exception as e:
                    logger.error(f"Error processing reaction answer: {e}")
                    raise GameError("Failed to process your answer. Please try again.")

                # Validate and calculate result
                return await self._process_validated_answer(
                    channel_id, user_id, processed_answer
                )

            except (GameError, GamePermissionError):
                # Re-raise game-specific errors
                raise
            except Exception as e:
                self._record_error("process_reaction")
                logger.error(
                    f"Unexpected error processing reaction answer in channel {channel_id}: {e}",
                    exc_info=True,
                )
                # Clean up potentially corrupted game state
                await self._cleanup_game(channel_id)
                raise GameError("An error occurred while processing your answer.")

    @handle_game_errors
    async def process_text_answer(
        self,
        channel_id: int,
        user_id: int,
        message: discord.Message,
    ) -> Optional[AnswerResult]:
        """
        Process a text-based answer for an active game with error handling.

        Args:
            channel_id: Discord channel ID where the message was sent.
            user_id: Discord user ID who sent the message.
            message: Discord message containing the answer.

        Returns:
            AnswerResult object if answer was processed, None if no active game or invalid answer.
        """
        # Use channel-specific lock to prevent race conditions
        channel_lock = await self._get_channel_lock(channel_id)

        async with channel_lock:
            try:
                # Check if there's an active game in this channel
                if channel_id not in self.active_games:
                    logger.debug(f"No active game in channel {channel_id}")
                    return None

                # Validate game state
                if not await self._validate_game_state(channel_id):
                    logger.warning(
                        f"Invalid game state in channel {channel_id}, cleaning up"
                    )
                    await self._cleanup_game(channel_id)
                    return None

                game_session = self.active_games[channel_id]

                # Process the text answer
                try:
                    processed_answer = await self.answer_processor.process_text_answer(
                        game_session.question, message
                    )

                    if processed_answer is None:
                        logger.debug(
                            f"Could not process text answer: {message.content}"
                        )
                        return None
                except Exception as e:
                    logger.error(f"Error processing text answer: {e}")
                    raise GameError("Failed to process your answer. Please try again.")

                # Validate and calculate result
                return await self._process_validated_answer(
                    channel_id, user_id, processed_answer
                )

            except (GameError, GamePermissionError):
                # Re-raise game-specific errors
                raise
            except Exception as e:
                self._record_error("process_text")
                logger.error(
                    f"Unexpected error processing text answer in channel {channel_id}: {e}",
                    exc_info=True,
                )
                # Clean up potentially corrupted game state
                await self._cleanup_game(channel_id)
                raise GameError("An error occurred while processing your answer.")

    async def _process_validated_answer(
        self,
        channel_id: int,
        user_id: int,
        processed_answer: Any,
    ) -> Optional[AnswerResult]:
        """
        Process a validated answer and calculate the result with error handling.

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
            try:
                is_correct = await self.answer_processor.validate_answer(
                    game_session.question, processed_answer
                )
            except Exception as e:
                logger.error(f"Error validating answer: {e}")
                # Default to incorrect if validation fails
                is_correct = False

            # Calculate points based on difficulty and time
            points_earned = 0
            if is_correct:
                try:
                    base_points = (
                        game_session.question.point_value or 10
                    )  # Default to 10 if not set
                    # Time bonus: lose 10% of points for every 5 seconds taken
                    time_penalty = min(0.5, (time_taken / 5) * 0.1)  # Max 50% penalty
                    points_earned = int(base_points * (1 - time_penalty))
                    points_earned = max(1, points_earned)  # Minimum 1 point
                except Exception as e:
                    logger.error(f"Error calculating points: {e}")
                    points_earned = 1  # Default to 1 point

            # Create answer result
            result = AnswerResult(
                is_correct=is_correct,
                points_earned=points_earned,
                time_taken=time_taken,
                explanation=getattr(game_session.question, "explanation", None),
            )

            # End the game after processing the answer
            try:
                await self.end_game(channel_id, reason="answered")
            except Exception as e:
                logger.error(f"Error ending game after answer: {e}")
                # Still return the result even if cleanup fails
                await self._cleanup_game(channel_id)

            logger.info(
                f"Processed answer in channel {channel_id}: "
                f"user {user_id}, correct: {is_correct}, points: {points_earned}"
            )
            return result

        except Exception as e:
            self._record_error("process_validated_answer")
            logger.error(
                f"Error processing validated answer in channel {channel_id}: {e}",
                exc_info=True,
            )
            # Ensure game is cleaned up even on error
            await self._cleanup_game(channel_id)
            raise GameError("Failed to process your answer. The game has been ended.")

    async def end_game(self, channel_id: int, reason: str = "completed") -> None:
        """
        End an active game session with comprehensive cleanup.

        Args:
            channel_id: Discord channel ID of the game to end.
            reason: Reason for ending the game ("completed", "timeout", "cancelled", "error").
        """
        # Use channel-specific lock to prevent race conditions during cleanup
        channel_lock = await self._get_channel_lock(channel_id)

        async with channel_lock:
            try:
                if channel_id not in self.active_games:
                    logger.debug(f"No active game to end in channel {channel_id}")
                    return

                game_session = self.active_games[channel_id]

                # Update game session state
                try:
                    game_session.end_time = datetime.now()
                    game_session.is_completed = True
                except Exception as e:
                    logger.warning(f"Error updating game session state: {e}")

                logger.info(f"Ending game in channel {channel_id}, reason: {reason}")

                # Cleanup the game resources
                await self._cleanup_game(channel_id)

            except Exception as e:
                self._record_error("end_game")
                logger.error(
                    f"Error ending game in channel {channel_id}: {e}", exc_info=True
                )
                # Force cleanup even if there were errors
                try:
                    await self._cleanup_game(channel_id)
                except Exception as cleanup_error:
                    logger.error(f"Error during force cleanup: {cleanup_error}")

    async def force_end_all_games(self, reason: str = "shutdown") -> int:
        """
        Force end all active games (emergency cleanup).

        Args:
            reason: Reason for ending all games.

        Returns:
            Number of games that were ended.
        """
        ended_count = 0
        active_channels = list(self.active_games.keys())

        for channel_id in active_channels:
            try:
                await self.end_game(channel_id, reason)
                ended_count += 1
            except Exception as e:
                logger.error(f"Error force ending game in channel {channel_id}: {e}")
                # Continue with other games even if one fails

        logger.info(f"Force ended {ended_count} games, reason: {reason}")
        return ended_count

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
        Clean up expired, abandoned, or inaccessible games with comprehensive checks.

        Returns:
            Number of games cleaned up.
        """
        cleaned_count = 0
        current_time = datetime.now()
        expired_channels = []

        # Create a copy of active games to avoid modification during iteration
        active_games_copy = dict(self.active_games)

        for channel_id, game_session in active_games_copy.items():
            should_cleanup = False
            cleanup_reason = ""

            try:
                # Check if game has been running too long
                max_duration = timedelta(minutes=10)  # Extended from 5 to 10 minutes
                if current_time - game_session.start_time > max_duration:
                    should_cleanup = True
                    cleanup_reason = "expired"

                # Check if channel is marked as inaccessible
                elif channel_id in self._inaccessible_channels:
                    should_cleanup = True
                    cleanup_reason = "inaccessible"

                # Validate game state
                elif not await self._validate_game_state(channel_id):
                    should_cleanup = True
                    cleanup_reason = "invalid_state"

                # Check if game session is missing required data
                elif not hasattr(game_session, "question") or not game_session.question:
                    should_cleanup = True
                    cleanup_reason = "missing_data"

                if should_cleanup:
                    expired_channels.append((channel_id, cleanup_reason))

            except Exception as e:
                logger.error(f"Error checking game {channel_id} for cleanup: {e}")
                expired_channels.append((channel_id, "error"))

        # Clean up identified games
        for channel_id, reason in expired_channels:
            try:
                logger.info(
                    f"Cleaning up game in channel {channel_id}, reason: {reason}"
                )
                await self.end_game(channel_id, reason=f"cleanup_{reason}")
                cleaned_count += 1
            except Exception as e:
                logger.error(f"Error cleaning up game in channel {channel_id}: {e}")
                # Force cleanup if normal cleanup fails
                try:
                    await self._cleanup_game(channel_id)
                    cleaned_count += 1
                except Exception as force_error:
                    logger.error(
                        f"Force cleanup also failed for channel {channel_id}: {force_error}"
                    )

        return cleaned_count

    async def cleanup_inaccessible_channels(self) -> int:
        """
        Check and clean up channels that have become inaccessible.

        Returns:
            Number of channels cleaned up.
        """
        if not self.bot:
            return 0

        cleaned_count = 0
        channels_to_check = set(self.active_games.keys()) | self._inaccessible_channels

        for channel_id in list(channels_to_check):
            try:
                # Try to access the channel
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    # Channel not found, mark as inaccessible
                    self._inaccessible_channels.add(channel_id)
                    if channel_id in self.active_games:
                        await self.end_game(channel_id, reason="channel_not_found")
                        cleaned_count += 1
                    continue

                # Check permissions
                if not await self._check_channel_permissions(channel_id):
                    self._inaccessible_channels.add(channel_id)
                    if channel_id in self.active_games:
                        await self.end_game(
                            channel_id, reason="insufficient_permissions"
                        )
                        cleaned_count += 1
                else:
                    # Channel is accessible, remove from inaccessible list
                    self._inaccessible_channels.discard(channel_id)

            except Exception as e:
                logger.error(
                    f"Error checking accessibility of channel {channel_id}: {e}"
                )
                self._inaccessible_channels.add(channel_id)
                if channel_id in self.active_games:
                    await self.end_game(channel_id, reason="accessibility_error")
                    cleaned_count += 1

        return cleaned_count

    async def _start_game_timer(self, channel_id: int, timeout_duration: int) -> None:
        """
        Start the timer for a game session with error handling.

        Args:
            channel_id: Discord channel ID.
            timeout_duration: Timeout duration in seconds.
        """
        try:
            # Cancel existing timer if any
            if channel_id in self.game_timers:
                old_timer = self.game_timers[channel_id]
                if not old_timer.done():
                    old_timer.cancel()
                    try:
                        await old_timer
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.warning(
                            f"Error cancelling old timer for channel {channel_id}: {e}"
                        )

            # Create and start new timer task
            timer_task = asyncio.create_task(
                self._game_timer_task(channel_id, timeout_duration)
            )
            self.game_timers[channel_id] = timer_task

        except Exception as e:
            logger.error(f"Error starting timer for channel {channel_id}: {e}")
            # If timer fails to start, set a fallback cleanup
            asyncio.create_task(self._fallback_timer(channel_id, timeout_duration))

    async def _fallback_timer(self, channel_id: int, timeout_duration: int) -> None:
        """Fallback timer in case main timer fails."""
        try:
            await asyncio.sleep(timeout_duration + 10)  # Extra 10 seconds buffer
            if channel_id in self.active_games:
                logger.warning(f"Fallback timer triggered for channel {channel_id}")
                await self.end_game(channel_id, reason="fallback_timeout")
        except Exception as e:
            logger.error(f"Error in fallback timer for channel {channel_id}: {e}")

    async def _game_timer_task(self, channel_id: int, timeout_duration: int) -> None:
        """
        Timer task that handles countdown and timeout for a game with comprehensive error handling.

        Args:
            channel_id: Discord channel ID.
            timeout_duration: Timeout duration in seconds.
        """
        try:
            countdown_intervals = [20, 10]  # Send countdown at these remaining seconds
            last_check_time = datetime.now()

            for remaining in range(timeout_duration, 0, -1):
                try:
                    await asyncio.sleep(1)

                    # Periodic validation to ensure game is still valid
                    current_time = datetime.now()
                    if (
                        current_time - last_check_time
                    ).total_seconds() >= 10:  # Check every 10 seconds
                        if not await self._validate_game_state(channel_id):
                            logger.warning(
                                f"Game state invalid during timer for channel {channel_id}"
                            )
                            return
                        last_check_time = current_time

                    # Check if game still exists
                    if channel_id not in self.active_games:
                        logger.debug(
                            f"Game no longer exists during timer for channel {channel_id}"
                        )
                        return

                    # Send countdown notification at specific intervals
                    if remaining in countdown_intervals:
                        callback = self.countdown_callbacks.get(channel_id)
                        if callback:
                            try:
                                await callback(remaining)
                            except discord.Forbidden:
                                logger.warning(
                                    f"Permission error in countdown callback for channel {channel_id}"
                                )
                                # Mark channel as inaccessible and end game
                                self._inaccessible_channels.add(channel_id)
                                await self.end_game(
                                    channel_id, reason="permission_error"
                                )
                                return
                            except discord.NotFound:
                                logger.warning(
                                    f"Resource not found in countdown callback for channel {channel_id}"
                                )
                                # Channel or message was deleted, end game
                                await self.end_game(
                                    channel_id, reason="resource_not_found"
                                )
                                return
                            except Exception as e:
                                logger.error(
                                    f"Error in countdown callback for channel {channel_id}: {e}"
                                )
                                # Continue timer despite callback error

                except asyncio.CancelledError:
                    logger.debug(f"Timer cancelled for channel {channel_id}")
                    return
                except Exception as e:
                    logger.error(f"Error in timer loop for channel {channel_id}: {e}")
                    # Continue the timer unless it's a critical error
                    if isinstance(e, (discord.Forbidden, discord.NotFound)):
                        await self.end_game(channel_id, reason="timer_error")
                        return

            # Game timed out normally
            if channel_id in self.active_games:
                logger.info(f"Game timed out in channel {channel_id}")

                # Call timeout callback
                callback = self.timeout_callbacks.get(channel_id)
                if callback:
                    try:
                        await callback()
                    except discord.Forbidden:
                        logger.warning(
                            f"Permission error in timeout callback for channel {channel_id}"
                        )
                        self._inaccessible_channels.add(channel_id)
                    except discord.NotFound:
                        logger.warning(
                            f"Resource not found in timeout callback for channel {channel_id}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error in timeout callback for channel {channel_id}: {e}"
                        )

                # End the game
                await self.end_game(channel_id, reason="timeout")

        except asyncio.CancelledError:
            logger.debug(f"Timer cancelled for channel {channel_id}")
        except Exception as e:
            self._record_error("timer_task")
            logger.error(
                f"Critical error in timer task for channel {channel_id}: {e}",
                exc_info=True,
            )
            # Ensure game is cleaned up even if timer fails
            try:
                await self.end_game(channel_id, reason="timer_error")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up after timer failure: {cleanup_error}")

    async def _cleanup_game(self, channel_id: int) -> None:
        """
        Clean up all resources for a game session with comprehensive error handling.

        Args:
            channel_id: Discord channel ID.
        """
        cleanup_errors = []

        try:
            # Cancel timer if exists
            if channel_id in self.game_timers:
                timer_task = self.game_timers[channel_id]
                try:
                    if not timer_task.done():
                        timer_task.cancel()
                        # Wait for cancellation to complete
                        try:
                            await timer_task
                        except asyncio.CancelledError:
                            pass
                except Exception as e:
                    cleanup_errors.append(f"timer cancellation: {e}")
                finally:
                    self.game_timers.pop(channel_id, None)

            # Remove callbacks
            try:
                self.timeout_callbacks.pop(channel_id, None)
                self.countdown_callbacks.pop(channel_id, None)
            except Exception as e:
                cleanup_errors.append(f"callback removal: {e}")

            # Remove active game
            try:
                self.active_games.pop(channel_id, None)
            except Exception as e:
                cleanup_errors.append(f"game removal: {e}")

            # Clean up channel lock if no longer needed
            try:
                async with self._global_lock:
                    if (
                        channel_id in self._game_locks
                        and channel_id not in self.active_games
                    ):
                        self._game_locks.pop(channel_id, None)
            except Exception as e:
                cleanup_errors.append(f"lock cleanup: {e}")

            if cleanup_errors:
                logger.warning(
                    f"Cleanup errors for channel {channel_id}: {'; '.join(cleanup_errors)}"
                )
            else:
                logger.debug(
                    f"Successfully cleaned up game resources for channel {channel_id}"
                )

        except Exception as e:
            logger.error(
                f"Critical error cleaning up game for channel {channel_id}: {e}",
                exc_info=True,
            )

    async def _periodic_maintenance(self) -> None:
        """
        Periodic maintenance task for health monitoring and cleanup.
        """
        while True:
            try:
                await asyncio.sleep(1800)  # 30 minutes

                logger.debug("Starting periodic game manager maintenance")

                # Clean up expired games
                expired_count = await self.cleanup_expired_games()

                # Clean up inaccessible channels
                inaccessible_count = await self.cleanup_inaccessible_channels()

                # Reset error count if it's been more than an hour
                if (
                    self._last_error_time
                    and datetime.now() - self._last_error_time > timedelta(hours=1)
                ):
                    self._error_count = 0

                # Log maintenance summary
                if expired_count > 0 or inaccessible_count > 0:
                    logger.info(
                        f"Maintenance completed: {expired_count} expired games, "
                        f"{inaccessible_count} inaccessible channels cleaned up"
                    )

                # Update last channel check time
                self._last_channel_check = datetime.now()

            except asyncio.CancelledError:
                logger.info("Periodic maintenance task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic maintenance: {e}", exc_info=True)
                # Continue running despite errors

    async def _periodic_cleanup(self) -> None:
        """
        Periodic cleanup task that runs every 5 minutes with enhanced error handling.
        """
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes

                # Perform cleanup operations
                cleaned = await self.cleanup_expired_games()

                # Additional cleanup for error recovery
                if (
                    self._error_count > self._max_errors_per_hour / 4
                ):  # If error rate is high
                    logger.warning(
                        "High error rate detected, performing additional cleanup"
                    )
                    inaccessible_cleaned = await self.cleanup_inaccessible_channels()
                    cleaned += inaccessible_cleaned

                if cleaned > 0:
                    logger.info(f"Periodic cleanup: removed {cleaned} games/channels")

            except asyncio.CancelledError:
                logger.info("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}", exc_info=True)
                # Continue running despite errors

    async def shutdown(self) -> None:
        """
        Shutdown the game manager and clean up all resources with comprehensive error handling.
        """
        logger.info("Starting game manager shutdown")
        shutdown_errors = []

        try:
            # Cancel background tasks
            tasks_to_cancel = []
            if self._cleanup_task and not self._cleanup_task.done():
                tasks_to_cancel.append(("cleanup", self._cleanup_task))
            if self._maintenance_task and not self._maintenance_task.done():
                tasks_to_cancel.append(("maintenance", self._maintenance_task))

            for task_name, task in tasks_to_cancel:
                try:
                    task.cancel()
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    shutdown_errors.append(f"{task_name} task: {e}")

            # End all active games
            ended_count = await self.force_end_all_games("shutdown")
            logger.info(f"Ended {ended_count} active games during shutdown")

            # Cancel all remaining timers
            timer_errors = 0
            for channel_id, timer_task in list(self.game_timers.items()):
                try:
                    if not timer_task.done():
                        timer_task.cancel()
                        await timer_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    timer_errors += 1
                    logger.debug(
                        f"Error cancelling timer for channel {channel_id}: {e}"
                    )

            if timer_errors > 0:
                shutdown_errors.append(f"{timer_errors} timer cancellation errors")

            # Clear all data structures
            try:
                self.game_timers.clear()
                self.timeout_callbacks.clear()
                self.countdown_callbacks.clear()
                self.active_games.clear()
                self._game_locks.clear()
                self._inaccessible_channels.clear()
            except Exception as e:
                shutdown_errors.append(f"data structure cleanup: {e}")

            if shutdown_errors:
                logger.warning(
                    f"Game manager shutdown completed with errors: {'; '.join(shutdown_errors)}"
                )
            else:
                logger.info("Game manager shutdown completed successfully")

        except Exception as e:
            logger.error(
                f"Critical error during game manager shutdown: {e}", exc_info=True
            )

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
        Get comprehensive statistics about active games and system health.

        Returns:
            Dictionary containing game statistics and health information.
        """
        try:
            stats = {
                "active_games": len(self.active_games),
                "active_timers": len(self.game_timers),
                "games_by_difficulty": {},
                "games_by_type": {"regular": 0, "challenge": 0},
                "error_tracking": {
                    "error_count": self._error_count,
                    "last_error_time": self._last_error_time.isoformat()
                    if self._last_error_time
                    else None,
                    "max_errors_per_hour": self._max_errors_per_hour,
                },
                "channel_health": {
                    "inaccessible_channels": len(self._inaccessible_channels),
                    "last_channel_check": self._last_channel_check.isoformat()
                    if self._last_channel_check
                    else None,
                },
                "background_tasks": {
                    "cleanup_task_running": self._cleanup_task
                    and not self._cleanup_task.done(),
                    "maintenance_task_running": self._maintenance_task
                    and not self._maintenance_task.done(),
                },
            }

            # Analyze active games
            game_durations = []
            for game_session in self.active_games.values():
                try:
                    # Count by difficulty
                    difficulty = (
                        getattr(game_session, "difficulty", "unknown") or "unknown"
                    )
                    stats["games_by_difficulty"][difficulty] = (
                        stats["games_by_difficulty"].get(difficulty, 0) + 1
                    )

                    # Count by type
                    if getattr(game_session, "is_challenge", False):
                        stats["games_by_type"]["challenge"] += 1
                    else:
                        stats["games_by_type"]["regular"] += 1

                    # Track game duration
                    if hasattr(game_session, "start_time"):
                        duration = (
                            datetime.now() - game_session.start_time
                        ).total_seconds()
                        game_durations.append(duration)

                except Exception as e:
                    logger.debug(f"Error analyzing game session: {e}")

            # Add duration statistics
            if game_durations:
                stats["game_durations"] = {
                    "average_seconds": sum(game_durations) / len(game_durations),
                    "max_seconds": max(game_durations),
                    "min_seconds": min(game_durations),
                }

            return stats

        except Exception as e:
            logger.error(f"Error generating game stats: {e}")
            return {
                "error": str(e),
                "active_games": len(self.active_games)
                if hasattr(self, "active_games")
                else 0,
            }

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of the game manager.

        Returns:
            Dictionary containing health status information.
        """
        try:
            health = {"status": "unknown", "issues": [], "recommendations": []}

            # Check error rate
            if self._error_count > self._max_errors_per_hour:
                health["issues"].append(f"High error rate: {self._error_count} errors")
                health["recommendations"].append("Check logs and restart if necessary")

            # Check inaccessible channels
            if len(self._inaccessible_channels) > 0:
                health["issues"].append(
                    f"{len(self._inaccessible_channels)} inaccessible channels"
                )
                health["recommendations"].append(
                    "Check bot permissions in affected channels"
                )

            # Check background tasks
            if not (self._cleanup_task and not self._cleanup_task.done()):
                health["issues"].append("Cleanup task not running")
                health["recommendations"].append("Restart background tasks")

            if not (self._maintenance_task and not self._maintenance_task.done()):
                health["issues"].append("Maintenance task not running")
                health["recommendations"].append("Restart background tasks")

            # Check for stuck games
            stuck_games = 0
            current_time = datetime.now()
            for game_session in self.active_games.values():
                if hasattr(game_session, "start_time"):
                    duration = current_time - game_session.start_time
                    if duration > timedelta(
                        minutes=15
                    ):  # Games running longer than 15 minutes
                        stuck_games += 1

            if stuck_games > 0:
                health["issues"].append(f"{stuck_games} potentially stuck games")
                health["recommendations"].append("Run cleanup to remove stuck games")

            # Determine overall status
            if not health["issues"]:
                health["status"] = "healthy"
            elif len(health["issues"]) <= 2:
                health["status"] = "warning"
            else:
                health["status"] = "critical"

            return health

        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                "status": "error",
                "issues": [f"Health check failed: {e}"],
                "recommendations": ["Check game manager logs"],
            }
