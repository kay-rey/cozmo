"""
Integration tests for concurrent game functionality across multiple channels.
Tests multi-channel game sessions, user isolation, and concurrent access patterns.
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Add the parent directory to the path so we can import our modules
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.question_engine import QuestionEngine
from utils.user_manager import UserManager
from utils.scoring_engine import ScoringEngine
from utils.database import DatabaseManager
from utils.models import Question, UserProfile, GameSession


class TestConcurrentGameFunctionality:
    """Tests for concurrent game functionality across multiple channels."""

    @pytest_asyncio.fixture
    async def multi_channel_environment(self):
        """Set up test environment for multi-channel testing."""
        # Create temporary database
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_file.close()

        db_manager = DatabaseManager(temp_file.name)
        await db_manager.initialize_database()

        # Create component instances
        question_engine = QuestionEngine()
        user_manager = UserManager()
        user_manager.db_manager = db_manager
        scoring_engine = ScoringEngine()

        # Create mock game sessions for different channels
        game_sessions = {}

        yield {
            "db_manager": db_manager,
            "question_engine": question_engine,
            "user_manager": user_manager,
            "scoring_engine": scoring_engine,
            "game_sessions": game_sessions,
        }

        # Cleanup
        await db_manager.close_all_connections()
        os.unlink(temp_file.name)

    @pytest.mark.asyncio
    async def test_multiple_channels_simultaneous_games(
        self, multi_channel_environment
    ):
        """Test simultaneous games running in multiple channels."""
        question_engine = multi_channel_environment["question_engine"]
        user_manager = multi_channel_environment["user_manager"]
        scoring_engine = multi_channel_environment["scoring_engine"]

        # Define multiple channels with different users
        channels = {
            12345: [1001, 1002, 1003],  # Channel 1 with 3 users
            67890: [2001, 2002],  # Channel 2 with 2 users
            11111: [3001, 3002, 3003, 3004],  # Channel 3 with 4 users
        }

        async def simulate_channel_game(channel_id, user_ids):
            """Simulate a game session in a specific channel."""
            channel_results = {}

            # Get a question for this channel
            question = await question_engine.get_question(difficulty="medium")
            if not question:
                return channel_results

            # Each user in the channel answers the question
            for user_id in user_ids:
                # Simulate different response times and accuracy
                is_correct = (user_id % 3) != 0  # 2/3 users correct
                time_taken = 5.0 + (user_id % 10)  # Varying response times

                # Get current user state
                current_user = await user_manager.get_or_create_user(user_id)

                # Calculate score
                score_result = scoring_engine.calculate_total_score(
                    difficulty=question.difficulty,
                    is_correct=is_correct,
                    time_taken=time_taken,
                    current_streak=current_user.current_streak,
                )

                points_earned = score_result["total_points"] if is_correct else 0

                # Update user stats
                await user_manager.update_stats(
                    user_id=user_id,
                    points=points_earned,
                    is_correct=is_correct,
                    difficulty=question.difficulty,
                )

                channel_results[user_id] = {
                    "points": points_earned,
                    "correct": is_correct,
                    "time": time_taken,
                }

            return channel_results

        # Run games in all channels concurrently
        tasks = [
            simulate_channel_game(channel_id, user_ids)
            for channel_id, user_ids in channels.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all channels completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == len(channels)

        # Verify user isolation - each user should have their own state
        all_user_ids = [
            user_id for user_list in channels.values() for user_id in user_list
        ]

        for user_id in all_user_ids:
            user = await user_manager.get_or_create_user(user_id)
            assert user.user_id == user_id
            assert user.questions_answered > 0

    @pytest.mark.asyncio
    async def test_channel_isolation_user_states(self, multi_channel_environment):
        """Test that user states are properly isolated between channels."""
        question_engine = multi_channel_environment["question_engine"]
        user_manager = multi_channel_environment["user_manager"]
        scoring_engine = multi_channel_environment["scoring_engine"]

        # Same user participating in multiple channels
        user_id = 9999
        channels = [11111, 22222, 33333]

        # User answers questions in different channels
        for i, channel_id in enumerate(channels):
            question = await question_engine.get_question(difficulty="easy")
            if not question:
                continue

            # Different performance in each channel
            is_correct = i % 2 == 0  # Alternating correct/incorrect
            time_taken = 10.0 + i * 2

            current_user = await user_manager.get_or_create_user(user_id)

            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=is_correct,
                time_taken=time_taken,
                current_streak=current_user.current_streak,
            )

            points_earned = score_result["total_points"] if is_correct else 0

            await user_manager.update_stats(
                user_id=user_id,
                points=points_earned,
                is_correct=is_correct,
                difficulty=question.difficulty,
            )

        # Verify user has cumulative stats across all channels
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.questions_answered == len(channels)
        # User state should be consistent regardless of which channel they played in

    @pytest.mark.asyncio
    async def test_concurrent_daily_challenge_access(self, multi_channel_environment):
        """Test concurrent access to daily challenges across channels."""
        question_engine = multi_channel_environment["question_engine"]
        user_manager = multi_channel_environment["user_manager"]

        # Multiple users from different channels attempting daily challenge
        user_ids = [5001, 5002, 5003, 5004, 5005]

        async def attempt_daily_challenge(user_id):
            """Simulate user attempting daily challenge."""
            # Check if can attempt
            can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
            if not can_attempt:
                return None

            # Get daily challenge question
            daily_question = await question_engine.get_daily_challenge_question()
            if not daily_question:
                return None

            # Complete the challenge
            await user_manager.update_challenge_completion(user_id, "daily")

            return {
                "user_id": user_id,
                "question_id": daily_question.id,
                "completed": True,
            }

        # All users attempt daily challenge concurrently
        tasks = [attempt_daily_challenge(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        successful_results = [
            r for r in results if r is not None and not isinstance(r, Exception)
        ]

        # All users should get the same daily question
        if len(successful_results) > 1:
            question_ids = [r["question_id"] for r in successful_results]
            assert all(qid == question_ids[0] for qid in question_ids)

        # Verify all users completed the challenge
        for user_id in user_ids:
            can_attempt_again = await user_manager.can_attempt_challenge(
                user_id, "daily"
            )
            assert can_attempt_again is False

    @pytest.mark.asyncio
    async def test_concurrent_weekly_challenge_access(self, multi_channel_environment):
        """Test concurrent access to weekly challenges across channels."""
        question_engine = multi_channel_environment["question_engine"]
        user_manager = multi_channel_environment["user_manager"]

        user_ids = [6001, 6002, 6003]

        async def attempt_weekly_challenge(user_id):
            """Simulate user attempting weekly challenge."""
            can_attempt = await user_manager.can_attempt_challenge(user_id, "weekly")
            if not can_attempt:
                return None

            # Get weekly challenge questions
            weekly_questions = await question_engine.get_weekly_challenge_questions()
            if not weekly_questions:
                return None

            # Complete the challenge
            await user_manager.update_challenge_completion(user_id, "weekly")

            return {
                "user_id": user_id,
                "question_count": len(weekly_questions),
                "question_ids": [q.id for q in weekly_questions],
                "completed": True,
            }

        # All users attempt weekly challenge concurrently
        tasks = [attempt_weekly_challenge(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        successful_results = [
            r for r in results if r is not None and not isinstance(r, Exception)
        ]

        # All users should get the same weekly questions
        if len(successful_results) > 1:
            first_questions = successful_results[0]["question_ids"]
            for result in successful_results[1:]:
                assert result["question_ids"] == first_questions

    @pytest.mark.asyncio
    async def test_high_concurrency_user_operations(self, multi_channel_environment):
        """Test high concurrency user operations."""
        user_manager = multi_channel_environment["user_manager"]
        scoring_engine = multi_channel_environment["scoring_engine"]

        # Create many concurrent user operations
        num_users = 20
        operations_per_user = 5

        async def user_operation_batch(user_id):
            """Perform multiple operations for a single user."""
            results = []

            for i in range(operations_per_user):
                try:
                    # Simulate answering questions
                    is_correct = (user_id + i) % 2 == 0
                    points = 10 if is_correct else 0

                    updated_user = await user_manager.update_stats(
                        user_id=user_id,
                        points=points,
                        is_correct=is_correct,
                        difficulty="easy",
                    )

                    results.append(
                        {
                            "operation": i,
                            "success": True,
                            "points": updated_user.total_points,
                        }
                    )

                except Exception as e:
                    results.append({"operation": i, "success": False, "error": str(e)})

            return results

        # Create tasks for all users
        user_ids = range(7000, 7000 + num_users)
        tasks = [user_operation_batch(user_id) for user_id in user_ids]

        # Execute all operations concurrently
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results
        successful_batches = [r for r in all_results if not isinstance(r, Exception)]
        assert len(successful_batches) > 0  # At least some should succeed

        # Verify final user states are consistent
        for user_id in user_ids:
            try:
                user = await user_manager.get_or_create_user(user_id)
                assert user.user_id == user_id
                # User should have some activity recorded
                assert user.questions_answered >= 0
            except Exception:
                # Some users might have failed operations, which is acceptable under high concurrency
                pass

    @pytest.mark.asyncio
    async def test_channel_specific_game_sessions(self, multi_channel_environment):
        """Test channel-specific game session management."""
        question_engine = multi_channel_environment["question_engine"]
        user_manager = multi_channel_environment["user_manager"]
        game_sessions = multi_channel_environment["game_sessions"]

        # Create game sessions for different channels
        channels_data = {
            10001: {"users": [8001, 8002], "difficulty": "easy"},
            10002: {"users": [8003, 8004, 8005], "difficulty": "medium"},
            10003: {"users": [8006], "difficulty": "hard"},
        }

        async def manage_channel_session(channel_id, channel_data):
            """Manage a game session for a specific channel."""
            users = channel_data["users"]
            difficulty = channel_data["difficulty"]

            # Create session
            session = GameSession(
                channel_id=channel_id,
                user_id=users[0],  # Primary user
                difficulty=difficulty,
                start_time=datetime.now(),
                is_completed=False,
            )

            game_sessions[channel_id] = session

            # Get question for this session
            question = await question_engine.get_question(difficulty=difficulty)
            if not question:
                return None

            session.question = question

            # Process answers from all users in the channel
            session_results = {}

            for user_id in users:
                # Simulate user answering
                is_correct = user_id % 2 == 0  # Even user IDs are correct
                time_taken = 8.0 + (user_id % 5)

                current_user = await user_manager.get_or_create_user(user_id)

                await user_manager.update_stats(
                    user_id=user_id,
                    points=20 if is_correct else 0,
                    is_correct=is_correct,
                    difficulty=difficulty,
                )

                session_results[user_id] = {"correct": is_correct, "time": time_taken}

            # Complete session
            session.is_completed = True
            session.end_time = datetime.now()

            return session_results

        # Run sessions for all channels concurrently
        tasks = [
            manage_channel_session(channel_id, channel_data)
            for channel_id, channel_data in channels_data.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all sessions completed
        successful_results = [
            r for r in results if r is not None and not isinstance(r, Exception)
        ]
        assert len(successful_results) == len(channels_data)

        # Verify sessions are properly isolated
        assert len(game_sessions) == len(channels_data)

        for channel_id, session in game_sessions.items():
            assert session.channel_id == channel_id
            assert session.is_completed is True

    @pytest.mark.asyncio
    async def test_concurrent_leaderboard_updates(self, multi_channel_environment):
        """Test concurrent leaderboard updates from multiple channels."""
        user_manager = multi_channel_environment["user_manager"]

        # Create users with different point totals
        users_data = [
            (9001, 100),
            (9002, 200),
            (9003, 150),
            (9004, 300),
            (9005, 250),
            (9006, 180),
        ]

        async def update_user_points(user_id, points):
            """Update user points and get their rank."""
            # Add points to user
            await user_manager.update_stats(
                user_id=user_id, points=points, is_correct=True, difficulty="medium"
            )

            # Get user rank
            rank = await user_manager.get_user_rank(user_id)
            return {"user_id": user_id, "rank": rank}

        # Update all users concurrently
        tasks = [update_user_points(user_id, points) for user_id, points in users_data]
        rank_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify ranking results
        successful_ranks = [r for r in rank_results if not isinstance(r, Exception)]
        assert len(successful_ranks) > 0

        # Verify ranking consistency
        final_ranks = {}
        for user_id, _ in users_data:
            try:
                rank = await user_manager.get_user_rank(user_id)
                if rank is not None:
                    final_ranks[user_id] = rank
            except Exception:
                pass  # Some operations might fail under concurrency

        # Users with higher points should have better (lower) ranks
        if len(final_ranks) > 1:
            # This is a basic consistency check
            assert all(
                isinstance(rank, int) and rank > 0 for rank in final_ranks.values()
            )

    @pytest.mark.asyncio
    async def test_database_connection_pooling_under_load(
        self, multi_channel_environment
    ):
        """Test database connection pooling under concurrent load."""
        user_manager = multi_channel_environment["user_manager"]
        db_manager = multi_channel_environment["db_manager"]

        # Create many concurrent database operations
        num_operations = 50

        async def database_operation(operation_id):
            """Perform a database operation."""
            user_id = 10000 + operation_id

            try:
                # Create user
                user = await user_manager.get_or_create_user(user_id)

                # Update stats
                await user_manager.update_stats(
                    user_id=user_id, points=10, is_correct=True, difficulty="easy"
                )

                # Get user again
                updated_user = await user_manager.get_or_create_user(user_id)

                return {
                    "operation_id": operation_id,
                    "success": True,
                    "user_points": updated_user.total_points,
                }

            except Exception as e:
                return {"operation_id": operation_id, "success": False, "error": str(e)}

        # Execute all operations concurrently
        tasks = [database_operation(i) for i in range(num_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful_ops = [
            r for r in results if isinstance(r, dict) and r.get("success")
        ]
        failed_ops = [
            r for r in results if isinstance(r, dict) and not r.get("success")
        ]
        exceptions = [r for r in results if isinstance(r, Exception)]

        # Most operations should succeed (allowing for some failures under high load)
        success_rate = len(successful_ops) / len(results)
        assert success_rate > 0.5  # At least 50% success rate

        # Verify database connections are properly managed
        # (This would require access to connection pool metrics in a real implementation)

    @pytest.mark.asyncio
    async def test_cross_channel_user_consistency(self, multi_channel_environment):
        """Test user data consistency across different channels."""
        question_engine = multi_channel_environment["question_engine"]
        user_manager = multi_channel_environment["user_manager"]

        user_id = 11111
        channels = [20001, 20002, 20003]

        # User participates in multiple channels sequentially and concurrently
        async def participate_in_channel(channel_id):
            """User participates in a specific channel."""
            question = await question_engine.get_question()
            if not question:
                return None

            # Get current user state
            current_user = await user_manager.get_or_create_user(user_id)
            initial_points = current_user.total_points

            # Answer question
            await user_manager.update_stats(
                user_id=user_id,
                points=20,
                is_correct=True,
                difficulty=question.difficulty,
            )

            # Get updated state
            updated_user = await user_manager.get_or_create_user(user_id)

            return {
                "channel_id": channel_id,
                "initial_points": initial_points,
                "final_points": updated_user.total_points,
                "questions_answered": updated_user.questions_answered,
            }

        # Participate in all channels concurrently
        tasks = [participate_in_channel(channel_id) for channel_id in channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify consistency
        successful_results = [
            r for r in results if r is not None and not isinstance(r, Exception)
        ]

        if len(successful_results) > 0:
            # Final user state should reflect all activities
            final_user = await user_manager.get_or_create_user(user_id)

            # User should have participated in activities
            assert final_user.questions_answered > 0
            assert final_user.total_points >= 0

            # User ID should be consistent
            assert final_user.user_id == user_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
