#!/usr/bin/env python3
"""
Database migration script for Enhanced Trivia System.
Handles schema updates and data preservation during deployments.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import DatabaseManager
from utils.backup import BackupManager
from utils.migrations import MigrationManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main migration function."""
    print("Enhanced Trivia System - Database Migration Tool")
    print("=" * 50)

    # Initialize managers
    db_manager = DatabaseManager()
    backup_manager = BackupManager(db_manager)
    migration_manager = MigrationManager(db_manager)

    try:
        # Step 1: Create pre-migration backup
        print("Creating pre-migration backup...")
        backup_path = await backup_manager.create_backup("pre_migration")
        print(f"✓ Backup created: {backup_path}")

        # Step 2: Check database integrity
        print("Checking database integrity...")
        integrity_ok = await db_manager.check_database_integrity()
        if not integrity_ok:
            print("✗ Database integrity check failed!")
            print("Please fix database issues before migration.")
            return False
        print("✓ Database integrity check passed")

        # Step 3: Get current schema version
        async with db_manager.get_connection() as conn:
            current_version = await migration_manager._get_schema_version(conn)
            target_version = db_manager.schema_version

        print(f"Current schema version: {current_version}")
        print(f"Target schema version: {target_version}")

        if current_version >= target_version:
            print("✓ Database is already up to date")
            return True

        # Step 4: Run migrations
        print(f"Running migrations from v{current_version} to v{target_version}...")
        async with db_manager.get_connection() as conn:
            await migration_manager.run_migrations(
                conn, current_version, target_version
            )
        print("✓ Migrations completed successfully")

        # Step 5: Verify migration
        print("Verifying migration...")
        integrity_ok = await db_manager.check_database_integrity()
        if not integrity_ok:
            print("✗ Post-migration integrity check failed!")
            print("Rolling back to pre-migration backup...")
            await backup_manager.restore_from_backup(backup_path)
            return False
        print("✓ Migration verification passed")

        # Step 6: Create post-migration backup
        print("Creating post-migration backup...")
        post_backup = await backup_manager.create_backup("post_migration")
        print(f"✓ Post-migration backup created: {post_backup}")

        print("\n✓ Database migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n✗ Migration failed: {e}")

        # Attempt rollback
        try:
            print("Attempting rollback...")
            await backup_manager.restore_from_backup(backup_path)
            print("✓ Rollback completed")
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {rollback_error}")
            print(f"✗ Rollback failed: {rollback_error}")

        return False

    finally:
        await db_manager.close_all_connections()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
