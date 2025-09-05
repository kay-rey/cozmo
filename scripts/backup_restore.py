#!/usr/bin/env python3
"""
Database backup and restoration utility for Enhanced Trivia System.
Provides command-line interface for backup operations.
"""

import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import DatabaseManager
from utils.backup import BackupManager, RecoveryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_backup(backup_type: str = "manual"):
    """Create a database backup."""
    db_manager = DatabaseManager()
    backup_manager = BackupManager(db_manager)

    try:
        print(f"Creating {backup_type} backup...")
        backup_path = await backup_manager.create_backup(backup_type)
        print(f"✓ Backup created successfully: {backup_path}")

        # Verify backup
        if await backup_manager.verify_backup(backup_path):
            print("✓ Backup verification passed")
        else:
            print("✗ Backup verification failed")
            return False

        return True

    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        print(f"✗ Backup failed: {e}")
        return False

    finally:
        await db_manager.close_all_connections()


async def restore_backup(backup_path: str):
    """Restore database from backup."""
    db_manager = DatabaseManager()
    backup_manager = BackupManager(db_manager)

    try:
        if not os.path.exists(backup_path):
            print(f"✗ Backup file not found: {backup_path}")
            return False

        print(f"Restoring from backup: {backup_path}")

        # Verify backup before restore
        if not await backup_manager.verify_backup(backup_path):
            print("✗ Backup verification failed - cannot restore")
            return False

        success = await backup_manager.restore_from_backup(backup_path)

        if success:
            print("✓ Database restored successfully")
        else:
            print("✗ Database restore failed")

        return success

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        print(f"✗ Restore failed: {e}")
        return False

    finally:
        await db_manager.close_all_connections()


async def list_backups():
    """List all available backups."""
    db_manager = DatabaseManager()
    backup_manager = BackupManager(db_manager)

    try:
        backups = await backup_manager.list_backups()

        if not backups:
            print("No backups found")
            return

        print("Available backups:")
        print("-" * 80)
        print(f"{'Filename':<40} {'Type':<15} {'Size':<10} {'Created':<20}")
        print("-" * 80)

        for backup in backups:
            size_mb = backup["size"] / (1024 * 1024)
            created = backup["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            backup_type = backup.get("type", "unknown")

            print(
                f"{backup['filename']:<40} {backup_type:<15} {size_mb:>8.1f}MB {created:<20}"
            )

    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        print(f"✗ Failed to list backups: {e}")

    finally:
        await db_manager.close_all_connections()


async def cleanup_backups(keep_count: int = 10):
    """Clean up old backups."""
    db_manager = DatabaseManager()
    backup_manager = BackupManager(db_manager)

    try:
        print(f"Cleaning up old backups (keeping {keep_count} most recent)...")
        await backup_manager.cleanup_old_backups()
        print("✓ Backup cleanup completed")

    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")
        print(f"✗ Backup cleanup failed: {e}")

    finally:
        await db_manager.close_all_connections()


async def emergency_recovery():
    """Perform emergency database recovery."""
    db_manager = DatabaseManager()
    backup_manager = BackupManager(db_manager)
    recovery_manager = RecoveryManager(db_manager, backup_manager)

    try:
        print("Starting emergency recovery...")
        success = await recovery_manager.emergency_recovery()

        if success:
            print("✓ Emergency recovery completed successfully")
        else:
            print("✗ Emergency recovery failed")

        return success

    except Exception as e:
        logger.error(f"Emergency recovery failed: {e}")
        print(f"✗ Emergency recovery failed: {e}")
        return False

    finally:
        await db_manager.close_all_connections()


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Database backup and restore utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a database backup")
    backup_parser.add_argument(
        "--type",
        default="manual",
        choices=["manual", "daily", "weekly", "pre_migration", "post_migration"],
        help="Type of backup to create",
    )

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_path", help="Path to backup file")

    # List command
    subparsers.add_parser("list", help="List available backups")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old backups")
    cleanup_parser.add_argument(
        "--keep", type=int, default=10, help="Number of backups to keep (default: 10)"
    )

    # Emergency recovery command
    subparsers.add_parser("emergency", help="Perform emergency recovery")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    if args.command == "backup":
        success = asyncio.run(create_backup(args.type))
    elif args.command == "restore":
        success = asyncio.run(restore_backup(args.backup_path))
    elif args.command == "list":
        asyncio.run(list_backups())
        success = True
    elif args.command == "cleanup":
        asyncio.run(cleanup_backups(args.keep))
        success = True
    elif args.command == "emergency":
        success = asyncio.run(emergency_recovery())
    else:
        parser.print_help()
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
