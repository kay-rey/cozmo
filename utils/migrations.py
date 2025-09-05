"""
Database migration system for the Enhanced Trivia System.
Handles schema updates and data migrations between versions.
"""

import logging
from typing import Dict, List, Callable
from datetime import datetime
import aiosqlite

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database schema migrations."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.migrations: Dict[int, Callable] = {
            # Future migrations will be added here
            # Example: 2: self._migrate_to_v2,
        }

    async def run_migrations(
        self, conn: aiosqlite.Connection, from_version: int, to_version: int
    ):
        """Run all migrations from from_version to to_version."""
        logger.info(f"Running migrations from version {from_version} to {to_version}")

        for version in range(from_version + 1, to_version + 1):
            if version in self.migrations:
                logger.info(f"Applying migration to version {version}")
                await self.migrations[version](conn)
                await self._update_schema_version(conn, version)
            else:
                logger.warning(f"No migration found for version {version}")

    async def _update_schema_version(self, conn: aiosqlite.Connection, version: int):
        """Update the schema version in the database."""
        await conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)", (version,)
        )
        await conn.commit()

    async def _get_schema_version(self, conn: aiosqlite.Connection) -> int:
        """Get the current schema version."""
        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        result = await cursor.fetchone()
        return result[0] if result[0] is not None else 0

    # Example migration method (for future use)
    async def _migrate_to_v2(self, conn: aiosqlite.Connection):
        """Example migration to version 2."""
        # This is a placeholder for future migrations
        # Example: Add a new column to users table
        # await conn.execute("ALTER TABLE users ADD COLUMN new_column TEXT DEFAULT ''")
        # await conn.commit()
        pass

    async def create_migration_backup(self, version: int) -> str:
        """Create a backup before running migrations."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"data/backups/pre_migration_v{version}_{timestamp}.db"
        return await self.db_manager.backup_database(backup_path)

    async def rollback_migration(self, backup_path: str) -> bool:
        """Rollback to a previous backup if migration fails."""
        logger.warning(f"Rolling back migration using backup: {backup_path}")
        return await self.db_manager.restore_database(backup_path)


# Migration utilities
async def safe_add_column(
    conn: aiosqlite.Connection,
    table: str,
    column: str,
    column_type: str,
    default_value: str = "",
):
    """Safely add a column to a table if it doesn't exist."""
    try:
        # Check if column exists
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        if column not in column_names:
            await conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {column_type} DEFAULT {default_value}"
            )
            await conn.commit()
            logger.info(f"Added column {column} to table {table}")
        else:
            logger.info(f"Column {column} already exists in table {table}")

    except Exception as e:
        logger.error(f"Failed to add column {column} to table {table}: {e}")
        raise


async def safe_create_index(
    conn: aiosqlite.Connection, index_name: str, table: str, columns: str
):
    """Safely create an index if it doesn't exist."""
    try:
        await conn.execute(
            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({columns})"
        )
        await conn.commit()
        logger.info(f"Created index {index_name}")
    except Exception as e:
        logger.error(f"Failed to create index {index_name}: {e}")
        raise
