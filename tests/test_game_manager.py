"""
Tests for the Game Manager system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from utils.game_manager import GameManager
from utils.question_engine import QuestionEngine
from utils.models import Question, GameSession
import discord


class TestGameManager:
    """Test cases for the GameManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.question_engine = Mock(spec=QuestionEngine)
        self.game_manager = GameManager(self.question_engine)

    @pytest.mark.asyncio
    async def test_start_game_success(self):
        """Test successfully starting a game."""
        # Mock question
        test_question = Question(
            id=1,
            question_text="Test question?",
            question_type="multiple_choice",
            difficulty="medium",
            options=["A", "B", "C", "D"],
            correct_answer="1",
            point_value=20,
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # Start game
        game_session = await self.game_manager.start_game(
            channel_id=12345, user_id=67890, difficulty="medium"
        )

        # Verify game was created
        assert game_session is not None
        assert game_session.channel_id == 12345
        assert game_session.user_id == 67890
        assert game_session.difficulty == "medium"
        assert game_session.question == test_question
        assert 67890 in game_session.participants

        # Verify game is tracked
        assert 12345 in self.game_manager.active_games
        assert await self.game_manager.get_active_games_count() == 1

    @pytest.mark.asyncio
    async def test_start_game_already_active(self):
        """Test starting a game when one is already active."""
        # Mock question
        test_question = Question(
            id=1,
            question_text="Test question?",
            question_type="multiple_choice",
            difficulty="medium",
            options=["A", "B", "C", "D"],
            correct_answer="1",
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # Start first game
        game1 = await self.game_manager.start_game(channel_id=12345, user_id=67890)
        assert game1 is not None

        # Try to start second game in same channel
        game2 = await self.game_manager.start_game(channel_id=12345, user_id=11111)
        assert game2 is None  # Should fail

        # Should still have only one game
        assert await self.game_manager.get_active_games_count() == 1

    @pytest.mark.asyncio
    async def test_start_game_no_question(self):
        """Test starting a game when no question is available."""
        self.question_engine.get_question = AsyncMock(return_value=None)

        # Try to start game
        game_session = await self.game_manager.start_game(
            channel_id=12345, user_id=67890
        )

        # Should fail
        assert game_session is None
        assert await self.game_manager.get_active_games_count() == 0

    @pytest.mark.asyncio
    async def test_get_active_game(self):
        """Test getting active game for a channel."""
        # Mock question
        test_question = Question(
            id=1,
            question_text="Test question?",
            question_type="multiple_choice",
            difficulty="medium",
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # No active game initially
        assert await self.game_manager.get_active_game(12345) is None

        # Start game
        await self.game_manager.start_game(channel_id=12345, user_id=67890)

        # Should now have active game
        active_game = await self.game_manager.get_active_game(12345)
        assert active_game is not None
        assert active_game.channel_id == 12345

    @pytest.mark.asyncio
    async def test_end_game(self):
        """Test ending a game."""
        # Mock question
        test_question = Question(
            id=1,
            question_text="Test question?",
            question_type="multiple_choice",
            difficulty="medium",
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # Start game
        await self.game_manager.start_game(channel_id=12345, user_id=67890)
        assert await self.game_manager.get_active_games_count() == 1

        # End game
        await self.game_manager.end_game(12345, reason="completed")

        # Should be no active games
        assert await self.game_manager.get_active_games_count() == 0
        assert await self.game_manager.get_active_game(12345) is None

    @pytest.mark.asyncio
    async def test_force_end_game(self):
        """Test force ending a game."""
        # Mock question
        test_question = Question(
            id=1,
            question_text="Test question?",
            question_type="multiple_choice",
            difficulty="medium",
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # Start game
        await self.game_manager.start_game(channel_id=12345, user_id=67890)

        # Force end game
        result = await self.game_manager.force_end_game(12345)
        assert result is True

        # Should be no active games
        assert await self.game_manager.get_active_games_count() == 0

        # Try to force end non-existent game
        result = await self.game_manager.force_end_game(99999)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_active_channels(self):
        """Test getting active channel IDs."""
        # Mock question
        test_question = Question(
            id=1,
            question_text="Test question?",
            question_type="multiple_choice",
            difficulty="medium",
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # No active games initially
        channels = await self.game_manager.get_active_channels()
        assert len(channels) == 0

        # Start games in different channels
        await self.game_manager.start_game(channel_id=12345, user_id=67890)
        await self.game_manager.start_game(channel_id=54321, user_id=11111)

        # Should have both channels
        channels = await self.game_manager.get_active_channels()
        assert len(channels) == 2
        assert 12345 in channels
        assert 54321 in channels

    def test_get_expected_answer_format(self):
        """Test getting expected answer format."""
        # No active game
        assert self.game_manager.get_expected_answer_format(12345) is None

        # Create mock game session
        test_question = Question(
            question_type="multiple_choice", options=["A", "B", "C", "D"]
        )

        game_session = GameSession(channel_id=12345, user_id=67890)
        game_session.question = test_question
        self.game_manager.active_games[12345] = game_session

        # Should get format
        format_str = self.game_manager.get_expected_answer_format(12345)
        assert format_str is not None
        assert "🇦, 🇧, 🇨, or 🇩" in format_str

    def test_get_correct_answer_display(self):
        """Test getting correct answer display."""
        # No active game
        assert self.game_manager.get_correct_answer_display(12345) is None

        # Create mock game session
        test_question = Question(
            question_type="multiple_choice",
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_answer="1",
        )

        game_session = GameSession(channel_id=12345, user_id=67890)
        game_session.question = test_question
        self.game_manager.active_games[12345] = game_session

        # Should get display
        display_str = self.game_manager.get_correct_answer_display(12345)
        assert display_str is not None
        assert "🇧" in display_str
        assert "Option B" in display_str

    def test_is_valid_reaction(self):
        """Test checking if reaction is valid."""
        # No active game
        assert self.game_manager.is_valid_reaction(12345, "🇦") is False

        # Create mock game session with multiple choice question
        test_question = Question(question_type="multiple_choice")
        game_session = GameSession(channel_id=12345, user_id=67890)
        game_session.question = test_question
        self.game_manager.active_games[12345] = game_session

        # Test valid and invalid reactions
        assert self.game_manager.is_valid_reaction(12345, "🇦") is True
        assert self.game_manager.is_valid_reaction(12345, "🇧") is True
        assert self.game_manager.is_valid_reaction(12345, "✅") is False
        assert self.game_manager.is_valid_reaction(12345, "🎉") is False

    def test_get_game_stats(self):
        """Test getting game statistics."""
        # No active games
        stats = self.game_manager.get_game_stats()
        assert stats["active_games"] == 0
        assert stats["active_timers"] == 0

        # Create mock game sessions
        game1 = GameSession(
            channel_id=12345, user_id=67890, difficulty="easy", is_challenge=False
        )
        game2 = GameSession(
            channel_id=54321, user_id=11111, difficulty="hard", is_challenge=True
        )

        self.game_manager.active_games[12345] = game1
        self.game_manager.active_games[54321] = game2

        # Check stats
        stats = self.game_manager.get_game_stats()
        assert stats["active_games"] == 2
        assert stats["games_by_difficulty"]["easy"] == 1
        assert stats["games_by_difficulty"]["hard"] == 1
        assert stats["games_by_type"]["regular"] == 1
        assert stats["games_by_type"]["challenge"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_expired_games(self):
        """Test cleaning up expired games."""
        # This test would require mocking datetime to simulate expired games
        # For now, just test that the method runs without error
        cleaned = await self.game_manager.cleanup_expired_games()
        assert isinstance(cleaned, int)
        assert cleaned >= 0

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test shutting down the game manager."""
        # Mock question
        test_question = Question(
            id=1,
            question_text="Test question?",
            question_type="multiple_choice",
            difficulty="medium",
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # Start some games
        await self.game_manager.start_game(channel_id=12345, user_id=67890)
        await self.game_manager.start_game(channel_id=54321, user_id=11111)

        assert await self.game_manager.get_active_games_count() == 2

        # Shutdown
        await self.game_manager.shutdown()

        # Should have no active games
        assert await self.game_manager.get_active_games_count() == 0


if __name__ == "__main__":
    pytest.main([__file__])
