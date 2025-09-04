"""
Integration tests for the leaderboard system.
Tests leaderboard functionality, ranking calculations, and command interactions.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Add the parent directory to the path so we can import our modules
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.leaderboard_manager import LeaderboardManager
from utils.database import DatabaseManager
from utils.user_manager import UserManager
from utils.models import UserProfile, LeaderboardEntry
from cogs.leaderboard_commands import LeaderboardCommands


class TestLeaderboardManager:
    """Test the LeaderboardManager class functionality."""

    @pytest_asyncio.fixture
    async def setup_test_db(self):
        """Set up a test database with sample data."""
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        db_manager = DatabaseManager(temp_db.name)
        await db_manager.initialize_database()

        # Create test users with different scores
        test_users = [
            (
                1001,
                1000,
                50,
                45,
                5,
                8,
            ),  # user_id, total_points, answered, correct, current_streak, best_streak
            (1002, 800, 40, 32, 3, 6),
            (1003, 1200, 60, 54, 7, 10),
            (1004, 600, 30, 24, 2, 4),
            (1005, 900, 45, 36, 4, 7),
        ]

        async with db_manager.get_connection() as conn:
            for user_data in test_users:
                await conn.execute(
                    """
                    INSERT INTO users (user_id, total_points, questions_answered, 
                                     questions_correct, current_streak, best_streak, last_played)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*user_data, datetime.now()),
                )
            await conn.commit()

        yield db_manager, temp_db.name

        # Cleanup
        await db_manager.close_all_connections()
        os.unlink(temp_db.name)

    @pytest.mark.asyncio
    async def test_all_time_leaderboard(self, setup_test_db):
        """Test all-time leaderboard functionality."""
        db_manager, db_path = setup_test_db

        leaderboard_manager = LeaderboardManager()
        leaderboard_manager.db_manager = db_manager

        # Get all-time leaderboard
        entries = await leaderboard_manager.get_leaderboard("all_time", limit=5)

        assert len(entries) == 5
        assert entries[0].user_id == 1003  # Highest points (1200)
        assert entries[0].rank == 1
        assert entries[0].total_points == 1200

        assert entries[1].user_id == 1001  # Second highest (1000)
        assert entries[1].rank == 2

        # Verify ranking order
        for i in range(len(entries) - 1):
            assert entries[i].total_points >= entries[i + 1].total_points

    @pytest.mark.asyncio
    async def test_user_rank_calculation(self, setup_test_db):
        """Test user rank calculation."""
        db_manager, db_path = setup_test_db

        leaderboard_manager = LeaderboardManager()
        leaderboard_manager.db_manager = db_manager

        # Test user rank for different users
        rank_info = await leaderboard_manager.get_user_rank(1003, "all_time")
        assert rank_info == (1, 5)  # Rank 1 out of 5 users

        rank_info = await leaderboard_manager.get_user_rank(1001, "all_time")
        assert rank_info == (2, 5)  # Rank 2 out of 5 users

        rank_info = await leaderboard_manager.get_user_rank(1004, "all_time")
        assert rank_info == (5, 5)  # Rank 5 out of 5 users

    @pytest.mark.asyncio
    async def test_weekly_rankings_update(self, setup_test_db):
        """Test weekly rankings calculation and updates."""
        db_manager, db_path = setup_test_db

        leaderboard_manager = LeaderboardManager()
        leaderboard_manager.db_manager = db_manager

        # Add some game sessions for this week
        async with db_manager.get_connection() as conn:
            # Add questions first
            await conn.execute(
                """
                INSERT INTO questions (question_text, question_type, difficulty, category, correct_answer, point_value)
                VALUES ('Test question', 'multiple_choice', 'medium', 'general', 'answer', 20)
                """
            )

            # Add game sessions for current week
            current_date = datetime.now()
            await conn.execute(
                """
                INSERT INTO game_sessions (channel_id, user_id, question_id, is_completed, end_time)
                VALUES (?, ?, 1, 1, ?)
                """,
                (12345, 1001, current_date),
            )
            await conn.execute(
                """
                INSERT INTO game_sessions (channel_id, user_id, question_id, is_completed, end_time)
                VALUES (?, ?, 1, 1, ?)
                """,
                (12345, 1002, current_date),
            )
            await conn.commit()

        # Update weekly rankings
        await leaderboard_manager.update_weekly_rankings()

        # Get weekly leaderboard
        weekly_entries = await leaderboard_manager.get_leaderboard("weekly", limit=5)

        # Should have entries for users who played this week
        assert len(weekly_entries) >= 2

        # Verify weekly ranks
        weekly_rank = await leaderboard_manager.get_user_rank(1001, "weekly")
        assert weekly_rank is not None

    @pytest.mark.asyncio
    async def test_nearby_ranks(self, setup_test_db):
        """Test getting nearby ranks functionality."""
        db_manager, db_path = setup_test_db

        leaderboard_manager = LeaderboardManager()
        leaderboard_manager.db_manager = db_manager

        # Get nearby ranks for middle-ranked user
        nearby = await leaderboard_manager.get_nearby_ranks(
            1001, "all_time", context_size=2
        )

        assert len(nearby) >= 3  # Should include user and context

        # Find the target user in the results
        user_entry = next((entry for entry in nearby if entry.user_id == 1001), None)
        assert user_entry is not None
        assert user_entry.rank == 2

    @pytest.mark.asyncio
    async def test_leaderboard_caching(self, setup_test_db):
        """Test leaderboard caching functionality."""
        db_manager, db_path = setup_test_db

        leaderboard_manager = LeaderboardManager()
        leaderboard_manager.db_manager = db_manager
        leaderboard_manager.cache_duration = 1  # 1 second for testing

        # First call should populate cache
        entries1 = await leaderboard_manager.get_leaderboard("all_time", limit=5)

        # Second call should use cache
        entries2 = await leaderboard_manager.get_leaderboard("all_time", limit=5)

        assert entries1 == entries2

        # Wait for cache to expire
        await asyncio.sleep(1.1)

        # Third call should refresh cache
        entries3 = await leaderboard_manager.get_leaderboard("all_time", limit=5)
        assert len(entries3) == len(entries1)

    @pytest.mark.asyncio
    async def test_pagination(self, setup_test_db):
        """Test leaderboard pagination."""
        db_manager, db_path = setup_test_db

        leaderboard_manager = LeaderboardManager()
        leaderboard_manager.db_manager = db_manager

        # Get first page
        page1 = await leaderboard_manager.get_leaderboard("all_time", limit=3, offset=0)
        assert len(page1) == 3
        assert page1[0].rank == 1

        # Get second page
        page2 = await leaderboard_manager.get_leaderboard("all_time", limit=3, offset=3)
        assert len(page2) == 2  # Only 5 total users, so 2 remaining
        assert page2[0].rank == 4


class TestLeaderboardCommands:
    """Test the Discord command functionality."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock Discord bot."""
        bot = MagicMock()
        return bot

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Discord context."""
        ctx = MagicMock()
        ctx.author.id = 1001
        ctx.author.display_name = "TestUser"
        ctx.send = AsyncMock()
        return ctx

    @pytest.fixture
    def leaderboard_cog(self, mock_bot):
        """Create LeaderboardCommands cog with mocked dependencies."""
        cog = LeaderboardCommands(mock_bot)
        cog.leaderboard_manager = MagicMock()
        return cog

    @pytest.mark.asyncio
    async def test_leaderboard_command_success(self, leaderboard_cog, mock_ctx):
        """Test successful leaderboard command execution."""
        # Mock leaderboard data
        mock_entries = [
            LeaderboardEntry(
                rank=1,
                user_id=1003,
                username="User#1003",
                total_points=1200,
                accuracy_percentage=90.0,
                questions_answered=60,
                current_streak=7,
            ),
            LeaderboardEntry(
                rank=2,
                user_id=1001,
                username="User#1001",
                total_points=1000,
                accuracy_percentage=90.0,
                questions_answered=50,
                current_streak=5,
            ),
        ]

        leaderboard_cog.leaderboard_manager.get_leaderboard = AsyncMock(
            return_value=mock_entries
        )

        # Test the underlying logic by calling the callback directly
        await leaderboard_cog.leaderboard_command.callback(
            leaderboard_cog, mock_ctx, "all_time", 1
        )

        # Verify manager was called correctly
        leaderboard_cog.leaderboard_manager.get_leaderboard.assert_called_once_with(
            period="all_time", limit=10, offset=0, user_context=1001
        )

        # Verify response was sent
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_leaderboard_command_invalid_period(self, leaderboard_cog, mock_ctx):
        """Test leaderboard command with invalid period."""
        await leaderboard_cog.leaderboard_command.callback(
            leaderboard_cog, mock_ctx, "invalid_period", 1
        )

        # Should send error message
        mock_ctx.send.assert_called_once()
        error_message = mock_ctx.send.call_args[0][0]
        assert "Invalid period" in error_message

    @pytest.mark.asyncio
    async def test_myrank_command_success(self, leaderboard_cog, mock_ctx):
        """Test successful myrank command execution."""
        # Mock rank data
        leaderboard_cog.leaderboard_manager.get_user_rank = AsyncMock(
            return_value=(2, 5)
        )
        leaderboard_cog.leaderboard_manager.get_nearby_ranks = AsyncMock(
            return_value=[]
        )
        leaderboard_cog.leaderboard_manager.get_rank_change = AsyncMock(return_value=1)

        # Execute command
        await leaderboard_cog.my_rank_command.callback(
            leaderboard_cog, mock_ctx, "all_time"
        )

        # Verify manager calls
        leaderboard_cog.leaderboard_manager.get_user_rank.assert_called_once_with(
            1001, "all_time"
        )
        leaderboard_cog.leaderboard_manager.get_nearby_ranks.assert_called_once_with(
            1001, "all_time", context_size=3
        )

        # Verify response
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        assert "embed" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_myrank_command_no_rank(self, leaderboard_cog, mock_ctx):
        """Test myrank command when user has no rank."""
        leaderboard_cog.leaderboard_manager.get_user_rank = AsyncMock(return_value=None)

        await leaderboard_cog.my_rank_command.callback(
            leaderboard_cog, mock_ctx, "all_time"
        )

        # Should send message about no rank
        mock_ctx.send.assert_called_once()
        message = mock_ctx.send.call_args[0][0]
        assert "don't have a rank" in message

    @pytest.mark.asyncio
    async def test_embed_formatting(self, leaderboard_cog, mock_ctx):
        """Test that embeds are properly formatted."""
        mock_entries = [
            LeaderboardEntry(
                rank=1,
                user_id=1001,
                username="User#1001",
                total_points=1000,
                accuracy_percentage=90.0,
                questions_answered=50,
                current_streak=5,
            ),
        ]

        embed = await leaderboard_cog._create_leaderboard_embed(
            mock_entries, "all_time", 1, 1001
        )

        assert embed.title == "🏆 All Time Leaderboard"
        assert "🥇" in embed.description  # Gold medal for rank 1
        assert "1,000 pts" in embed.description  # Formatted points
        assert "90.0% accuracy" in embed.description
        assert "🔥 5 streak" in embed.description

    @pytest.mark.asyncio
    async def test_rank_embed_formatting(self, leaderboard_cog, mock_ctx):
        """Test rank embed formatting."""
        mock_user = MagicMock()
        mock_user.display_name = "TestUser"

        embed = await leaderboard_cog._create_rank_embed(
            mock_user, 2, 10, [], "all_time", 1
        )

        assert "Your All Time Rank" in embed.title
        assert "Rank #2" in embed.fields[0].value
        assert "out of 10" in embed.fields[0].value
        assert "Top 90.0%" in embed.fields[0].value  # Percentile calculation
        assert "Up 1 positions" in embed.fields[0].value  # Rank change


class TestLeaderboardIntegration:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_full_leaderboard_workflow(self):
        """Test complete leaderboard workflow from data to display."""
        # This would be a comprehensive test that:
        # 1. Sets up test database with users and game data
        # 2. Updates weekly rankings
        # 3. Retrieves leaderboard through manager
        # 4. Formats display through commands
        # 5. Verifies end-to-end functionality

        # For now, this is a placeholder for the full integration test
        # In a real implementation, this would combine all the above components
        pass

    @pytest.mark.asyncio
    async def test_concurrent_leaderboard_access(self):
        """Test concurrent access to leaderboard system."""
        # Test that multiple simultaneous requests don't cause issues
        # This would test thread safety and caching under load
        pass

    @pytest.mark.asyncio
    async def test_leaderboard_performance(self):
        """Test leaderboard performance with larger datasets."""
        # Test performance with hundreds or thousands of users
        # Verify that pagination and caching work efficiently
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
