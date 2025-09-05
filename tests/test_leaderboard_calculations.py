"""
Comprehensive tests for leaderboard calculations and ranking logic.
Tests ranking algorithms, tie-breaking, and performance metrics.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta

# Add the parent directory to the path so we can import our modules
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.models import LeaderboardEntry, UserProfile


class TestLeaderboardCalculations:
    """Comprehensive tests for leaderboard calculations."""

    @pytest.fixture
    def sample_users_data(self):
        """Sample user data for leaderboard testing."""
        return [
            {
                "user_id": 1001,
                "username": "User1001",
                "total_points": 1000,
                "questions_answered": 50,
                "questions_correct": 45,
                "current_streak": 5,
                "best_streak": 10,
                "accuracy": 90.0,
            },
            {
                "user_id": 1002,
                "username": "User1002",
                "total_points": 1200,
                "questions_answered": 60,
                "questions_correct": 48,
                "current_streak": 8,
                "best_streak": 12,
                "accuracy": 80.0,
            },
            {
                "user_id": 1003,
                "username": "User1003",
                "total_points": 800,
                "questions_answered": 40,
                "questions_correct": 36,
                "current_streak": 3,
                "best_streak": 8,
                "accuracy": 90.0,
            },
            {
                "user_id": 1004,
                "username": "User1004",
                "total_points": 1200,  # Same as 1002 for tie-breaking test
                "questions_answered": 55,
                "questions_correct": 50,
                "current_streak": 10,
                "best_streak": 15,
                "accuracy": 90.9,
            },
            {
                "user_id": 1005,
                "username": "User1005",
                "total_points": 0,  # New user
                "questions_answered": 0,
                "questions_correct": 0,
                "current_streak": 0,
                "best_streak": 0,
                "accuracy": 0.0,
            },
        ]

    def create_leaderboard_entries(self, users_data):
        """Create LeaderboardEntry objects from user data."""
        entries = []
        for i, user in enumerate(users_data):
            entry = LeaderboardEntry(
                rank=i + 1,  # Will be recalculated
                user_id=user["user_id"],
                username=user["username"],
                total_points=user["total_points"],
                accuracy_percentage=user["accuracy"],
                questions_answered=user["questions_answered"],
                current_streak=user["current_streak"],
            )
            entries.append(entry)
        return entries

    def test_basic_ranking_by_points(self, sample_users_data):
        """Test basic ranking by total points."""
        entries = self.create_leaderboard_entries(sample_users_data)

        # Sort by points (descending)
        sorted_entries = sorted(entries, key=lambda x: x.total_points, reverse=True)

        # Assign ranks
        for i, entry in enumerate(sorted_entries):
            entry.rank = i + 1

        # Verify ranking order
        assert sorted_entries[0].user_id in [1002, 1004]  # Tied at 1200 points
        assert sorted_entries[1].user_id in [1002, 1004]  # Tied at 1200 points
        assert sorted_entries[2].user_id == 1001  # 1000 points
        assert sorted_entries[3].user_id == 1003  # 800 points
        assert sorted_entries[4].user_id == 1005  # 0 points

    def test_tie_breaking_by_accuracy(self, sample_users_data):
        """Test tie-breaking by accuracy when points are equal."""
        entries = self.create_leaderboard_entries(sample_users_data)

        # Sort by points first, then by accuracy
        sorted_entries = sorted(
            entries, key=lambda x: (x.total_points, x.accuracy_percentage), reverse=True
        )

        # Assign ranks
        for i, entry in enumerate(sorted_entries):
            entry.rank = i + 1

        # Users 1002 and 1004 both have 1200 points
        # User 1004 has 90.9% accuracy, User 1002 has 80.0% accuracy
        # So User 1004 should rank higher
        top_two = sorted_entries[:2]
        assert top_two[0].user_id == 1004  # Higher accuracy
        assert top_two[1].user_id == 1002  # Lower accuracy

    def test_tie_breaking_multiple_criteria(self, sample_users_data):
        """Test tie-breaking with multiple criteria."""
        # Modify data to create more complex ties
        sample_users_data[1]["accuracy"] = 90.9  # Same as user 1004
        sample_users_data[3]["accuracy"] = 90.9  # Same as user 1004

        entries = self.create_leaderboard_entries(sample_users_data)

        # Sort by points, accuracy, then current streak
        sorted_entries = sorted(
            entries,
            key=lambda x: (x.total_points, x.accuracy_percentage, x.current_streak),
            reverse=True,
        )

        # Users 1002 and 1004 now have same points and accuracy
        # User 1004 has streak 10, User 1002 has streak 8
        # So User 1004 should still rank higher
        top_two = sorted_entries[:2]
        assert top_two[0].user_id == 1004  # Higher streak
        assert top_two[1].user_id == 1002  # Lower streak

    def test_ranking_with_zero_points_users(self, sample_users_data):
        """Test ranking behavior with users who have zero points."""
        entries = self.create_leaderboard_entries(sample_users_data)

        # Filter out zero-point users (common leaderboard behavior)
        active_entries = [e for e in entries if e.total_points > 0]

        # Sort remaining users
        sorted_entries = sorted(
            active_entries, key=lambda x: x.total_points, reverse=True
        )

        # Verify zero-point user is excluded
        user_ids = [e.user_id for e in sorted_entries]
        assert 1005 not in user_ids  # Zero-point user excluded
        assert len(sorted_entries) == 4  # Only active users

    def test_percentile_calculation(self, sample_users_data):
        """Test percentile calculation for user rankings."""
        entries = self.create_leaderboard_entries(sample_users_data)
        active_entries = [e for e in entries if e.total_points > 0]
        total_users = len(active_entries)

        # Sort by points
        sorted_entries = sorted(
            active_entries, key=lambda x: x.total_points, reverse=True
        )

        # Calculate percentiles
        for i, entry in enumerate(sorted_entries):
            entry.rank = i + 1
            percentile = ((total_users - entry.rank) / total_users) * 100

            # Verify percentile calculations
            if entry.rank == 1:
                assert percentile >= 75  # Top user should be in top 25%
            elif entry.rank == total_users:
                assert percentile == 0  # Last user is 0th percentile

    def test_weekly_ranking_calculation(self, sample_users_data):
        """Test weekly ranking calculations."""
        # Simulate weekly points (subset of total points)
        weekly_data = []
        for user in sample_users_data:
            weekly_points = user["total_points"] // 3  # Simulate weekly activity
            weekly_data.append(
                {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "weekly_points": weekly_points,
                    "weekly_questions": user["questions_answered"] // 3,
                }
            )

        # Create weekly leaderboard entries
        weekly_entries = []
        for data in weekly_data:
            if data["weekly_points"] > 0:  # Only include active users
                entry = LeaderboardEntry(
                    rank=0,
                    user_id=data["user_id"],
                    username=data["username"],
                    total_points=data["weekly_points"],
                    accuracy_percentage=0,  # Would be calculated separately
                    questions_answered=data["weekly_questions"],
                    current_streak=0,
                )
                weekly_entries.append(entry)

        # Sort and rank
        sorted_entries = sorted(
            weekly_entries, key=lambda x: x.total_points, reverse=True
        )
        for i, entry in enumerate(sorted_entries):
            entry.rank = i + 1

        # Verify weekly rankings
        assert len(sorted_entries) <= len(sample_users_data)
        if sorted_entries:
            assert sorted_entries[0].total_points >= sorted_entries[-1].total_points

    def test_rank_change_calculation(self, sample_users_data):
        """Test rank change calculation between periods."""
        # Create current rankings
        current_entries = self.create_leaderboard_entries(sample_users_data)
        current_sorted = sorted(
            current_entries, key=lambda x: x.total_points, reverse=True
        )

        for i, entry in enumerate(current_sorted):
            entry.rank = i + 1

        # Simulate previous rankings (different order)
        previous_ranks = {
            1001: 1,  # Was rank 1, now rank 3 (down 2)
            1002: 3,  # Was rank 3, now rank 1 or 2 (up 1-2)
            1003: 2,  # Was rank 2, now rank 4 (down 2)
            1004: 4,  # Was rank 4, now rank 1 or 2 (up 2-3)
            1005: 5,  # Was rank 5, still rank 5 (no change)
        }

        # Calculate rank changes
        for entry in current_sorted:
            previous_rank = previous_ranks.get(entry.user_id)
            if previous_rank:
                rank_change = previous_rank - entry.rank  # Positive = moved up
                entry.rank_change = rank_change

        # Verify rank changes make sense
        for entry in current_sorted:
            if entry.user_id == 1001:
                assert entry.rank_change < 0  # Moved down
            elif entry.user_id in [1002, 1004]:
                assert entry.rank_change > 0  # Moved up

    def test_leaderboard_pagination(self, sample_users_data):
        """Test leaderboard pagination logic."""
        entries = self.create_leaderboard_entries(sample_users_data)
        sorted_entries = sorted(entries, key=lambda x: x.total_points, reverse=True)

        # Assign ranks
        for i, entry in enumerate(sorted_entries):
            entry.rank = i + 1

        # Test pagination
        page_size = 2
        page_1 = sorted_entries[0:page_size]  # Ranks 1-2
        page_2 = sorted_entries[page_size : page_size * 2]  # Ranks 3-4
        page_3 = sorted_entries[page_size * 2 : page_size * 3]  # Rank 5

        # Verify pagination
        assert len(page_1) == 2
        assert len(page_2) == 2
        assert len(page_3) == 1

        # Verify rank continuity
        assert page_1[0].rank == 1
        assert page_1[1].rank == 2
        assert page_2[0].rank == 3
        assert page_2[1].rank == 4
        assert page_3[0].rank == 5

    def test_nearby_ranks_calculation(self, sample_users_data):
        """Test calculation of nearby ranks around a user."""
        entries = self.create_leaderboard_entries(sample_users_data)
        sorted_entries = sorted(entries, key=lambda x: x.total_points, reverse=True)

        # Assign ranks
        for i, entry in enumerate(sorted_entries):
            entry.rank = i + 1

        # Find user 1001 (should be rank 3)
        target_user_rank = None
        for entry in sorted_entries:
            if entry.user_id == 1001:
                target_user_rank = entry.rank
                break

        # Get nearby ranks (context_size = 1)
        context_size = 1
        start_rank = max(1, target_user_rank - context_size)
        end_rank = min(len(sorted_entries), target_user_rank + context_size)

        nearby_entries = [e for e in sorted_entries if start_rank <= e.rank <= end_rank]

        # Should include user and neighbors
        assert len(nearby_entries) >= 1  # At least the user
        assert any(e.user_id == 1001 for e in nearby_entries)  # Includes target user

    def test_leaderboard_with_identical_stats(self):
        """Test leaderboard behavior with users having identical stats."""
        identical_users = [
            {
                "user_id": 2001,
                "username": "User2001",
                "total_points": 500,
                "questions_answered": 25,
                "questions_correct": 20,
                "current_streak": 3,
                "accuracy": 80.0,
            },
            {
                "user_id": 2002,
                "username": "User2002",
                "total_points": 500,
                "questions_answered": 25,
                "questions_correct": 20,
                "current_streak": 3,
                "accuracy": 80.0,
            },
            {
                "user_id": 2003,
                "username": "User2003",
                "total_points": 500,
                "questions_answered": 25,
                "questions_correct": 20,
                "current_streak": 3,
                "accuracy": 80.0,
            },
        ]

        entries = self.create_leaderboard_entries(identical_users)

        # Sort by points, accuracy, streak, then user_id for consistency
        sorted_entries = sorted(
            entries,
            key=lambda x: (
                x.total_points,
                x.accuracy_percentage,
                x.current_streak,
                x.user_id,
            ),
            reverse=True,
        )

        # All should have same stats but different ranks
        assert all(e.total_points == 500 for e in sorted_entries)
        assert (
            sorted_entries[0].user_id
            < sorted_entries[1].user_id
            < sorted_entries[2].user_id
        )

    def test_leaderboard_performance_metrics(self, sample_users_data):
        """Test calculation of performance metrics for leaderboard."""
        entries = self.create_leaderboard_entries(sample_users_data)

        # Calculate additional metrics
        for entry in entries:
            if entry.questions_answered > 0:
                # Points per question
                entry.efficiency = entry.total_points / entry.questions_answered

                # Streak ratio (current/best)
                if hasattr(entry, "best_streak") and entry.current_streak > 0:
                    # We'd need to add best_streak to LeaderboardEntry for this
                    pass

        # Sort by efficiency
        efficiency_sorted = sorted(
            [e for e in entries if e.questions_answered > 0],
            key=lambda x: x.efficiency,
            reverse=True,
        )

        # Verify efficiency calculations
        for entry in efficiency_sorted:
            assert entry.efficiency > 0
            assert entry.efficiency == entry.total_points / entry.questions_answered

    def test_leaderboard_edge_cases(self):
        """Test leaderboard edge cases."""
        # Empty leaderboard
        empty_entries = []
        sorted_empty = sorted(empty_entries, key=lambda x: x.total_points, reverse=True)
        assert len(sorted_empty) == 0

        # Single user leaderboard
        single_user = [
            LeaderboardEntry(
                rank=1,
                user_id=3001,
                username="OnlyUser",
                total_points=100,
                accuracy_percentage=75.0,
                questions_answered=10,
                current_streak=2,
            )
        ]

        sorted_single = sorted(single_user, key=lambda x: x.total_points, reverse=True)
        assert len(sorted_single) == 1
        assert sorted_single[0].rank == 1

    def test_leaderboard_data_validation(self, sample_users_data):
        """Test validation of leaderboard data."""
        entries = self.create_leaderboard_entries(sample_users_data)

        for entry in entries:
            # Validate data types
            assert isinstance(entry.rank, int)
            assert isinstance(entry.user_id, int)
            assert isinstance(entry.username, str)
            assert isinstance(entry.total_points, int)
            assert isinstance(entry.accuracy_percentage, float)
            assert isinstance(entry.questions_answered, int)
            assert isinstance(entry.current_streak, int)

            # Validate data ranges
            assert entry.rank > 0
            assert entry.user_id > 0
            assert entry.total_points >= 0
            assert 0.0 <= entry.accuracy_percentage <= 100.0
            assert entry.questions_answered >= 0
            assert entry.current_streak >= 0

            # Validate logical consistency
            if entry.questions_answered == 0:
                assert entry.total_points == 0
                assert entry.accuracy_percentage == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
