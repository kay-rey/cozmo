#!/usr/bin/env python3
"""
Health check script for Enhanced Trivia System.
Monitors database health, performance, and system status.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import DatabaseManager
from utils.backup import BackupManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs comprehensive health checks on the trivia system."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.backup_manager = BackupManager(self.db_manager)
        self.checks = []
        self.warnings = []
        self.errors = []

    def add_check(
        self, name: str, status: str, message: str = "", details: dict = None
    ):
        """Add a health check result."""
        check = {
            "name": name,
            "status": status,  # 'OK', 'WARNING', 'ERROR'
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(),
        }
        self.checks.append(check)

        if status == "WARNING":
            self.warnings.append(check)
        elif status == "ERROR":
            self.errors.append(check)

    async def check_database_connectivity(self):
        """Check if database is accessible and responsive."""
        try:
            start_time = time.time()
            async with self.db_manager.get_connection() as conn:
                cursor = await conn.execute("SELECT 1")
                await cursor.fetchone()

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            if response_time < 100:
                self.add_check(
                    "Database Connectivity",
                    "OK",
                    f"Response time: {response_time:.2f}ms",
                )
            elif response_time < 500:
                self.add_check(
                    "Database Connectivity",
                    "WARNING",
                    f"Slow response time: {response_time:.2f}ms",
                )
            else:
                self.add_check(
                    "Database Connectivity",
                    "ERROR",
                    f"Very slow response time: {response_time:.2f}ms",
                )

        except Exception as e:
            self.add_check(
                "Database Connectivity", "ERROR", f"Cannot connect to database: {e}"
            )

    async def check_database_integrity(self):
        """Check database integrity."""
        try:
            integrity_ok = await self.db_manager.check_database_integrity()

            if integrity_ok:
                self.add_check(
                    "Database Integrity", "OK", "All integrity checks passed"
                )
            else:
                self.add_check("Database Integrity", "ERROR", "Integrity check failed")

        except Exception as e:
            self.add_check("Database Integrity", "ERROR", f"Integrity check error: {e}")

    async def check_database_size(self):
        """Check database size and growth."""
        try:
            db_path = self.db_manager.db_path

            if not os.path.exists(db_path):
                self.add_check("Database Size", "ERROR", "Database file not found")
                return

            size_bytes = os.path.getsize(db_path)
            size_mb = size_bytes / (1024 * 1024)

            # Get available disk space
            stat = os.statvfs(os.path.dirname(db_path))
            free_bytes = stat.f_bavail * stat.f_frsize
            free_gb = free_bytes / (1024 * 1024 * 1024)

            details = {"size_mb": round(size_mb, 2), "free_space_gb": round(free_gb, 2)}

            if free_gb < 1:  # Less than 1GB free
                self.add_check(
                    "Database Size",
                    "ERROR",
                    f"Low disk space: {free_gb:.2f}GB free",
                    details,
                )
            elif free_gb < 5:  # Less than 5GB free
                self.add_check(
                    "Database Size",
                    "WARNING",
                    f"Disk space getting low: {free_gb:.2f}GB free",
                    details,
                )
            else:
                self.add_check(
                    "Database Size",
                    "OK",
                    f"Database: {size_mb:.2f}MB, Free space: {free_gb:.2f}GB",
                    details,
                )

        except Exception as e:
            self.add_check("Database Size", "ERROR", f"Size check error: {e}")

    async def check_table_counts(self):
        """Check table record counts for anomalies."""
        try:
            async with self.db_manager.get_connection() as conn:
                tables = [
                    "users",
                    "questions",
                    "user_achievements",
                    "weekly_rankings",
                    "game_sessions",
                ]
                counts = {}

                for table in tables:
                    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = (await cursor.fetchone())[0]
                    counts[table] = count

                # Check for reasonable counts
                if counts["users"] == 0:
                    self.add_check(
                        "Table Counts", "WARNING", "No users in database", counts
                    )
                elif counts["questions"] == 0:
                    self.add_check(
                        "Table Counts", "ERROR", "No questions in database", counts
                    )
                else:
                    self.add_check("Table Counts", "OK", "All tables have data", counts)

        except Exception as e:
            self.add_check("Table Counts", "ERROR", f"Count check error: {e}")

    async def check_recent_backups(self):
        """Check if recent backups exist and are valid."""
        try:
            backups = await self.backup_manager.list_backups()

            if not backups:
                self.add_check("Recent Backups", "ERROR", "No backups found")
                return

            # Check most recent backup
            latest_backup = backups[0]
            backup_age = datetime.now() - latest_backup["created_at"]

            # Verify backup integrity
            backup_valid = await self.backup_manager.verify_backup(
                latest_backup["path"]
            )

            details = {
                "latest_backup": latest_backup["filename"],
                "backup_age_hours": round(backup_age.total_seconds() / 3600, 1),
                "backup_valid": backup_valid,
                "total_backups": len(backups),
            }

            if not backup_valid:
                self.add_check(
                    "Recent Backups", "ERROR", "Latest backup is corrupted", details
                )
            elif backup_age > timedelta(days=2):
                self.add_check(
                    "Recent Backups",
                    "ERROR",
                    f"Latest backup is {backup_age.days} days old",
                    details,
                )
            elif backup_age > timedelta(
                hours=25
            ):  # More than 25 hours (daily backup missed)
                self.add_check(
                    "Recent Backups",
                    "WARNING",
                    f"Latest backup is {backup_age.days} day(s) old",
                    details,
                )
            else:
                self.add_check(
                    "Recent Backups",
                    "OK",
                    f"Latest backup: {latest_backup['filename']}",
                    details,
                )

        except Exception as e:
            self.add_check("Recent Backups", "ERROR", f"Backup check error: {e}")

    async def check_connection_pool(self):
        """Check database connection pool health."""
        try:
            pool_size = len(self.db_manager._connection_pool)
            max_pool_size = self.db_manager._max_pool_size
            error_count = self.db_manager._error_count

            details = {
                "pool_size": pool_size,
                "max_pool_size": max_pool_size,
                "error_count": error_count,
            }

            if error_count > 50:  # High error count
                self.add_check(
                    "Connection Pool",
                    "ERROR",
                    f"High error count: {error_count}",
                    details,
                )
            elif error_count > 10:
                self.add_check(
                    "Connection Pool",
                    "WARNING",
                    f"Elevated error count: {error_count}",
                    details,
                )
            else:
                self.add_check(
                    "Connection Pool",
                    "OK",
                    f"Pool size: {pool_size}/{max_pool_size}",
                    details,
                )

        except Exception as e:
            self.add_check("Connection Pool", "ERROR", f"Pool check error: {e}")

    async def check_log_files(self):
        """Check log file sizes and recent entries."""
        try:
            log_dir = "logs"

            if not os.path.exists(log_dir):
                self.add_check("Log Files", "WARNING", "Log directory not found")
                return

            log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]

            if not log_files:
                self.add_check("Log Files", "WARNING", "No log files found")
                return

            total_size = 0
            latest_log = None
            latest_mtime = 0

            for log_file in log_files:
                log_path = os.path.join(log_dir, log_file)
                size = os.path.getsize(log_path)
                mtime = os.path.getmtime(log_path)

                total_size += size

                if mtime > latest_mtime:
                    latest_mtime = mtime
                    latest_log = log_file

            total_size_mb = total_size / (1024 * 1024)
            last_modified = datetime.fromtimestamp(latest_mtime)
            age = datetime.now() - last_modified

            details = {
                "total_size_mb": round(total_size_mb, 2),
                "log_count": len(log_files),
                "latest_log": latest_log,
                "last_modified_hours_ago": round(age.total_seconds() / 3600, 1),
            }

            if total_size_mb > 100:  # More than 100MB of logs
                self.add_check(
                    "Log Files",
                    "WARNING",
                    f"Large log files: {total_size_mb:.2f}MB",
                    details,
                )
            elif age > timedelta(hours=2):  # No recent log activity
                self.add_check(
                    "Log Files",
                    "WARNING",
                    f"No recent log activity: {age.total_seconds() / 3600:.1f}h ago",
                    details,
                )
            else:
                self.add_check(
                    "Log Files",
                    "OK",
                    f"{len(log_files)} log files, {total_size_mb:.2f}MB total",
                    details,
                )

        except Exception as e:
            self.add_check("Log Files", "ERROR", f"Log check error: {e}")

    async def run_all_checks(self):
        """Run all health checks."""
        print("Running Enhanced Trivia System Health Checks...")
        print("=" * 50)

        checks_to_run = [
            ("Database Connectivity", self.check_database_connectivity),
            ("Database Integrity", self.check_database_integrity),
            ("Database Size", self.check_database_size),
            ("Table Counts", self.check_table_counts),
            ("Recent Backups", self.check_recent_backups),
            ("Connection Pool", self.check_connection_pool),
            ("Log Files", self.check_log_files),
        ]

        for check_name, check_func in checks_to_run:
            try:
                print(f"Running {check_name}...", end=" ")
                await check_func()

                # Find the result for this check
                result = next((c for c in self.checks if c["name"] == check_name), None)
                if result:
                    status_symbol = (
                        "✓"
                        if result["status"] == "OK"
                        else "⚠️"
                        if result["status"] == "WARNING"
                        else "✗"
                    )
                    print(f"{status_symbol} {result['status']}")
                else:
                    print("? UNKNOWN")

            except Exception as e:
                print(f"✗ ERROR: {e}")
                self.add_check(check_name, "ERROR", f"Check failed: {e}")

    def print_summary(self):
        """Print health check summary."""
        print("\n" + "=" * 50)
        print("HEALTH CHECK SUMMARY")
        print("=" * 50)

        ok_count = len([c for c in self.checks if c["status"] == "OK"])
        warning_count = len(self.warnings)
        error_count = len(self.errors)

        print(f"Total Checks: {len(self.checks)}")
        print(f"✓ OK: {ok_count}")
        print(f"⚠️ Warnings: {warning_count}")
        print(f"✗ Errors: {error_count}")

        if self.warnings:
            print("\nWARNINGS:")
            for warning in self.warnings:
                print(f"  ⚠️ {warning['name']}: {warning['message']}")

        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  ✗ {error['name']}: {error['message']}")

        # Overall health status
        if error_count > 0:
            print(f"\n🔴 OVERALL STATUS: CRITICAL ({error_count} errors)")
            return False
        elif warning_count > 0:
            print(f"\n🟡 OVERALL STATUS: WARNING ({warning_count} warnings)")
            return True
        else:
            print(f"\n🟢 OVERALL STATUS: HEALTHY")
            return True

    async def cleanup(self):
        """Clean up resources."""
        try:
            await self.db_manager.close_all_connections()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Main health check function."""
    checker = HealthChecker()

    try:
        await checker.run_all_checks()
        healthy = checker.print_summary()

        # Exit with appropriate code
        return 0 if healthy else 1

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        print(f"\n✗ Health check failed: {e}")
        return 2

    finally:
        await checker.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
