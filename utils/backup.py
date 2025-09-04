"""
Database backup and recovery utilities for the Enhanced Trivia System.
Provides automated backup scheduling and recovery mechanisms.
"""

import os
import shutil
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import glob

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages database backups and recovery operations."""

    def __init__(self, db_manager, backup_dir: str = "data/backups"):
        self.db_manager = db_manager
        self.backup_dir = backup_dir
        self.max_backups = 30  # Keep 30 days of backups

        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)

    async def create_backup(self, backup_type: str = "manual") -> str:
        """Create a database backup with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"trivia_{backup_type}_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        try:
            # Create the backup
            await self.db_manager.backup_database(backup_path)

            # Create metadata file
            await self._create_backup_metadata(backup_path, backup_type)

            logger.info(f"Created {backup_type} backup: {backup_filename}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    async def _create_backup_metadata(self, backup_path: str, backup_type: str):
        """Create metadata file for the backup."""
        metadata_path = backup_path + ".meta"

        # Get database stats
        stats = await self.db_manager.get_database_stats()

        metadata = {
            "backup_type": backup_type,
            "created_at": datetime.now().isoformat(),
            "database_stats": stats,
            "backup_size": os.path.getsize(backup_path)
            if os.path.exists(backup_path)
            else 0,
        }

        try:
            import json

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to create backup metadata: {e}")

    async def create_daily_backup(self) -> Optional[str]:
        """Create a daily backup if one doesn't exist for today."""
        today = datetime.now().strftime("%Y%m%d")
        existing_backups = glob.glob(
            os.path.join(self.backup_dir, f"trivia_daily_{today}_*.db")
        )

        if existing_backups:
            logger.info(f"Daily backup already exists for {today}")
            return existing_backups[0]

        return await self.create_backup("daily")

    async def create_weekly_backup(self) -> Optional[str]:
        """Create a weekly backup if one doesn't exist for this week."""
        # Get Monday of current week
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        week_str = monday.strftime("%Y%m%d")

        existing_backups = glob.glob(
            os.path.join(self.backup_dir, f"trivia_weekly_{week_str}_*.db")
        )

        if existing_backups:
            logger.info(f"Weekly backup already exists for week of {week_str}")
            return existing_backups[0]

        return await self.create_backup("weekly")

    async def cleanup_old_backups(self):
        """Remove old backups beyond the retention limit."""
        try:
            backup_files = glob.glob(os.path.join(self.backup_dir, "trivia_*.db"))
            backup_files.sort(key=os.path.getmtime, reverse=True)

            # Keep the most recent backups
            files_to_delete = backup_files[self.max_backups :]

            for backup_file in files_to_delete:
                try:
                    os.remove(backup_file)
                    # Also remove metadata file if it exists
                    meta_file = backup_file + ".meta"
                    if os.path.exists(meta_file):
                        os.remove(meta_file)
                    logger.info(f"Deleted old backup: {os.path.basename(backup_file)}")
                except Exception as e:
                    logger.warning(f"Failed to delete backup {backup_file}: {e}")

            if files_to_delete:
                logger.info(f"Cleaned up {len(files_to_delete)} old backups")

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")

    async def list_backups(self) -> List[dict]:
        """List all available backups with metadata."""
        backups = []
        backup_files = glob.glob(os.path.join(self.backup_dir, "trivia_*.db"))
        backup_files.sort(key=os.path.getmtime, reverse=True)

        for backup_file in backup_files:
            backup_info = {
                "filename": os.path.basename(backup_file),
                "path": backup_file,
                "size": os.path.getsize(backup_file),
                "created_at": datetime.fromtimestamp(os.path.getmtime(backup_file)),
                "type": "unknown",
            }

            # Try to load metadata
            meta_file = backup_file + ".meta"
            if os.path.exists(meta_file):
                try:
                    import json

                    with open(meta_file, "r") as f:
                        metadata = json.load(f)
                        backup_info.update(metadata)
                except Exception as e:
                    logger.warning(f"Failed to read metadata for {backup_file}: {e}")

            backups.append(backup_info)

        return backups

    async def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from a specific backup."""
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            # Create a backup of current database before restore
            pre_restore_backup = await self.create_backup("pre_restore")
            logger.info(f"Created pre-restore backup: {pre_restore_backup}")

            # Perform the restore
            success = await self.db_manager.restore_database(backup_path)

            if success:
                logger.info(f"Successfully restored database from {backup_path}")

                # Verify the restored database
                integrity_ok = await self.db_manager.check_database_integrity()
                if not integrity_ok:
                    logger.error("Restored database failed integrity check")
                    return False

                return True
            else:
                logger.error(f"Failed to restore database from {backup_path}")
                return False

        except Exception as e:
            logger.error(f"Error during database restore: {e}")
            return False

    async def get_latest_backup(
        self, backup_type: Optional[str] = None
    ) -> Optional[str]:
        """Get the path to the latest backup, optionally filtered by type."""
        pattern = f"trivia_{backup_type}_*.db" if backup_type else "trivia_*.db"
        backup_files = glob.glob(os.path.join(self.backup_dir, pattern))

        if not backup_files:
            return None

        # Return the most recent backup
        latest_backup = max(backup_files, key=os.path.getmtime)
        return latest_backup

    async def verify_backup(self, backup_path: str) -> bool:
        """Verify that a backup file is valid and not corrupted."""
        if not os.path.exists(backup_path):
            return False

        try:
            # Try to open the backup database and run a simple query
            import aiosqlite

            async with aiosqlite.connect(backup_path) as conn:
                cursor = await conn.execute("PRAGMA integrity_check")
                result = await cursor.fetchone()
                return result[0] == "ok"

        except Exception as e:
            logger.error(f"Backup verification failed for {backup_path}: {e}")
            return False

    async def schedule_automatic_backups(self):
        """Schedule automatic daily and weekly backups."""
        logger.info("Starting automatic backup scheduler")

        while True:
            try:
                # Create daily backup
                await self.create_daily_backup()

                # Create weekly backup on Mondays
                if datetime.now().weekday() == 0:  # Monday
                    await self.create_weekly_backup()

                # Cleanup old backups
                await self.cleanup_old_backups()

                # Wait 24 hours before next check
                await asyncio.sleep(24 * 60 * 60)

            except Exception as e:
                logger.error(f"Error in automatic backup scheduler: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(60 * 60)


class RecoveryManager:
    """Manages database recovery operations and emergency procedures."""

    def __init__(self, db_manager, backup_manager):
        self.db_manager = db_manager
        self.backup_manager = backup_manager

    async def emergency_recovery(self) -> bool:
        """Perform emergency recovery using the latest available backup."""
        logger.warning("Starting emergency database recovery")

        try:
            # Check if current database is corrupted
            integrity_ok = await self.db_manager.check_database_integrity()

            if integrity_ok:
                logger.info("Current database is healthy, no recovery needed")
                return True

            # Find the latest backup
            latest_backup = await self.backup_manager.get_latest_backup()

            if not latest_backup:
                logger.error("No backups available for recovery")
                return False

            # Verify the backup before using it
            backup_valid = await self.backup_manager.verify_backup(latest_backup)

            if not backup_valid:
                logger.error(f"Latest backup is corrupted: {latest_backup}")
                # Try to find an older valid backup
                backups = await self.backup_manager.list_backups()
                for backup in backups[1:]:  # Skip the first (latest) one
                    if await self.backup_manager.verify_backup(backup["path"]):
                        latest_backup = backup["path"]
                        logger.info(f"Using older backup: {latest_backup}")
                        break
                else:
                    logger.error("No valid backups found for recovery")
                    return False

            # Perform the recovery
            success = await self.backup_manager.restore_from_backup(latest_backup)

            if success:
                logger.info("Emergency recovery completed successfully")
                return True
            else:
                logger.error("Emergency recovery failed")
                return False

        except Exception as e:
            logger.error(f"Emergency recovery failed with error: {e}")
            return False

    async def create_recovery_point(self, description: str = "Recovery point") -> str:
        """Create a recovery point before making significant changes."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = await self.backup_manager.create_backup(f"recovery_{timestamp}")
        logger.info(f"Created recovery point: {description}")
        return backup_path
