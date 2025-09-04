"""
Database connection utilities with async support for the Enhanced Trivia System.
Provides SQLite database connection management, schema creation, and migration support.
"""

import aiosqlite
import asyncio
import logging
import os
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database connections and operations with async support."""

    def __init__(self, db_path: str = "data/trivia.db"):
        self.db_path = db_path
        self.schema_version = 1
        self._connection_pool = []
        self._pool_size = 5

        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool or create a new one."""
        connection = None
        try:
            if self._connection_pool:
                connection = self._connection_pool.pop()
            else:
                connection = await aiosqlite.connect(self.db_path)
                # Enable foreign key constraints
                await connection.execute("PRAGMA foreign_keys = ON")
                await connection.commit()

            yield connection

        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if connection:
                await connection.rollback()
            raise
        finally:
            if connection and len(self._connection_pool) < self._pool_size:
                self._connection_pool.append(connection)
            elif connection:
                await connection.close()

    async def initialize_database(self):
        """Initialize the database with required tables and schema."""
        try:
            async with self.get_connection() as conn:
                # Create schema version table first
                await self._create_schema_version_table(conn)

                # Check current schema version
                current_version = await self._get_schema_version(conn)

                if current_version == 0:
                    # Fresh database, create all tables
                    await self._create_all_tables(conn)
                    await self._set_schema_version(conn, self.schema_version)
                    logger.info("Database initialized with fresh schema")
                elif current_version < self.schema_version:
                    # Run migrations
                    await self._run_migrations(conn, current_version)
                    logger.info(
                        f"Database migrated from version {current_version} to {self.schema_version}"
                    )

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def _create_schema_version_table(self, conn: aiosqlite.Connection):
        """Create the schema version tracking table."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.commit()

    async def _get_schema_version(self, conn: aiosqlite.Connection) -> int:
        """Get the current schema version."""
        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        result = await cursor.fetchone()
        return result[0] if result[0] is not None else 0

    async def _set_schema_version(self, conn: aiosqlite.Connection, version: int):
        """Set the schema version."""
        await conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)", (version,)
        )
        await conn.commit()

    async def _create_all_tables(self, conn: aiosqlite.Connection):
        """Create all required tables for the trivia system."""

        # Users table
        await conn.execute("""
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                total_points INTEGER DEFAULT 0,
                questions_answered INTEGER DEFAULT 0,
                questions_correct INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                last_played TIMESTAMP,
                daily_challenge_completed DATE,
                weekly_challenge_completed DATE,
                preferred_difficulty TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Questions table
        await conn.execute("""
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL CHECK (question_type IN ('multiple_choice', 'true_false', 'fill_blank')),
                difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
                category TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                options TEXT, -- JSON for multiple choice options
                answer_variations TEXT, -- JSON for fill-in-blank variations
                explanation TEXT,
                point_value INTEGER DEFAULT 0,
                times_asked INTEGER DEFAULT 0,
                times_correct INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User achievements table
        await conn.execute("""
            CREATE TABLE user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_id TEXT NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE(user_id, achievement_id)
            )
        """)

        # Weekly rankings table
        await conn.execute("""
            CREATE TABLE weekly_rankings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                week_start DATE NOT NULL,
                points INTEGER DEFAULT 0,
                rank INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE(user_id, week_start)
            )
        """)

        # Game sessions table for tracking active games
        await conn.execute("""
            CREATE TABLE game_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                question_id INTEGER,
                difficulty TEXT,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                is_completed BOOLEAN DEFAULT FALSE,
                is_challenge BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE SET NULL
            )
        """)

        # Create indexes for better performance
        await self._create_indexes(conn)

        await conn.commit()
        logger.info("All database tables created successfully")

    async def _create_indexes(self, conn: aiosqlite.Connection):
        """Create database indexes for better query performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_total_points ON users (total_points DESC)",
            "CREATE INDEX IF NOT EXISTS idx_users_last_played ON users (last_played)",
            "CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions (difficulty)",
            "CREATE INDEX IF NOT EXISTS idx_questions_category ON questions (category)",
            "CREATE INDEX IF NOT EXISTS idx_questions_type ON questions (question_type)",
            "CREATE INDEX IF NOT EXISTS idx_user_achievements_user_id ON user_achievements (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_weekly_rankings_week_start ON weekly_rankings (week_start)",
            "CREATE INDEX IF NOT EXISTS idx_weekly_rankings_points ON weekly_rankings (points DESC)",
            "CREATE INDEX IF NOT EXISTS idx_game_sessions_channel_id ON game_sessions (channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_game_sessions_active ON game_sessions (is_completed, start_time)",
        ]

        for index_sql in indexes:
            await conn.execute(index_sql)

        await conn.commit()

    async def _run_migrations(self, conn: aiosqlite.Connection, current_version: int):
        """Run database migrations from current version to latest."""
        # Future migrations will be implemented here
        # For now, we only have version 1
        if current_version < self.schema_version:
            await self._set_schema_version(conn, self.schema_version)

    async def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the database."""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data/backups/trivia_backup_{timestamp}.db"

        # Ensure backup directory exists
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        try:
            # Use file system copy for SQLite backup
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            raise

    async def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup."""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Close all connections before restore
            await self.close_all_connections()

            # Restore the backup
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from {backup_path}")

            # Reinitialize after restore
            await self.initialize_database()
            return True

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False

    async def check_database_integrity(self) -> bool:
        """Check database integrity and return True if healthy."""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("PRAGMA integrity_check")
                result = await cursor.fetchone()
                is_healthy = result[0] == "ok"

                if is_healthy:
                    logger.info("Database integrity check passed")
                else:
                    logger.warning(f"Database integrity check failed: {result[0]}")

                return is_healthy

        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            return False

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and information."""
        try:
            async with self.get_connection() as conn:
                stats = {}

                # Get table row counts
                tables = [
                    "users",
                    "questions",
                    "user_achievements",
                    "weekly_rankings",
                    "game_sessions",
                ]
                for table in tables:
                    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = await cursor.fetchone()
                    stats[f"{table}_count"] = count[0]

                # Get database size
                cursor = await conn.execute("PRAGMA page_count")
                page_count = await cursor.fetchone()
                cursor = await conn.execute("PRAGMA page_size")
                page_size = await cursor.fetchone()
                stats["database_size_bytes"] = page_count[0] * page_size[0]

                # Get schema version
                stats["schema_version"] = await self._get_schema_version(conn)

                return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    async def close_all_connections(self):
        """Close all connections in the pool."""
        while self._connection_pool:
            conn = self._connection_pool.pop()
            await conn.close()
        logger.info("All database connections closed")


# Global database manager instance
db_manager = DatabaseManager()
