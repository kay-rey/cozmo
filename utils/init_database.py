"""
Database initialization script for the Enhanced Trivia System.
This script can be run to initialize or reset the database.
"""

import asyncio
import logging
import sys
import os

# Add the parent directory to the path so we can import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import db_manager
from utils.backup import BackupManager, RecoveryManager
from utils.migrations import MigrationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def initialize_database():
    """Initialize the database with all required tables and indexes."""
    try:
        logger.info("Starting database initialization...")

        # Initialize the database
        await db_manager.initialize_database()

        # Check database integrity
        integrity_ok = await db_manager.check_database_integrity()
        if not integrity_ok:
            logger.error("Database integrity check failed after initialization")
            return False

        # Get database stats
        stats = await db_manager.get_database_stats()
        logger.info(f"Database initialized successfully. Stats: {stats}")

        # Create initial backup
        backup_manager = BackupManager(db_manager)
        backup_path = await backup_manager.create_backup("initial")
        logger.info(f"Created initial backup: {backup_path}")

        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    finally:
        await db_manager.close_all_connections()


async def reset_database():
    """Reset the database by removing the existing file and reinitializing."""
    try:
        logger.warning("Resetting database - all data will be lost!")

        # Create backup before reset
        if os.path.exists(db_manager.db_path):
            backup_manager = BackupManager(db_manager)
            backup_path = await backup_manager.create_backup("pre_reset")
            logger.info(f"Created backup before reset: {backup_path}")

        # Close all connections
        await db_manager.close_all_connections()

        # Remove existing database file
        if os.path.exists(db_manager.db_path):
            os.remove(db_manager.db_path)
            logger.info("Removed existing database file")

        # Reinitialize
        return await initialize_database()

    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False


async def test_database_operations():
    """Test basic database operations."""
    try:
        logger.info("Testing database operations...")

        async with db_manager.get_connection() as conn:
            # Test inserting a user
            await conn.execute(
                """
                INSERT OR REPLACE INTO users (user_id, total_points, questions_answered)
                VALUES (?, ?, ?)
            """,
                (12345, 100, 10),
            )

            # Test querying the user
            cursor = await conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (12345,)
            )
            user = await cursor.fetchone()

            if user:
                logger.info(f"Test user created successfully: {user}")
            else:
                logger.error("Failed to create test user")
                return False

            # Test inserting a question
            await conn.execute(
                """
                INSERT INTO questions (question_text, question_type, difficulty, category, correct_answer, point_value)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                ("Test question?", "multiple_choice", "easy", "test", "A", 10),
            )

            # Test querying the question
            cursor = await conn.execute(
                "SELECT * FROM questions WHERE category = ?", ("test",)
            )
            question = await cursor.fetchone()

            if question:
                logger.info(f"Test question created successfully: {question}")
            else:
                logger.error("Failed to create test question")
                return False

            await conn.commit()
            logger.info("All database operations test passed!")
            return True

    except Exception as e:
        logger.error(f"Database operations test failed: {e}")
        return False


async def main():
    """Main function to run database initialization."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "reset":
            success = await reset_database()
        elif command == "test":
            await initialize_database()
            success = await test_database_operations()
        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Usage: python init_database.py [reset|test]")
            return
    else:
        success = await initialize_database()

    if success:
        logger.info("Database setup completed successfully!")
    else:
        logger.error("Database setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
