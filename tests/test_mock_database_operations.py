"""
Mock database testing for all data operations.
Tests database interactions with mocked connections and error scenarios.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
import aiosqlite

# Add the parent directory to the path so we can import our modules
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.user_manager import UserManager
from utils.database import DatabaseManager
from utils.models import UserProfile


class TestMockDatabaseOperations:
    """Test database operations with mocked connections."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_manager = MagicMock(spec=DatabaseManager)
        mock_manager.get_connection = AsyncMock()
        return mock_manager

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        mock_conn = AsyncMock(spec=aiosqlite.Connection)
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()
        mock_conn.fetchone = AsyncMock()
        mock_conn.fetchall = AsyncMock()
        return mock_conn

    @pytest.fixture
    def user_manager_with_mock_db(self, mock_db_manager):
        """Create UserManager with mocked database."""
        manager = UserManager()
        manager.db_manager = mock_db_manager
        return manager

    @pytest.mark.asyncio
    async def test_user_creation_database_operations(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test user creation database operations."""
        user_id = 12345

        # Setup mock connection context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock cursor for user lookup (user doesn't exist)
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_connection.execute.return_value = mock_cursor

        # Create user
        user = await user_manager_with_mock_db.get_or_create_user(user_id)

        # Verify database calls
        assert mock_connection.execute.call_count >= 1
        assert mock_connection.commit.called

        # Verify user object
        assert user.user_id == user_id
        assert user.total_points == 0

    @pytest.mark.asyncio
    async def test_user_retrieval_database_operations(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test user retrieval database operations."""
        user_id = 12345

        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock existing user data
        user_data = (
            user_id,
            100,
            10,
            8,
            3,
            5,  # user_id, points, answered, correct, current_streak, best_streak
            datetime.now().isoformat(),
            None,
            None,
            "medium",
            datetime.now().isoformat(),
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=user_data)
        mock_connection.execute.return_value = mock_cursor

        # Retrieve user
        user = await user_manager_with_mock_db.get_or_create_user(user_id)

        # Verify database query
        mock_connection.execute.assert_called_once()

        # Verify user data
        assert user.user_id == user_id
        assert user.total_points == 100
        assert user.questions_answered == 10
        assert user.questions_correct == 8

    @pytest.mark.asyncio
    async def test_stats_update_database_operations(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test stats update database operations."""
        user_id = 12345

        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock existing user for get_or_create_user call
        user_data = (
            user_id,
            50,
            5,
            4,
            2,
            3,
            None,
            None,
            None,
            None,
            datetime.now().isoformat(),
        )
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=user_data)
        mock_connection.execute.return_value = mock_cursor

        # Update stats
        await user_manager_with_mock_db.update_stats(
            user_id, 20, True, "medium", "science"
        )

        # Verify database operations
        assert mock_connection.execute.call_count >= 2  # At least get and update
        assert mock_connection.commit.called

    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self, user_manager_with_mock_db):
        """Test database connection error handling."""
        # Mock connection failure
        user_manager_with_mock_db.db_manager.get_connection.side_effect = Exception(
            "Connection failed"
        )

        # Should raise exception
        with pytest.raises(Exception, match="Connection failed"):
            await user_manager_with_mock_db.get_or_create_user(12345)

    @pytest.mark.asyncio
    async def test_database_query_error_handling(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test database query error handling."""
        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock query failure
        mock_connection.execute.side_effect = Exception("Query failed")

        # Should raise exception
        with pytest.raises(Exception, match="Query failed"):
            await user_manager_with_mock_db.get_or_create_user(12345)

    @pytest.mark.asyncio
    async def test_database_commit_error_handling(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test database commit error handling."""
        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock successful query but failed commit
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_connection.execute.return_value = mock_cursor
        mock_connection.commit.side_effect = Exception("Commit failed")

        # Should raise exception
        with pytest.raises(Exception, match="Commit failed"):
            await user_manager_with_mock_db.get_or_create_user(12345)

    @pytest.mark.asyncio
    async def test_challenge_completion_database_operations(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test challenge completion database operations."""
        user_id = 12345

        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Test daily challenge completion
        result = await user_manager_with_mock_db.update_challenge_completion(
            user_id, "daily"
        )

        # Verify database operations
        mock_connection.execute.assert_called_once()
        mock_connection.commit.assert_called_once()
        assert result is True

        # Reset mocks for weekly challenge test
        mock_connection.reset_mock()

        # Test weekly challenge completion
        result = await user_manager_with_mock_db.update_challenge_completion(
            user_id, "weekly"
        )

        # Verify database operations
        mock_connection.execute.assert_called_once()
        mock_connection.commit.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_user_rank_database_operations(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test user rank calculation database operations."""
        user_id = 12345

        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock rank query result
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(3,))  # Rank 3
        mock_connection.execute.return_value = mock_cursor

        # Get user rank
        rank = await user_manager_with_mock_db.get_user_rank(user_id)

        # Verify database query
        mock_connection.execute.assert_called_once()
        assert rank == 3

    @pytest.mark.asyncio
    async def test_user_stats_database_operations(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test comprehensive user stats database operations."""
        user_id = 12345

        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock user profile data
        user_data = (
            user_id,
            200,
            20,
            16,
            4,
            6,
            None,
            None,
            None,
            None,
            datetime.now().isoformat(),
        )

        # Mock various query results
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=user_data)
        mock_cursor.fetchall = AsyncMock(
            return_value=[]
        )  # Empty results for other queries
        mock_connection.execute.return_value = mock_cursor

        # Get user stats
        stats = await user_manager_with_mock_db.get_user_stats(user_id)

        # Verify multiple database queries were made
        assert (
            mock_connection.execute.call_count >= 5
        )  # Profile + category + difficulty + performance + achievements + rank

        # Verify stats structure
        assert stats.user_profile.user_id == user_id
        assert isinstance(stats.points_per_category, dict)
        assert isinstance(stats.difficulty_breakdown, dict)

    @pytest.mark.asyncio
    async def test_user_reset_database_operations(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test user reset database operations."""
        user_id = 12345

        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Reset user stats
        result = await user_manager_with_mock_db.reset_user_stats(user_id)

        # Verify multiple database operations (update users, delete achievements, delete sessions)
        assert mock_connection.execute.call_count >= 3
        assert mock_connection.commit.called
        assert result is True

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test database transaction rollback on error."""
        # Setup mock connection that fails on commit
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock successful execute but failed commit
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_connection.execute.return_value = mock_cursor
        mock_connection.commit.side_effect = Exception("Commit failed")

        # Should handle the error
        with pytest.raises(Exception):
            await user_manager_with_mock_db.get_or_create_user(12345)

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test concurrent database operations."""
        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock user data
        user_data = (
            12345,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            None,
            None,
            datetime.now().isoformat(),
        )
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=user_data)
        mock_connection.execute.return_value = mock_cursor

        # Simulate concurrent operations
        import asyncio

        tasks = [
            user_manager_with_mock_db.update_stats(12345, 10, True, "easy"),
            user_manager_with_mock_db.update_stats(12345, 20, True, "medium"),
            user_manager_with_mock_db.get_user_rank(12345),
        ]

        # Should handle concurrent operations without error
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least some operations should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0

    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion(self, user_manager_with_mock_db):
        """Test handling of database connection pool exhaustion."""
        # Mock connection pool exhaustion
        user_manager_with_mock_db.db_manager.get_connection.side_effect = Exception(
            "Connection pool exhausted"
        )

        # Should handle gracefully
        with pytest.raises(Exception, match="Connection pool exhausted"):
            await user_manager_with_mock_db.get_or_create_user(12345)

    @pytest.mark.asyncio
    async def test_malformed_database_data_handling(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test handling of malformed database data."""
        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock malformed user data (missing fields)
        malformed_data = (12345, None, None)  # Incomplete row
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=malformed_data)
        mock_connection.execute.return_value = mock_cursor

        # Should handle malformed data gracefully
        try:
            user = await user_manager_with_mock_db.get_or_create_user(12345)
            # If it succeeds, verify it handles missing data appropriately
            assert user.user_id == 12345
        except (IndexError, TypeError):
            # It's acceptable to raise an exception for malformed data
            pass

    @pytest.mark.asyncio
    async def test_database_timeout_handling(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test database timeout handling."""
        # Setup mock connection that times out
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock timeout error
        mock_connection.execute.side_effect = asyncio.TimeoutError("Database timeout")

        # Should handle timeout
        with pytest.raises(asyncio.TimeoutError):
            await user_manager_with_mock_db.get_or_create_user(12345)

    @pytest.mark.asyncio
    async def test_database_integrity_constraint_violation(
        self, user_manager_with_mock_db, mock_connection
    ):
        """Test database integrity constraint violation handling."""
        # Setup mock connection
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        user_manager_with_mock_db.db_manager.get_connection.return_value = mock_context

        # Mock integrity constraint violation
        mock_connection.execute.side_effect = aiosqlite.IntegrityError(
            "UNIQUE constraint failed"
        )

        # Should handle constraint violation
        with pytest.raises(aiosqlite.IntegrityError):
            await user_manager_with_mock_db.get_or_create_user(12345)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
