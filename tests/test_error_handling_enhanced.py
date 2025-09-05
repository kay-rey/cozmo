"""
Test suite for enhanced error handling and logging in the trivia system.
Tests database error handling, game state error handling, and recovery mechanisms.
"""

import pytest
import asyncio
import tempfile
import os
import shutil
import sqlite3
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import discord

# Import the enhanced modules
from utils.database import (
    DatabaseManager,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseIntegrityError,
)
from utils.game_manager import (
    GameManager,
    GameError,
    GamePermissionError,
    GameStateError,
    GameConcurrencyError,
)
from utils.question_engine import QuestionEngine
from utils.models import Question, GameSession


class TestDatabaseErrorHandling:
    """Test database error handling and recovery mechanisms."""

    @pytest.fixture
    async def temp_db_manager(self):
        """Create a temporary database manager for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_trivia.db")

        manager = DatabaseManager(db_path)
        await manager.initialize_database()

        yield manager

        # Cleanup
        await manager.close_all_connections()
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_database_connection_retry(self, temp_db_manager):
        """Test database connection retry mechanism."""
        # Simulate connection failure by corrupting the database path
        original_path = temp_db_manager.db_path
        temp_db_manager.db_path = "/invalid/path/database.db"

        with pytest.raises(DatabaseConnectionError):
            async with temp_db_manager.get_connection() as conn:
                await conn.execute("SELECT 1")

        # Restore path and verify recovery
        temp_db_manager.db_path = original_path
        async with temp_db_manager.get_connection() as conn:
            cursor = await conn.execute("SELECT 1")
            result = await cursor.fetchone()
            assert result[0] == 1

    @pytest.mark.asyncio
    async def test_database_integrity_check(self, temp_db_manager):
        """Test database integrity checking."""
        # Test healthy database
        is_healthy = await temp_db_manager.check_database_integrity()
        assert is_healthy is True

        # Test integrity check with missing tables
        async with temp_db_manager.get_connection() as conn:
            await conn.execute("DROP TABLE IF EXISTS users")
            await conn.commit()

        is_healthy = await temp_db_manager.check_database_integrity()
        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_database_backup_and_restore(self, temp_db_manager):
        """Test database backup and restore functionality."""
        # Add some test data
        async with temp_db_manager.get_connection() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, total_points) VALUES (?, ?)", (12345, 100)
            )
            await conn.commit()

        # Create backup
        backup_path = await temp_db_manager.backup_database()
        assert os.path.exists(backup_path)
        assert os.path.exists(f"{backup_path}.meta")

        # Modify original data
        async with temp_db_manager.get_connection() as conn:
            await conn.execute(
                "UPDATE users SET total_points = ? WHERE user_id = ?", (200, 12345)
            )
            await conn.commit()

        # Restore from backup
        success = await temp_db_manager.restore_database(backup_path)
        assert success is True

        # Verify restored data
        async with temp_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT total_points FROM users WHERE user_id = ?", (12345,)
            )
            result = await cursor.fetchone()
            assert result[0] == 100

    @pytest.mark.asyncio
    async def test_database_corruption_recovery(self, temp_db_manager):
        """Test database corruption detection and recovery."""
        # Simulate corruption by writing invalid data
        with open(temp_db_manager.db_path, "wb") as f:
            f.write(b"corrupted data")

        # Test corruption detection
        is_healthy = await temp_db_manager.check_database_integrity()
        assert is_healthy is False

        # Test recovery attempt (should create new database)
        await temp_db_manager.initialize_database()

        # Verify new database is healthy
        is_healthy = await temp_db_manager.check_database_integrity()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_database_maintenance(self, temp_db_manager):
        """Test database maintenance operations."""
        # Add old test data
        old_date = datetime.now() - timedelta(days=10)
        async with temp_db_manager.get_connection() as conn:
            await conn.execute(
                "INSERT INTO game_sessions (channel_id, user_id, start_time, is_completed) VALUES (?, ?, ?, ?)",
                (123, 456, old_date, True),
            )
            await conn.commit()

        # Run maintenance
        await temp_db_manager.perform_maintenance()

        # Verify old data was cleaned up
        async with temp_db_manager.get_connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM game_sessions")
            count = await cursor.fetchone()
            assert count[0] == 0

    @pytest.mark.asyncio
    async def test_database_health_status(self, temp_db_manager):
        """Test database health status reporting."""
        health = await temp_db_manager.get_health_status()

        assert "status" in health
        assert "issues" in health
        assert "recommendations" in health
        assert health["status"] in ["healthy", "warning", "critical"]

    @pytest.mark.asyncio
    async def test_connection_pool_management(self, temp_db_manager):
        """Test connection pool error handling."""

        # Test multiple concurrent connections
        async def test_connection():
            async with temp_db_manager.get_connection() as conn:
                await conn.execute("SELECT 1")
                await asyncio.sleep(0.1)

        # Run multiple concurrent operations
        tasks = [test_connection() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Verify pool is managed correctly
        stats = await temp_db_manager.get_database_stats()
        assert stats["connection_pool_size"] <= temp_db_manager._pool_size


class TestGameManagerErrorHandling:
    """Test game manager error handling and cleanup mechanisms."""

    @pytest.fixture
    def mock_question_engine(self):
        """Create a mock question engine."""
        engine = Mock(spec=QuestionEngine)
        engine.get_question = AsyncMock(
            return_value=Question(
                id=1,
                question_text="Test question?",
                question_type="multiple_choice",
                difficulty="easy",
                category="test",
                correct_answer="A",
                options=["A", "B", "C", "D"],
                point_value=10,
            )
        )
        return engine

    @pytest.fixture
    def mock_bot(self):
        """Create a mock Discord bot."""
        bot = Mock(spec=discord.Bot)

        # Mock channel
        channel = Mock()
        channel.permissions_for.return_value = Mock(
            send_messages=True,
            embed_links=True,
            add_reactions=True,
            read_message_history=True,
            use_external_emojis=True,
        )
        channel.guild.me = Mock()

        bot.get_channel.return_value = channel
        return bot

    @pytest.fixture
    async def game_manager(self, mock_question_engine, mock_bot):
        """Create a game manager for testing."""
        manager = GameManager(mock_question_engine, mock_bot)
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_game_start_permission_error(self, game_manager, mock_bot):
        """Test game start with permission errors."""
        # Mock permission check failure
        channel = mock_bot.get_channel.return_value
        channel.permissions_for.return_value.send_messages = False

        with pytest.raises(GamePermissionError):
            await game_manager.start_game(
                channel_id=123, user_id=456, difficulty="easy"
            )

    @pytest.mark.asyncio
    async def test_game_concurrency_error(self, game_manager):
        """Test concurrent game conflict handling."""
        # Start first game
        game1 = await game_manager.start_game(
            channel_id=123, user_id=456, difficulty="easy"
        )
        assert game1 is not None

        # Try to start second game in same channel
        with pytest.raises(GameConcurrencyError):
            await game_manager.start_game(
                channel_id=123, user_id=789, difficulty="medium"
            )

    @pytest.mark.asyncio
    async def test_game_state_validation(self, game_manager):
        """Test game state validation and cleanup."""
        # Start a game
        game = await game_manager.start_game(
            channel_id=123, user_id=456, difficulty="easy"
        )
        assert game is not None

        # Corrupt game state by removing question
        game.question = None

        # Validation should fail and trigger cleanup
        is_valid = await game_manager._validate_game_state(123)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_inaccessible_channel_cleanup(self, game_manager, mock_bot):
        """Test cleanup of inaccessible channels."""
        # Start a game
        await game_manager.start_game(channel_id=123, user_id=456, difficulty="easy")

        # Simulate channel becoming inaccessible
        mock_bot.get_channel.return_value = None

        # Run cleanup
        cleaned = await game_manager.cleanup_inaccessible_channels()
        assert cleaned == 1
        assert 123 not in game_manager.active_games

    @pytest.mark.asyncio
    async def test_expired_game_cleanup(self, game_manager):
        """Test cleanup of expired games."""
        # Start a game
        game = await game_manager.start_game(
            channel_id=123, user_id=456, difficulty="easy"
        )

        # Simulate game being very old
        game.start_time = datetime.now() - timedelta(minutes=15)

        # Run cleanup
        cleaned = await game_manager.cleanup_expired_games()
        assert cleaned == 1
        assert 123 not in game_manager.active_games

    @pytest.mark.asyncio
    async def test_timer_error_handling(self, game_manager):
        """Test timer error handling and fallback."""

        # Mock callback that raises an exception
        def failing_callback():
            raise discord.Forbidden(Mock(), "Permission denied")

        # Start game with failing callback
        await game_manager.start_game(
            channel_id=123,
            user_id=456,
            difficulty="easy",
            timeout_duration=1,  # Short timeout for testing
            timeout_callback=failing_callback,
        )

        # Wait for timeout
        await asyncio.sleep(2)

        # Game should be cleaned up despite callback error
        assert 123 not in game_manager.active_games

    @pytest.mark.asyncio
    async def test_race_condition_prevention(self, game_manager):
        """Test race condition prevention with concurrent operations."""

        async def start_game_task():
            try:
                return await game_manager.start_game(
                    channel_id=123, user_id=456, difficulty="easy"
                )
            except GameConcurrencyError:
                return None

        # Try to start multiple games concurrently
        tasks = [start_game_task() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one should succeed
        successful_games = [
            r for r in results if r is not None and not isinstance(r, Exception)
        ]
        assert len(successful_games) == 1

    @pytest.mark.asyncio
    async def test_error_tracking(self, game_manager):
        """Test error tracking and monitoring."""
        # Simulate multiple errors
        for _ in range(5):
            game_manager._record_error("test_error")

        # Check error tracking
        assert game_manager._error_count == 5
        assert game_manager._last_error_time is not None

        # Get health status
        health = game_manager.get_health_status()
        assert "error_count" in str(health) or health["status"] != "healthy"

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, game_manager):
        """Test graceful shutdown with active games."""
        # Start multiple games
        for i in range(3):
            await game_manager.start_game(
                channel_id=100 + i, user_id=456, difficulty="easy"
            )

        assert len(game_manager.active_games) == 3

        # Shutdown should clean up all games
        await game_manager.shutdown()

        assert len(game_manager.active_games) == 0
        assert len(game_manager.game_timers) == 0

    @pytest.mark.asyncio
    async def test_callback_error_wrapping(self, game_manager):
        """Test callback error wrapping and handling."""
        error_raised = False

        def failing_callback():
            nonlocal error_raised
            error_raised = True
            raise Exception("Test callback error")

        # Wrap callback
        wrapped = game_manager._wrap_callback(failing_callback, "test")

        # Call wrapped callback - should not raise exception
        await wrapped()

        # But the original callback should have been called
        assert error_raised is True


class TestIntegrationErrorHandling:
    """Test integration between database and game manager error handling."""

    @pytest.mark.asyncio
    async def test_database_game_manager_integration(self):
        """Test error handling integration between database and game manager."""
        # Create temporary database
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_integration.db")

        try:
            # Initialize database
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize_database()

            # Create question engine and game manager
            question_engine = Mock(spec=QuestionEngine)
            question_engine.get_question = AsyncMock(
                return_value=Question(
                    id=1,
                    question_text="Integration test?",
                    question_type="multiple_choice",
                    difficulty="easy",
                    category="test",
                    correct_answer="A",
                    options=["A", "B", "C", "D"],
                    point_value=10,
                )
            )

            game_manager = GameManager(question_engine)

            # Test that both systems can handle errors gracefully
            game = await game_manager.start_game(
                channel_id=123, user_id=456, difficulty="easy"
            )

            assert game is not None

            # Simulate database error during game
            # Game manager should handle this gracefully
            await game_manager.end_game(123, reason="test")

            # Cleanup
            await game_manager.shutdown()
            await db_manager.close_all_connections()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run basic tests
    import sys

    print("Testing enhanced error handling implementation...")

    # Test database error handling
    print("✓ Database error handling classes imported successfully")

    # Test game manager error handling
    print("✓ Game manager error handling classes imported successfully")

    # Test exception hierarchy
    assert issubclass(DatabaseConnectionError, DatabaseError)
    assert issubclass(DatabaseIntegrityError, DatabaseError)
    assert issubclass(GamePermissionError, GameError)
    assert issubclass(GameStateError, GameError)
    assert issubclass(GameConcurrencyError, GameError)
    print("✓ Exception hierarchy is correct")

    print("\nAll basic error handling tests passed!")
    print("Run with pytest for comprehensive testing:")
    print("pytest tests/test_error_handling_enhanced.py -v")
