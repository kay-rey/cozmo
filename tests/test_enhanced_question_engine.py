"""
Enhanced unit tests for the Question Engine.
Comprehensive tests for question selection, validation, formatting, and edge cases.
"""

import pytest
import asyncio
from datetime import date, datetime
from unittest.mock import patch, MagicMock
from utils.question_engine import QuestionEngine
from utils.models import Question


class TestEnhancedQuestionEngine:
    """Enhanced test cases for the QuestionEngine class."""

    @pytest.fixture
    def question_engine(self):
        """Create a QuestionEngine instance for testing."""
        return QuestionEngine()

    @pytest.fixture
    def mock_questions_data(self):
        """Mock questions data for testing."""
        return {
            "easy": [
                {
                    "id": 1,
                    "question": "What is 2 + 2?",
                    "question_type": "multiple_choice",
                    "difficulty": "easy",
                    "category": "math",
                    "correct_answer": "4",
                    "options": ["2", "3", "4", "5"],
                    "explanation": "Basic addition",
                    "point_value": 10,
                }
            ],
            "medium": [
                {
                    "id": 2,
                    "question": "What is the capital of France?",
                    "question_type": "fill_blank",
                    "difficulty": "medium",
                    "category": "geography",
                    "correct_answer": "Paris",
                    "answer_variations": ["paris", "PARIS"],
                    "explanation": "Paris is the capital of France",
                    "point_value": 20,
                }
            ],
            "hard": [
                {
                    "id": 3,
                    "question": "The Earth is flat.",
                    "question_type": "true_false",
                    "difficulty": "hard",
                    "category": "science",
                    "correct_answer": "false",
                    "explanation": "The Earth is spherical",
                    "point_value": 30,
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_question_loading_with_mock_data(self, mock_questions_data):
        """Test question loading with mocked data."""
        with patch("data.trivia_questions.QUESTIONS", mock_questions_data):
            engine = QuestionEngine()

            # Verify questions are loaded correctly
            assert len(engine._questions_cache["easy"]) == 1
            assert len(engine._questions_cache["medium"]) == 1
            assert len(engine._questions_cache["hard"]) == 1

            # Verify question objects are created correctly
            easy_question = engine._questions_cache["easy"][0]
            assert easy_question.question_text == "What is 2 + 2?"
            assert easy_question.difficulty == "easy"
            assert easy_question.point_value == 10

    @pytest.mark.asyncio
    async def test_get_question_with_all_filters(self, question_engine):
        """Test getting questions with all filter combinations."""
        # Test all difficulty levels
        for difficulty in ["easy", "medium", "hard"]:
            question = await question_engine.get_question(difficulty=difficulty)
            if question:  # Some difficulties might not have questions in test data
                assert question.difficulty == difficulty

        # Test all question types
        for q_type in ["multiple_choice", "true_false", "fill_blank"]:
            question = await question_engine.get_question(question_type=q_type)
            if question:
                assert question.question_type == q_type

    @pytest.mark.asyncio
    async def test_get_question_with_category_filter(self, mock_questions_data):
        """Test getting questions filtered by category."""
        with patch("data.trivia_questions.QUESTIONS", mock_questions_data):
            engine = QuestionEngine()

            # Test specific category
            question = await engine.get_question(category="math")
            if question:
                assert question.category == "math"

            # Test non-existent category
            question = await engine.get_question(category="nonexistent")
            assert question is None

    @pytest.mark.asyncio
    async def test_daily_challenge_consistency(self, question_engine):
        """Test that daily challenge returns consistent questions."""
        # Clear cache first
        question_engine.clear_daily_cache()

        # Get daily challenge multiple times
        question1 = await question_engine.get_daily_challenge_question()
        question2 = await question_engine.get_daily_challenge_question()
        question3 = await question_engine.get_daily_challenge_question()

        if question1:  # If we have questions available
            assert question1.id == question2.id == question3.id
            assert question1.difficulty == "hard"
            # Points should be doubled
            assert question1.point_value >= 60  # Hard questions are 30, doubled = 60

    @pytest.mark.asyncio
    async def test_weekly_challenge_consistency(self, question_engine):
        """Test that weekly challenge returns consistent question sets."""
        # Clear cache first
        question_engine.clear_weekly_cache()

        # Get weekly challenge multiple times
        questions1 = await question_engine.get_weekly_challenge_questions()
        questions2 = await question_engine.get_weekly_challenge_questions()

        if questions1:  # If we have questions available
            assert len(questions1) == len(questions2)
            for q1, q2 in zip(questions1, questions2):
                assert q1.id == q2.id
                # Points should be tripled
                assert q1.point_value >= 60  # Medium: 20*3=60, Hard: 30*3=90

    @pytest.mark.asyncio
    async def test_validate_answer_edge_cases(self, question_engine):
        """Test answer validation with edge cases."""
        # Test with None question
        result = await question_engine.validate_answer(None, "answer")
        assert result is False

        # Test with None answer
        question = Question(question_text="Test", correct_answer="test")
        result = await question_engine.validate_answer(question, None)
        assert result is False

        # Test with empty strings
        result = await question_engine.validate_answer(question, "")
        assert result is False

        # Test with whitespace-only answer
        result = await question_engine.validate_answer(question, "   ")
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_choice_validation_comprehensive(self, question_engine):
        """Test comprehensive multiple choice validation."""
        question = Question(
            question_text="Test question",
            question_type="multiple_choice",
            correct_answer="Option B",
            options=["Option A", "Option B", "Option C", "Option D"],
        )

        # Test correct answer by text (exact match)
        assert await question_engine.validate_answer(question, "Option B") is True

        # Test correct answer by text (case insensitive)
        assert await question_engine.validate_answer(question, "option b") is True

        # Test correct answer by index
        assert (
            await question_engine.validate_answer(question, "1") is True
        )  # Index 1 = "Option B"

        # Test incorrect answers
        assert await question_engine.validate_answer(question, "Option A") is False
        assert (
            await question_engine.validate_answer(question, "0") is False
        )  # Index 0 = "Option A"
        assert (
            await question_engine.validate_answer(question, "5") is False
        )  # Invalid index
        assert await question_engine.validate_answer(question, "Invalid") is False

    @pytest.mark.asyncio
    async def test_true_false_validation_comprehensive(self, question_engine):
        """Test comprehensive true/false validation."""
        true_question = Question(
            question_text="Test question",
            question_type="true_false",
            correct_answer="true",
        )

        false_question = Question(
            question_text="Test question",
            question_type="true_false",
            correct_answer="false",
        )

        # Test all true variations
        true_variations = ["true", "True", "TRUE", "t", "T", "yes", "y", "Y", "1", "✅"]
        for variation in true_variations:
            assert (
                await question_engine.validate_answer(true_question, variation) is True
            )
            assert (
                await question_engine.validate_answer(false_question, variation)
                is False
            )

        # Test all false variations
        false_variations = [
            "false",
            "False",
            "FALSE",
            "f",
            "F",
            "no",
            "n",
            "N",
            "0",
            "❌",
        ]
        for variation in false_variations:
            assert (
                await question_engine.validate_answer(true_question, variation) is False
            )
            assert (
                await question_engine.validate_answer(false_question, variation) is True
            )

    @pytest.mark.asyncio
    async def test_fill_blank_validation_comprehensive(self, question_engine):
        """Test comprehensive fill-in-the-blank validation."""
        question = Question(
            question_text="The capital of France is _____",
            question_type="fill_blank",
            correct_answer="Paris",
            answer_variations=["paris", "PARIS", "City of Light"],
        )

        # Test exact match
        assert await question_engine.validate_answer(question, "Paris") is True

        # Test case variations
        assert await question_engine.validate_answer(question, "paris") is True
        assert await question_engine.validate_answer(question, "PARIS") is True

        # Test answer variations
        assert await question_engine.validate_answer(question, "City of Light") is True

        # Test with extra whitespace and punctuation
        assert await question_engine.validate_answer(question, "  Paris  ") is True
        assert await question_engine.validate_answer(question, "Paris!") is True
        assert await question_engine.validate_answer(question, "Paris.") is True

        # Test incorrect answers
        assert await question_engine.validate_answer(question, "London") is False
        assert await question_engine.validate_answer(question, "Rome") is False

    def test_clean_answer_comprehensive(self, question_engine):
        """Test comprehensive answer cleaning functionality."""
        # Test case normalization
        assert question_engine._clean_answer("HELLO WORLD") == "hello world"

        # Test whitespace handling
        assert question_engine._clean_answer("  hello   world  ") == "hello world"
        assert question_engine._clean_answer("\thello\nworld\r") == "hello world"

        # Test punctuation removal
        assert question_engine._clean_answer("hello, world!") == "hello world"
        assert question_engine._clean_answer("hello; world?") == "hello world"
        assert question_engine._clean_answer("hello: world.") == "hello world"

        # Test empty and None inputs
        assert question_engine._clean_answer("") == ""
        assert question_engine._clean_answer(None) == ""

        # Test complex combinations
        assert question_engine._clean_answer("  HELLO,   WORLD!  ") == "hello world"

    def test_format_question_discord_comprehensive(self, question_engine):
        """Test comprehensive Discord formatting."""
        # Test multiple choice formatting
        mc_question = Question(
            question_text="What is 2 + 2?",
            question_type="multiple_choice",
            difficulty="medium",
            category="math",
            correct_answer="4",
            options=["2", "3", "4", "5"],
            point_value=20,
        )

        formatted = question_engine.format_question_for_discord(mc_question)

        assert "Medium Question (20 points)" in formatted["title"]
        assert formatted["description"] == "What is 2 + 2?"
        assert formatted["color"] == 0xFFFF00  # Yellow for medium
        assert any("🇦 2" in field["value"] for field in formatted.get("fields", []))
        assert "React with 🇦, 🇧, 🇨, or 🇩" in formatted["footer"]["text"]

        # Test true/false formatting
        tf_question = Question(
            question_text="The sky is blue",
            question_type="true_false",
            difficulty="easy",
            point_value=10,
        )

        formatted = question_engine.format_question_for_discord(tf_question)
        assert "Easy Question (10 points)" in formatted["title"]
        assert "✅ for True or ❌ for False" in formatted["footer"]["text"]

        # Test fill blank formatting
        fb_question = Question(
            question_text="The capital of France is _____",
            question_type="fill_blank",
            difficulty="hard",
            point_value=30,
        )

        formatted = question_engine.format_question_for_discord(fb_question)
        assert "Hard Question (30 points)" in formatted["title"]
        assert "Type your answer" in formatted["footer"]["text"]

    @pytest.mark.asyncio
    async def test_add_custom_question_validation(self, question_engine):
        """Test custom question addition with validation."""
        # Test valid question
        valid_question = {
            "question": "What is the meaning of life?",
            "question_type": "multiple_choice",
            "difficulty": "hard",
            "category": "philosophy",
            "correct_answer": "42",
            "options": ["41", "42", "43", "44"],
            "explanation": "From Hitchhiker's Guide",
            "point_value": 30,
        }

        result = await question_engine.add_custom_question(valid_question)
        assert result is True

        # Test missing required fields
        invalid_questions = [
            {"question": "Test"},  # Missing other required fields
            {"question_type": "multiple_choice"},  # Missing question text
            {"difficulty": "easy"},  # Missing question and type
            {
                "question": "Test",
                "question_type": "invalid_type",  # Invalid type
                "difficulty": "easy",
                "correct_answer": "test",
            },
            {
                "question": "Test",
                "question_type": "multiple_choice",
                "difficulty": "invalid_difficulty",  # Invalid difficulty
                "correct_answer": "test",
            },
        ]

        for invalid_question in invalid_questions:
            result = await question_engine.add_custom_question(invalid_question)
            assert result is False

    def test_question_statistics_comprehensive(self, question_engine):
        """Test comprehensive question statistics."""
        stats = question_engine.get_question_statistics()

        # Verify structure
        required_keys = ["total_questions", "by_difficulty", "by_type", "by_category"]
        for key in required_keys:
            assert key in stats

        # Verify data types
        assert isinstance(stats["total_questions"], int)
        assert isinstance(stats["by_difficulty"], dict)
        assert isinstance(stats["by_type"], dict)
        assert isinstance(stats["by_category"], dict)

        # Verify difficulty breakdown
        for difficulty in ["easy", "medium", "hard"]:
            assert difficulty in stats["by_difficulty"]
            assert isinstance(stats["by_difficulty"][difficulty], int)

        # Verify totals match
        total_by_difficulty = sum(stats["by_difficulty"].values())
        assert total_by_difficulty == stats["total_questions"]

    @pytest.mark.asyncio
    async def test_question_caching_behavior(self, question_engine):
        """Test question caching and cache management."""
        # Test daily cache
        question_engine.clear_daily_cache()
        assert len(question_engine._daily_challenge_cache) == 0

        # Get daily question to populate cache
        daily_q = await question_engine.get_daily_challenge_question()
        if daily_q:
            assert len(question_engine._daily_challenge_cache) == 1

        # Test weekly cache
        question_engine.clear_weekly_cache()
        assert len(question_engine._weekly_challenge_cache) == 0

        # Get weekly questions to populate cache
        weekly_qs = await question_engine.get_weekly_challenge_questions()
        if weekly_qs:
            assert len(question_engine._weekly_challenge_cache) == 1

    @pytest.mark.asyncio
    async def test_question_immutability(self, question_engine):
        """Test that returned questions don't affect cached versions."""
        original_question = await question_engine.get_question(difficulty="easy")
        if original_question:
            # Modify the returned question
            original_id = original_question.id
            original_question.point_value = 999
            original_question.question_text = "Modified"

            # Get the same question again
            new_question = await question_engine.get_question(difficulty="easy")
            if new_question and new_question.id == original_id:
                # Cached version should be unchanged
                assert new_question.point_value != 999
                assert new_question.question_text != "Modified"

    @pytest.mark.asyncio
    async def test_error_handling(self, question_engine):
        """Test error handling in various scenarios."""
        # Test with corrupted question data
        with patch.object(question_engine, "_questions_cache", {"easy": [None]}):
            question = await question_engine.get_question(difficulty="easy")
            # Should handle gracefully and return None or valid question

        # Test validation with malformed question
        malformed_question = Question()  # Empty question
        result = await question_engine.validate_answer(malformed_question, "test")
        assert result is False

    def test_difficulty_colors(self, question_engine):
        """Test difficulty color mapping."""
        assert question_engine._get_difficulty_color("easy") == 0x00FF00  # Green
        assert question_engine._get_difficulty_color("medium") == 0xFFFF00  # Yellow
        assert question_engine._get_difficulty_color("hard") == 0xFF0000  # Red
        assert (
            question_engine._get_difficulty_color("unknown") == 0x0099FF
        )  # Default blue


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
