"""
Test suite for database infrastructure and data models.
Tests database connection, schema creation, migrations, and backup/recovery.
"""

import asyncio
import os
import tempfile
import shutil
import sys
from datetime import datetime, date

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import DatabaseManager
from utils.backup import BackupManager, RecoveryManager
from utils.migrations import MigrationManager
from utils.models import (
    UserProfile,
    Question,
    UserAchievement,
    WeeklyRanking,
    GameSession,
)


class TestDatabaseInfrastructure:
    """Test database infrastructure components."""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_dir, "test_trivia.db")
        self.db_manager = DatabaseManager(self.test_db_path)
        self.backup_manager = BackupManager(
            self.db_manager, os.path.join(self.test_dir, "backups")
        )
        self.recovery_manager = RecoveryManager(self.db_manager, self.backup_manager)

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    async def test_database_initialization(self):
        """Test database initialization and schema creation."""
        # Initialize database
        await self.db_manager.initialize_database()

        # Check that database file was created
        assert os.path.exists(self.test_db_path)

        # Check database integrity
        integrity_ok = await self.db_manager.check_database_integrity()
        assert integrity_ok

        # Check that all tables were created
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = await cursor.fetchall()
            table_names = [table[0] for table in tables]

            expected_tables = [
                "users",
                "questions",
                "user_achievements",
                "weekly_rankings",
                "game_sessions",
                "schema_version",
            ]
            for table in expected_tables:
                assert table in table_names

        await self.db_manager.close_all_connections()

    async def test_database_operations(self):
        """Test basic database CRUD operations."""
        await self.db_manager.initialize_database()

        async with self.db_manager.get_connection() as conn:
            # Test user operations
            await conn.execute(
                """
                INSERT INTO users (user_id, total_points, questions_answered, questions_correct)
                VALUES (?, ?, ?, ?)
            """,
                (12345, 150, 15, 12),
            )

            cursor = await conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (12345,)
            )
            user = await cursor.fetchone()
            assert user is not None
            assert user[1] == 150  # total_points

            # Test question operations
            await conn.execute(
                """
                INSERT INTO questions (question_text, question_type, difficulty, category, correct_answer, point_value)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "What is the capital of California?",
                    "multiple_choice",
                    "easy",
                    "geography",
                    "Sacramento",
                    10,
                ),
            )

            cursor = await conn.execute(
                "SELECT * FROM questions WHERE category = ?", ("geography",)
            )
            question = await cursor.fetchone()
            assert question is not None
            assert question[1] == "What is the capital of California?"

            # Test achievement operations
            await conn.execute(
                """
                INSERT INTO user_achievements (user_id, achievement_id)
                VALUES (?, ?)
            """,
                (12345, "hot_streak"),
            )

            cursor = await conn.execute(
                "SELECT * FROM user_achievements WHERE user_id = ?", (12345,)
            )
            achievement = await cursor.fetchone()
            assert achievement is not None
            assert achievement[2] == "hot_streak"

            await conn.commit()

        await self.db_manager.close_all_connections()

    async def test_data_models(self):
        """Test data model serialization and deserialization."""
        # Test UserProfile
        user_profile = UserProfile(
            user_id=12345,
            total_points=200,
            questions_answered=20,
            questions_correct=18,
            current_streak=5,
            best_streak=8,
            last_played=datetime.now(),
            preferred_difficulty="medium",
        )

        # Test serialization
        user_dict = user_profile.to_dict()
        assert user_dict["user_id"] == 12345
        assert user_dict["total_points"] == 200

        # Test deserialization
        restored_user = UserProfile.from_dict(user_dict)
        assert restored_user.user_id == user_profile.user_id
        assert restored_user.total_points == user_profile.total_points
        assert restored_user.accuracy_percentage == 90.0

        # Test Question model
        question = Question(
            question_text="Test question?",
            question_type="multiple_choice",
            difficulty="medium",
            category="test",
            correct_answer="A",
            options=["A", "B", "C", "D"],
            explanation="This is a test question",
        )

        question_dict = question.to_dict()
        restored_question = Question.from_dict(question_dict)
        assert restored_question.question_text == question.question_text
        assert restored_question.options == question.options
        assert restored_question.point_value == 20  # Medium difficulty default

    async def test_backup_and_recovery(self):
        """Test backup and recovery functionality."""
        await self.db_manager.initialize_database()

        # Add some test data
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, total_points) VALUES (?, ?)
            """,
                (12345, 100),
            )
            await conn.commit()

        # Create backup
        backup_path = await self.backup_manager.create_backup("test")
        assert os.path.exists(backup_path)

        # Verify backup
        backup_valid = await self.backup_manager.verify_backup(backup_path)
        assert backup_valid

        # Modify original database
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                "UPDATE users SET total_points = ? WHERE user_id = ?", (200, 12345)
            )
            await conn.commit()

        # Restore from backup
        restore_success = await self.backup_manager.restore_from_backup(backup_path)
        assert restore_success

        # Verify restoration
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT total_points FROM users WHERE user_id = ?", (12345,)
            )
            result = await cursor.fetchone()
            assert result[0] == 100  # Should be restored to original value

        await self.db_manager.close_all_connections()

    async def test_database_stats(self):
        """Test database statistics functionality."""
        await self.db_manager.initialize_database()

        # Add some test data
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, total_points) VALUES (?, ?)", (1, 100)
            )
            await conn.execute(
                "INSERT INTO users (user_id, total_points) VALUES (?, ?)", (2, 200)
            )
            await conn.execute(
                "INSERT INTO questions (question_text, question_type, difficulty, category, correct_answer) VALUES (?, ?, ?, ?, ?)",
                ("Test?", "multiple_choice", "easy", "test", "A"),
            )
            await conn.commit()

        # Get stats
        stats = await self.db_manager.get_database_stats()

        assert stats["users_count"] == 2
        assert stats["questions_count"] == 1
        assert stats["schema_version"] == 1
        assert stats["database_size_bytes"] > 0

        await self.db_manager.close_all_connections()

    async def test_connection_pooling(self):
        """Test database connection pooling."""
        await self.db_manager.initialize_database()

        # Test multiple concurrent connections
        async def test_connection():
            async with self.db_manager.get_connection() as conn:
                cursor = await conn.execute("SELECT 1")
                result = await cursor.fetchone()
                return result[0]

        # Run multiple concurrent operations
        tasks = [test_connection() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should return 1
        assert all(result == 1 for result in results)

        await self.db_manager.close_all_connections()


async def run_all_tests():
    """Run all database infrastructure tests."""
    test_instance = TestDatabaseInfrastructure()

    tests = [
        test_instance.test_database_initialization,
        test_instance.test_database_operations,
        test_instance.test_data_models,
        test_instance.test_backup_and_recovery,
        test_instance.test_database_stats,
        test_instance.test_connection_pooling,
    ]

    for i, test in enumerate(tests, 1):
        print(f"Running test {i}/{len(tests)}: {test.__name__}")
        test_instance.setup_method()
        try:
            await test()
            print(f"✅ {test.__name__} passed")
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            raise
        finally:
            test_instance.teardown_method()

    print("🎉 All database infrastructure tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
