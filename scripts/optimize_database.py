#!/usr/bin/env python3
"""
Database optimization script for Enhanced Trivia System.
Handles performance optimization, indexing, and maintenance.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Handles database performance optimization."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def analyze_performance(self):
        """Analyze database performance and suggest optimizations."""
        print("Analyzing database performance...")

        async with self.db_manager.get_connection() as conn:
            # Get table statistics
            stats = {}

            tables = [
                "users",
                "questions",
                "user_achievements",
                "weekly_rankings",
                "game_sessions",
            ]

            for table in tables:
                cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = (await cursor.fetchone())[0]
                stats[table] = count

            # Check index usage
            cursor = await conn.execute("PRAGMA index_list('users')")
            user_indexes = await cursor.fetchall()

            cursor = await conn.execute("PRAGMA index_list('questions')")
            question_indexes = await cursor.fetchall()

            print("\nDatabase Statistics:")
            print("-" * 40)
            for table, count in stats.items():
                print(f"{table:<20}: {count:>10,} rows")

            print(f"\nIndexes on users table: {len(user_indexes)}")
            print(f"Indexes on questions table: {len(question_indexes)}")

            return stats

    async def optimize_indexes(self):
        """Create or update database indexes for better performance."""
        print("Optimizing database indexes...")

        async with self.db_manager.get_connection() as conn:
            # Additional performance indexes
            optimization_indexes = [
                # Composite indexes for common query patterns
                "CREATE INDEX IF NOT EXISTS idx_users_points_streak ON users (total_points DESC, current_streak DESC)",
                "CREATE INDEX IF NOT EXISTS idx_questions_difficulty_category ON questions (difficulty, category)",
                "CREATE INDEX IF NOT EXISTS idx_questions_performance ON questions (times_asked, times_correct)",
                "CREATE INDEX IF NOT EXISTS idx_game_sessions_user_time ON game_sessions (user_id, start_time DESC)",
                "CREATE INDEX IF NOT EXISTS idx_weekly_rankings_week_rank ON weekly_rankings (week_start, rank)",
                # Indexes for challenge queries
                "CREATE INDEX IF NOT EXISTS idx_users_daily_challenge ON users (daily_challenge_completed)",
                "CREATE INDEX IF NOT EXISTS idx_users_weekly_challenge ON users (weekly_challenge_completed)",
                # Performance tracking indexes
                "CREATE INDEX IF NOT EXISTS idx_questions_success_rate ON questions (CAST(times_correct AS FLOAT) / NULLIF(times_asked, 0))",
            ]

            created_count = 0
            for index_sql in optimization_indexes:
                try:
                    await conn.execute(index_sql)
                    created_count += 1
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")

            await conn.commit()
            print(f"✓ Created/verified {created_count} optimization indexes")

    async def vacuum_database(self):
        """Vacuum the database to reclaim space and optimize storage."""
        print("Vacuuming database...")

        async with self.db_manager.get_connection() as conn:
            # Get database size before vacuum
            cursor = await conn.execute("PRAGMA page_count")
            page_count_before = (await cursor.fetchone())[0]

            cursor = await conn.execute("PRAGMA page_size")
            page_size = (await cursor.fetchone())[0]

            size_before = page_count_before * page_size

            # Perform vacuum
            await conn.execute("VACUUM")

            # Get size after vacuum
            cursor = await conn.execute("PRAGMA page_count")
            page_count_after = (await cursor.fetchone())[0]

            size_after = page_count_after * page_size

            space_saved = size_before - size_after

            print(f"✓ Database vacuumed")
            print(f"  Size before: {size_before / 1024 / 1024:.2f} MB")
            print(f"  Size after:  {size_after / 1024 / 1024:.2f} MB")
            print(f"  Space saved: {space_saved / 1024 / 1024:.2f} MB")

    async def analyze_queries(self):
        """Analyze common query patterns and performance."""
        print("Analyzing query patterns...")

        async with self.db_manager.get_connection() as conn:
            # Enable query plan analysis
            await conn.execute("PRAGMA query_only = ON")

            # Test common queries and their execution plans
            test_queries = [
                (
                    "User leaderboard",
                    "SELECT user_id, total_points FROM users ORDER BY total_points DESC LIMIT 10",
                ),
                (
                    "Random question",
                    "SELECT * FROM questions WHERE difficulty = 'medium' ORDER BY RANDOM() LIMIT 1",
                ),
                ("User stats", "SELECT * FROM users WHERE user_id = 1"),
                (
                    "Weekly rankings",
                    "SELECT * FROM weekly_rankings WHERE week_start = date('now', 'weekday 1', '-7 days') ORDER BY points DESC",
                ),
                (
                    "Active sessions",
                    "SELECT * FROM game_sessions WHERE is_completed = FALSE",
                ),
            ]

            print("\nQuery Performance Analysis:")
            print("-" * 60)

            for query_name, query in test_queries:
                try:
                    cursor = await conn.execute(f"EXPLAIN QUERY PLAN {query}")
                    plan = await cursor.fetchall()

                    print(f"\n{query_name}:")
                    for step in plan:
                        print(f"  {step[3]}")

                except Exception as e:
                    print(f"  Error analyzing {query_name}: {e}")

            await conn.execute("PRAGMA query_only = OFF")

    async def update_statistics(self):
        """Update database statistics for query optimization."""
        print("Updating database statistics...")

        async with self.db_manager.get_connection() as conn:
            await conn.execute("ANALYZE")
            await conn.commit()

            print("✓ Database statistics updated")

    async def check_fragmentation(self):
        """Check database fragmentation and suggest maintenance."""
        print("Checking database fragmentation...")

        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute("PRAGMA freelist_count")
            freelist_count = (await cursor.fetchone())[0]

            cursor = await conn.execute("PRAGMA page_count")
            page_count = (await cursor.fetchone())[0]

            if page_count > 0:
                fragmentation_ratio = freelist_count / page_count

                print(f"Free pages: {freelist_count}")
                print(f"Total pages: {page_count}")
                print(f"Fragmentation ratio: {fragmentation_ratio:.2%}")

                if fragmentation_ratio > 0.1:  # More than 10% fragmentation
                    print("⚠️  High fragmentation detected - consider running VACUUM")
                else:
                    print("✓ Fragmentation is within acceptable limits")
            else:
                print("✓ No fragmentation detected")


async def main():
    """Main optimization function."""
    print("Enhanced Trivia System - Database Optimization Tool")
    print("=" * 55)

    db_manager = DatabaseManager()
    optimizer = DatabaseOptimizer(db_manager)

    try:
        # Step 1: Analyze current performance
        await optimizer.analyze_performance()

        # Step 2: Check fragmentation
        await optimizer.check_fragmentation()

        # Step 3: Optimize indexes
        await optimizer.optimize_indexes()

        # Step 4: Update statistics
        await optimizer.update_statistics()

        # Step 5: Analyze query patterns
        await optimizer.analyze_queries()

        # Step 6: Vacuum if needed (optional - can be resource intensive)
        print("\nOptional: Run VACUUM to defragment database? (y/N): ", end="")
        response = input().strip().lower()
        if response == "y":
            await optimizer.vacuum_database()

        print("\n✓ Database optimization completed!")

    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        print(f"\n✗ Optimization failed: {e}")
        return False

    finally:
        await db_manager.close_all_connections()

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
