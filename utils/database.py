"""
Database connection utilities with async support for the Enhanced Trivia System.
Provides SQLite database connection management, schema creation, and migration support.
Enhanced with comprehensive error handling, connection pooling, and recovery mechanisms.
"""

import aiosqlite
import asyncio
import logging
import os
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from contextlib import asynccontextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database-related errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""

    pass


class DatabaseIntegrityError(DatabaseError):
    """Exception raised when database integrity check fails."""

    pass


class DatabaseRecoveryError(DatabaseError):
    """Exception raised when database recovery fails."""

    pass


def retry_on_database_error(
    max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0
):
    """Decorator to retry database operations on failure with exponential backoff."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (aiosqlite.Error, sqlite3.Error, DatabaseError) as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            f"Database operation {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        break

                    wait_time = delay * (backoff**attempt)
                    logger.warning(
                        f"Database operation {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    # Don't retry on non-database errors
                    logger.error(f"Non-database error in {func.__name__}: {e}")
                    raise

            raise last_exception

        return wrapper

    return decorator


class DatabaseManager:
    """
    Manages SQLite database connections and operations with async support.
    Enhanced with connection pooling, error handling, and recovery mechanisms.
    """

    def __init__(self, db_path: str = "data/trivia.db"):
        self.db_path = db_path
        self.schema_version = 1
        self._connection_pool = []
        self._pool_size = 10
        self._max_pool_size = 20
        self._pool_lock = asyncio.Lock()
        self._connection_timeout = 30.0
        self._busy_timeout = 30000  # 30 seconds in milliseconds

        # Health monitoring
        self._last_integrity_check = None
        self._integrity_check_interval = timedelta(hours=6)
        self._auto_backup_enabled = True
        self._backup_interval = timedelta(hours=12)
        self._last_backup = None

        # Error tracking
        self._error_count = 0
        self._last_error_time = None
        self._max_errors_per_hour = 100

        # Ensure data directory exists
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            os.makedirs("data/backups", exist_ok=True)
            logger.info(f"Database directories initialized: {os.path.dirname(db_path)}")
        except OSError as e:
            logger.error(f"Failed to create database directories: {e}")
            raise DatabaseError(f"Cannot create database directories: {e}")

    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new database connection with proper configuration."""
        try:
            connection = await aiosqlite.connect(
                self.db_path, timeout=self._connection_timeout
            )

            # Configure connection for optimal performance and reliability
            await connection.execute("PRAGMA foreign_keys = ON")
            await connection.execute("PRAGMA journal_mode = WAL")
            await connection.execute("PRAGMA synchronous = NORMAL")
            await connection.execute("PRAGMA cache_size = -64000")  # 64MB cache
            await connection.execute(f"PRAGMA busy_timeout = {self._busy_timeout}")
            await connection.execute("PRAGMA temp_store = MEMORY")
            await connection.commit()

            logger.debug("New database connection created and configured")
            return connection

        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise DatabaseConnectionError(f"Cannot create database connection: {e}")

    async def _validate_connection(self, connection: aiosqlite.Connection) -> bool:
        """Validate that a connection is still healthy."""
        try:
            cursor = await connection.execute("SELECT 1")
            await cursor.fetchone()
            return True
        except Exception:
            return False

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool or create a new one with error handling."""
        connection = None
        acquired_from_pool = False

        try:
            async with self._pool_lock:
                # Try to get a connection from the pool
                while self._connection_pool:
                    connection = self._connection_pool.pop()
                    if await self._validate_connection(connection):
                        acquired_from_pool = True
                        break
                    else:
                        # Connection is stale, close it
                        try:
                            await connection.close()
                        except Exception:
                            pass
                        connection = None

                # Create new connection if none available from pool
                if connection is None:
                    connection = await self._create_connection()
                    logger.debug("Created new database connection")

            # Track connection usage for monitoring
            start_time = time.time()

            yield connection

            # Log slow operations
            duration = time.time() - start_time
            if duration > 5.0:  # Log operations taking more than 5 seconds
                logger.warning(f"Slow database operation detected: {duration:.2f}s")

        except Exception as e:
            self._record_error()
            logger.error(f"Database connection error: {e}")

            if connection:
                try:
                    await connection.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")

            # If this was a connection error, try to recover
            if isinstance(e, (aiosqlite.Error, sqlite3.Error)):
                await self._handle_connection_error(e)

            raise DatabaseConnectionError(f"Database operation failed: {e}")

        finally:
            if connection:
                try:
                    # Return connection to pool if it's still healthy and pool isn't full
                    async with self._pool_lock:
                        if len(
                            self._connection_pool
                        ) < self._pool_size and await self._validate_connection(
                            connection
                        ):
                            self._connection_pool.append(connection)
                        else:
                            await connection.close()
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")
                    try:
                        await connection.close()
                    except Exception:
                        pass

    def _record_error(self):
        """Record database error for monitoring."""
        current_time = datetime.now()
        self._error_count += 1
        self._last_error_time = current_time

        # Reset error count if it's been more than an hour
        if self._last_error_time and current_time - self._last_error_time > timedelta(
            hours=1
        ):
            self._error_count = 1

    async def _handle_connection_error(self, error: Exception):
        """Handle database connection errors with recovery attempts."""
        logger.warning(f"Handling database connection error: {error}")

        # Check if we're hitting too many errors
        if self._error_count > self._max_errors_per_hour:
            logger.critical("Too many database errors detected, initiating recovery")
            await self._emergency_recovery()

        # Clear the connection pool to force new connections
        await self._clear_connection_pool()

        # Run integrity check if we haven't recently
        if (
            not self._last_integrity_check
            or datetime.now() - self._last_integrity_check
            > self._integrity_check_interval
        ):
            try:
                await self.check_database_integrity()
            except Exception as integrity_error:
                logger.error(
                    f"Integrity check failed during error recovery: {integrity_error}"
                )

    async def _clear_connection_pool(self):
        """Clear all connections from the pool."""
        async with self._pool_lock:
            while self._connection_pool:
                conn = self._connection_pool.pop()
                try:
                    await conn.close()
                except Exception:
                    pass
        logger.info("Database connection pool cleared")

    async def _emergency_recovery(self):
        """Perform emergency database recovery procedures."""
        logger.critical("Initiating emergency database recovery")

        try:
            # Clear all connections
            await self._clear_connection_pool()

            # Create backup before recovery
            backup_path = await self.backup_database()
            logger.info(f"Emergency backup created: {backup_path}")

            # Check if database file is accessible
            if not os.path.exists(self.db_path):
                raise DatabaseRecoveryError("Database file is missing")

            # Try to repair database
            await self._repair_database()

            # Reset error counter
            self._error_count = 0

            logger.info("Emergency database recovery completed successfully")

        except Exception as e:
            logger.critical(f"Emergency database recovery failed: {e}")
            raise DatabaseRecoveryError(f"Emergency recovery failed: {e}")

    async def _repair_database(self):
        """Attempt to repair database corruption."""
        try:
            # Use sqlite3 directly for repair operations
            temp_db_path = f"{self.db_path}.repair"

            # Create a new database and copy data
            with sqlite3.connect(temp_db_path) as temp_conn:
                temp_conn.execute("PRAGMA journal_mode = DELETE")

                # Try to dump and restore data
                with sqlite3.connect(self.db_path) as source_conn:
                    # Get schema
                    schema_cursor = source_conn.execute(
                        "SELECT sql FROM sqlite_master WHERE type='table'"
                    )

                    for row in schema_cursor:
                        if row[0]:  # Skip None values
                            temp_conn.execute(row[0])

                    # Copy data table by table
                    tables_cursor = source_conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )

                    for table_row in tables_cursor:
                        table_name = table_row[0]
                        try:
                            data_cursor = source_conn.execute(
                                f"SELECT * FROM {table_name}"
                            )
                            rows = data_cursor.fetchall()

                            if rows:
                                placeholders = ",".join(["?" for _ in rows[0]])
                                temp_conn.executemany(
                                    f"INSERT INTO {table_name} VALUES ({placeholders})",
                                    rows,
                                )
                        except sqlite3.Error as e:
                            logger.warning(f"Could not copy table {table_name}: {e}")

                    temp_conn.commit()

            # Replace original with repaired database
            shutil.move(temp_db_path, self.db_path)
            logger.info("Database repair completed successfully")

        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
            raise DatabaseRecoveryError(f"Database repair failed: {e}")

    @retry_on_database_error(max_retries=3)
    async def initialize_database(self):
        """Initialize the database with required tables and schema with error handling."""
        try:
            # Check if database file exists and is accessible
            if os.path.exists(self.db_path):
                # Verify database is not corrupted
                if not await self.check_database_integrity():
                    logger.warning("Database corruption detected during initialization")
                    await self._handle_corrupted_database()

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
                else:
                    logger.info(
                        f"Database already at current version {self.schema_version}"
                    )

            # Perform initial integrity check
            await self.check_database_integrity()

            # Create initial backup if auto-backup is enabled
            if self._auto_backup_enabled and not self._last_backup:
                try:
                    await self.backup_database()
                    self._last_backup = datetime.now()
                except Exception as e:
                    logger.warning(f"Initial backup failed: {e}")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")

    async def _handle_corrupted_database(self):
        """Handle corrupted database by attempting recovery."""
        logger.warning("Handling corrupted database")

        try:
            # Create backup of corrupted database for analysis
            corrupted_backup = f"{self.db_path}.corrupted_{int(time.time())}"
            shutil.copy2(self.db_path, corrupted_backup)
            logger.info(f"Corrupted database backed up to: {corrupted_backup}")

            # Try to repair the database
            await self._repair_database()

        except Exception as repair_error:
            logger.error(f"Database repair failed: {repair_error}")

            # Try to restore from most recent backup
            backup_restored = await self._restore_from_latest_backup()
            if not backup_restored:
                # Last resort: create fresh database
                logger.warning("Creating fresh database as last resort")
                os.remove(self.db_path)

    async def _restore_from_latest_backup(self) -> bool:
        """Restore database from the most recent backup."""
        try:
            backup_dir = "data/backups"
            if not os.path.exists(backup_dir):
                return False

            # Find most recent backup
            backup_files = [f for f in os.listdir(backup_dir) if f.endswith(".db")]
            if not backup_files:
                return False

            # Sort by modification time (most recent first)
            backup_files.sort(
                key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
                reverse=True,
            )
            latest_backup = os.path.join(backup_dir, backup_files[0])

            # Restore from backup
            success = await self.restore_database(latest_backup)
            if success:
                logger.info(f"Database restored from backup: {latest_backup}")

            return success

        except Exception as e:
            logger.error(f"Failed to restore from latest backup: {e}")
            return False

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

    @retry_on_database_error(max_retries=2)
    async def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the database with integrity verification."""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data/backups/trivia_backup_{timestamp}.db"

        # Ensure backup directory exists
        try:
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        except OSError as e:
            raise DatabaseError(f"Cannot create backup directory: {e}")

        try:
            # Check source database integrity before backup
            if not await self.check_database_integrity():
                logger.warning(
                    "Source database has integrity issues, backup may be corrupted"
                )

            # Use SQLite's backup API for consistent backup
            async with self.get_connection() as source_conn:
                # Create backup using SQLite's backup API
                backup_conn = await aiosqlite.connect(backup_path)
                try:
                    await source_conn.backup(backup_conn)
                    await backup_conn.close()

                    # Verify backup integrity
                    backup_manager = DatabaseManager(backup_path)
                    if await backup_manager.check_database_integrity():
                        logger.info(f"Database backed up successfully to {backup_path}")

                        # Create metadata file
                        metadata_path = f"{backup_path}.meta"
                        with open(metadata_path, "w") as meta_file:
                            meta_file.write(
                                f"backup_time={datetime.now().isoformat()}\n"
                            )
                            meta_file.write(f"source_db={self.db_path}\n")
                            meta_file.write(
                                f"schema_version={await self._get_schema_version(source_conn)}\n"
                            )

                        self._last_backup = datetime.now()
                        return backup_path
                    else:
                        os.remove(backup_path)
                        raise DatabaseError("Backup verification failed")

                except Exception as e:
                    await backup_conn.close()
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    raise

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            raise DatabaseError(f"Database backup failed: {e}")

    async def cleanup_old_backups(self, keep_count: int = 10):
        """Clean up old backup files, keeping only the most recent ones."""
        try:
            backup_dir = "data/backups"
            if not os.path.exists(backup_dir):
                return

            # Get all backup files
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.endswith(".db") and "backup" in filename:
                    filepath = os.path.join(backup_dir, filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # Remove old backups
            removed_count = 0
            for filepath, _ in backup_files[keep_count:]:
                try:
                    os.remove(filepath)
                    # Also remove metadata file if it exists
                    meta_path = f"{filepath}.meta"
                    if os.path.exists(meta_path):
                        os.remove(meta_path)
                    removed_count += 1
                except OSError as e:
                    logger.warning(f"Failed to remove old backup {filepath}: {e}")

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old backup files")

        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

    async def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup with verification."""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Verify backup integrity before restore
            backup_manager = DatabaseManager(backup_path)
            if not await backup_manager.check_database_integrity():
                logger.error(f"Backup file {backup_path} is corrupted")
                return False

            # Create backup of current database before restore
            current_backup = None
            if os.path.exists(self.db_path):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    current_backup = f"data/backups/pre_restore_backup_{timestamp}.db"
                    shutil.copy2(self.db_path, current_backup)
                    logger.info(f"Current database backed up to {current_backup}")
                except Exception as e:
                    logger.warning(f"Failed to backup current database: {e}")

            # Close all connections before restore
            await self.close_all_connections()

            try:
                # Restore the backup
                shutil.copy2(backup_path, self.db_path)
                logger.info(f"Database restored from {backup_path}")

                # Reinitialize after restore
                await self.initialize_database()

                # Verify restored database
                if await self.check_database_integrity():
                    logger.info("Database restore completed successfully")
                    return True
                else:
                    logger.error("Restored database failed integrity check")
                    # Try to restore from current backup if available
                    if current_backup and os.path.exists(current_backup):
                        shutil.copy2(current_backup, self.db_path)
                        logger.info("Restored from pre-restore backup")
                    return False

            except Exception as restore_error:
                logger.error(f"Database restore failed: {restore_error}")
                # Try to restore from current backup if available
                if current_backup and os.path.exists(current_backup):
                    try:
                        shutil.copy2(current_backup, self.db_path)
                        await self.initialize_database()
                        logger.info("Restored from pre-restore backup after failure")
                    except Exception as recovery_error:
                        logger.error(
                            f"Failed to recover from pre-restore backup: {recovery_error}"
                        )
                return False

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False

    async def check_database_integrity(self) -> bool:
        """Check database integrity and return True if healthy."""
        try:
            async with self.get_connection() as conn:
                # Run integrity check
                cursor = await conn.execute("PRAGMA integrity_check")
                result = await cursor.fetchone()
                integrity_ok = result[0] == "ok"

                # Run foreign key check
                cursor = await conn.execute("PRAGMA foreign_key_check")
                fk_violations = await cursor.fetchall()
                fk_ok = len(fk_violations) == 0

                # Check for table existence
                cursor = await conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('users', 'questions', 'user_achievements', 'weekly_rankings')
                """)
                tables = await cursor.fetchall()
                tables_ok = len(tables) >= 4  # Should have at least 4 core tables

                is_healthy = integrity_ok and fk_ok and tables_ok

                if is_healthy:
                    logger.debug("Database integrity check passed")
                    self._last_integrity_check = datetime.now()
                else:
                    issues = []
                    if not integrity_ok:
                        issues.append(f"integrity: {result[0]}")
                    if not fk_ok:
                        issues.append(f"foreign key violations: {len(fk_violations)}")
                    if not tables_ok:
                        issues.append(
                            f"missing tables: expected 4, found {len(tables)}"
                        )

                    logger.warning(
                        f"Database integrity check failed: {', '.join(issues)}"
                    )

                return is_healthy

        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            return False

    async def perform_maintenance(self):
        """Perform routine database maintenance tasks."""
        try:
            logger.info("Starting database maintenance")

            # Check if maintenance is needed
            current_time = datetime.now()

            # Integrity check
            if (
                not self._last_integrity_check
                or current_time - self._last_integrity_check
                > self._integrity_check_interval
            ):
                if not await self.check_database_integrity():
                    logger.warning(
                        "Database integrity issues detected during maintenance"
                    )
                    await self._handle_corrupted_database()

            # Auto backup
            if self._auto_backup_enabled and (
                not self._last_backup
                or current_time - self._last_backup > self._backup_interval
            ):
                try:
                    await self.backup_database()
                    await self.cleanup_old_backups()
                except Exception as e:
                    logger.error(f"Auto backup failed during maintenance: {e}")

            # Optimize database
            await self._optimize_database()

            # Clean up old data
            await self._cleanup_old_data()

            logger.info("Database maintenance completed successfully")

        except Exception as e:
            logger.error(f"Database maintenance failed: {e}")

    async def _optimize_database(self):
        """Optimize database performance."""
        try:
            async with self.get_connection() as conn:
                # Analyze tables for query optimization
                await conn.execute("ANALYZE")

                # Vacuum database to reclaim space (only if not in WAL mode during active use)
                cursor = await conn.execute("PRAGMA journal_mode")
                journal_mode = await cursor.fetchone()

                if journal_mode[0].lower() != "wal":
                    await conn.execute("VACUUM")
                    logger.debug("Database vacuumed")

                await conn.commit()
                logger.debug("Database optimization completed")

        except Exception as e:
            logger.warning(f"Database optimization failed: {e}")

    async def _cleanup_old_data(self):
        """Clean up old data that's no longer needed."""
        try:
            async with self.get_connection() as conn:
                # Clean up old game sessions (older than 7 days)
                cutoff_date = datetime.now() - timedelta(days=7)
                cursor = await conn.execute(
                    "DELETE FROM game_sessions WHERE start_time < ? AND is_completed = TRUE",
                    (cutoff_date,),
                )
                deleted_sessions = cursor.rowcount

                # Clean up old weekly rankings (keep last 12 weeks)
                cutoff_week = datetime.now() - timedelta(weeks=12)
                cursor = await conn.execute(
                    "DELETE FROM weekly_rankings WHERE week_start < ?",
                    (cutoff_week.date(),),
                )
                deleted_rankings = cursor.rowcount

                await conn.commit()

                if deleted_sessions > 0 or deleted_rankings > 0:
                    logger.info(
                        f"Cleaned up old data: {deleted_sessions} game sessions, {deleted_rankings} weekly rankings"
                    )

        except Exception as e:
            logger.warning(f"Data cleanup failed: {e}")

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics and health information."""
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
                    try:
                        cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                        count = await cursor.fetchone()
                        stats[f"{table}_count"] = count[0]
                    except Exception as e:
                        logger.warning(f"Failed to get count for table {table}: {e}")
                        stats[f"{table}_count"] = -1

                # Get database size information
                try:
                    cursor = await conn.execute("PRAGMA page_count")
                    page_count = await cursor.fetchone()
                    cursor = await conn.execute("PRAGMA page_size")
                    page_size = await cursor.fetchone()
                    stats["database_size_bytes"] = page_count[0] * page_size[0]
                    stats["database_size_mb"] = round(
                        stats["database_size_bytes"] / (1024 * 1024), 2
                    )
                except Exception as e:
                    logger.warning(f"Failed to get database size: {e}")
                    stats["database_size_bytes"] = -1

                # Get schema version
                try:
                    stats["schema_version"] = await self._get_schema_version(conn)
                except Exception as e:
                    logger.warning(f"Failed to get schema version: {e}")
                    stats["schema_version"] = -1

                # Get connection pool stats
                stats["connection_pool_size"] = len(self._connection_pool)
                stats["max_pool_size"] = self._pool_size

                # Get error tracking stats
                stats["error_count"] = self._error_count
                stats["last_error_time"] = (
                    self._last_error_time.isoformat() if self._last_error_time else None
                )

                # Get maintenance stats
                stats["last_integrity_check"] = (
                    self._last_integrity_check.isoformat()
                    if self._last_integrity_check
                    else None
                )
                stats["last_backup"] = (
                    self._last_backup.isoformat() if self._last_backup else None
                )
                stats["auto_backup_enabled"] = self._auto_backup_enabled

                # Get database configuration
                try:
                    cursor = await conn.execute("PRAGMA journal_mode")
                    journal_mode = await cursor.fetchone()
                    stats["journal_mode"] = journal_mode[0]

                    cursor = await conn.execute("PRAGMA synchronous")
                    synchronous = await cursor.fetchone()
                    stats["synchronous_mode"] = synchronous[0]

                    cursor = await conn.execute("PRAGMA cache_size")
                    cache_size = await cursor.fetchone()
                    stats["cache_size"] = cache_size[0]
                except Exception as e:
                    logger.warning(f"Failed to get database configuration: {e}")

                return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}

    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall database health status."""
        try:
            health = {"status": "unknown", "issues": [], "recommendations": []}

            # Check basic connectivity
            try:
                async with self.get_connection() as conn:
                    await conn.execute("SELECT 1")
                health["connectivity"] = "ok"
            except Exception as e:
                health["connectivity"] = "failed"
                health["issues"].append(f"Database connectivity failed: {e}")
                health["status"] = "critical"
                return health

            # Check integrity
            integrity_ok = await self.check_database_integrity()
            health["integrity"] = "ok" if integrity_ok else "failed"
            if not integrity_ok:
                health["issues"].append("Database integrity check failed")
                health["recommendations"].append(
                    "Run database repair or restore from backup"
                )

            # Check error rate
            if self._error_count > self._max_errors_per_hour / 2:
                health["issues"].append(f"High error rate: {self._error_count} errors")
                health["recommendations"].append(
                    "Monitor database operations and check logs"
                )

            # Check backup status
            if self._auto_backup_enabled:
                if not self._last_backup:
                    health["issues"].append("No backups created yet")
                    health["recommendations"].append("Create initial backup")
                elif datetime.now() - self._last_backup > self._backup_interval * 2:
                    health["issues"].append("Backups are overdue")
                    health["recommendations"].append("Check backup system")

            # Check maintenance status
            if (
                self._last_integrity_check
                and datetime.now() - self._last_integrity_check
                > self._integrity_check_interval * 2
            ):
                health["issues"].append("Integrity checks are overdue")
                health["recommendations"].append("Run database maintenance")

            # Determine overall status
            if not health["issues"]:
                health["status"] = "healthy"
            elif len(health["issues"]) <= 2 and integrity_ok:
                health["status"] = "warning"
            else:
                health["status"] = "critical"

            return health

        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {
                "status": "critical",
                "issues": [f"Health check failed: {e}"],
                "recommendations": ["Check database system and logs"],
            }

    async def close_all_connections(self):
        """Close all connections in the pool safely."""
        async with self._pool_lock:
            closed_count = 0
            while self._connection_pool:
                conn = self._connection_pool.pop()
                try:
                    await conn.close()
                    closed_count += 1
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e}")

            if closed_count > 0:
                logger.info(f"Closed {closed_count} database connections")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_database()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_all_connections()
        if exc_type:
            logger.error(
                f"Database manager exiting with error: {exc_type.__name__}: {exc_val}"
            )
        return False


# Global database manager instance
db_manager = DatabaseManager()
