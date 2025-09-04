"""
Question Engine for the Enhanced Trivia System.
Handles question selection, validation, and formatting for different question types.
"""

import random
import re
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from utils.models import Question, QUESTION_TYPES, DIFFICULTY_LEVELS, POINT_VALUES
from data.trivia_questions import QUESTIONS


class QuestionEngine:
    """
    Manages question selection, validation, and formatting for the trivia system.
    Supports multiple choice, true/false, and fill-in-the-blank questions.
    """

    def __init__(self):
        """Initialize the Question Engine."""
        self._questions_cache = {}
        self._daily_challenge_cache = {}
        self._weekly_challenge_cache = {}
        self._load_questions()

    def _load_questions(self) -> None:
        """Load questions from the questions data file into Question objects."""
        self._questions_cache = {"easy": [], "medium": [], "hard": []}

        for difficulty, questions_list in QUESTIONS.items():
            for question_data in questions_list:
                question = self._convert_to_question_object(question_data)
                self._questions_cache[difficulty].append(question)

    def _convert_to_question_object(self, question_data: Dict[str, Any]) -> Question:
        """Convert question data dictionary to Question object."""
        # Handle different answer formats from the data
        correct_answer = question_data.get("correct_answer")

        # For multiple choice questions, convert index to actual answer
        if question_data.get("question_type") == "multiple_choice" and isinstance(
            correct_answer, int
        ):
            options = question_data.get("options", [])
            if 0 <= correct_answer < len(options):
                correct_answer = options[correct_answer]

        # For true/false questions, ensure boolean is converted to string
        elif question_data.get("question_type") == "true_false":
            correct_answer = str(correct_answer).lower()

        return Question(
            id=question_data.get("id"),
            question_text=question_data.get("question", ""),
            question_type=question_data.get("question_type", "multiple_choice"),
            difficulty=question_data.get("difficulty", "medium"),
            category=question_data.get("category", "general"),
            correct_answer=str(correct_answer),
            options=question_data.get("options"),
            answer_variations=question_data.get("answer_variations", []),
            explanation=question_data.get("explanation"),
            point_value=question_data.get(
                "point_value",
                POINT_VALUES.get(question_data.get("difficulty", "medium"), 20),
            ),
            times_asked=question_data.get("times_asked", 0),
            times_correct=question_data.get("times_correct", 0),
        )

    async def get_question(
        self,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Optional[Question]:
        """
        Get a random question based on specified criteria.

        Args:
            difficulty: Question difficulty ("easy", "medium", "hard"). If None, random difficulty.
            question_type: Question type ("multiple_choice", "true_false", "fill_blank"). If None, any type.
            category: Question category. If None, any category.

        Returns:
            Question object or None if no matching questions found.
        """
        # If no difficulty specified, choose randomly
        if difficulty is None:
            difficulty = random.choice(DIFFICULTY_LEVELS)

        # Validate difficulty
        if difficulty not in DIFFICULTY_LEVELS:
            difficulty = "medium"

        # Get questions for the specified difficulty
        available_questions = self._questions_cache.get(difficulty, [])

        # Filter by question type if specified
        if question_type and question_type in QUESTION_TYPES:
            available_questions = [
                q for q in available_questions if q.question_type == question_type
            ]

        # Filter by category if specified
        if category:
            available_questions = [
                q for q in available_questions if q.category == category
            ]

        # Return random question from filtered list
        if available_questions:
            question = random.choice(available_questions)
            # Create a copy to avoid modifying the cached version
            return Question(
                id=question.id,
                question_text=question.question_text,
                question_type=question.question_type,
                difficulty=question.difficulty,
                category=question.category,
                correct_answer=question.correct_answer,
                options=question.options.copy() if question.options else None,
                answer_variations=question.answer_variations.copy()
                if question.answer_variations
                else None,
                explanation=question.explanation,
                point_value=question.point_value,
                times_asked=question.times_asked,
                times_correct=question.times_correct,
            )

        return None

    async def get_daily_challenge_question(self) -> Optional[Question]:
        """
        Get the daily challenge question.
        Returns the same question for the entire day.

        Returns:
            Question object for daily challenge or None if not available.
        """
        today = date.today().isoformat()

        # Check if we already have today's question cached
        if today in self._daily_challenge_cache:
            return self._daily_challenge_cache[today]

        # Select a hard question for daily challenge
        question = await self.get_question(difficulty="hard")
        if question:
            # Double the points for daily challenge
            question.point_value *= 2
            self._daily_challenge_cache[today] = question

        return question

    async def get_weekly_challenge_questions(self) -> List[Question]:
        """
        Get 5 questions for the weekly challenge.
        Returns the same set of questions for the entire week.

        Returns:
            List of 5 Question objects for weekly challenge.
        """
        # Get the start of the current week (Monday)
        today = date.today()
        days_since_monday = today.weekday()
        week_start = today.replace(day=today.day - days_since_monday).isoformat()

        # Check if we already have this week's questions cached
        if week_start in self._weekly_challenge_cache:
            return self._weekly_challenge_cache[week_start]

        # Select 5 questions: 2 medium, 3 hard
        questions = []

        # Get 2 medium questions
        for _ in range(2):
            question = await self.get_question(difficulty="medium")
            if question:
                question.point_value *= 3  # Triple points for weekly challenge
                questions.append(question)

        # Get 3 hard questions
        for _ in range(3):
            question = await self.get_question(difficulty="hard")
            if question:
                question.point_value *= 3  # Triple points for weekly challenge
                questions.append(question)

        # Cache the questions for the week
        if questions:
            self._weekly_challenge_cache[week_start] = questions

        return questions

    async def validate_answer(self, question: Question, user_answer: Any) -> bool:
        """
        Validate a user's answer against the correct answer.

        Args:
            question: The Question object being answered.
            user_answer: The user's answer (can be string, int, bool, etc.).

        Returns:
            True if the answer is correct, False otherwise.
        """
        if not question or user_answer is None:
            return False

        # Convert user answer to string for comparison
        user_answer_str = str(user_answer).strip()

        if question.question_type == "multiple_choice":
            return self._validate_multiple_choice(question, user_answer_str)
        elif question.question_type == "true_false":
            return self._validate_true_false(question, user_answer_str)
        elif question.question_type == "fill_blank":
            return self._validate_fill_blank(question, user_answer_str)

        return False

    def _validate_multiple_choice(self, question: Question, user_answer: str) -> bool:
        """Validate multiple choice answer."""
        if not question.options:
            return False

        user_answer_lower = user_answer.lower().strip()
        correct_answer_lower = question.correct_answer.lower().strip()

        # Check if user_answer is an index (0-3)
        try:
            answer_index = int(user_answer)
            if 0 <= answer_index < len(question.options):
                return (
                    question.options[answer_index].lower().strip()
                    == correct_answer_lower
                )
        except ValueError:
            pass

        # Check if user answer matches the correct answer directly
        if user_answer_lower == correct_answer_lower:
            return True

        # Check if user answer matches any option and that option is correct
        for option in question.options:
            if option.lower().strip() == user_answer_lower:
                return option.lower().strip() == correct_answer_lower

        return False

    def _validate_true_false(self, question: Question, user_answer: str) -> bool:
        """Validate true/false answer."""
        user_answer_lower = user_answer.lower()
        correct_answer_lower = question.correct_answer.lower()

        # Handle various true/false representations
        true_values = ["true", "t", "yes", "y", "1", "✅"]
        false_values = ["false", "f", "no", "n", "0", "❌"]

        user_is_true = user_answer_lower in true_values
        user_is_false = user_answer_lower in false_values

        correct_is_true = correct_answer_lower in ["true", "t", "yes", "y", "1"]

        if user_is_true:
            return correct_is_true
        elif user_is_false:
            return not correct_is_true

        return False

    def _validate_fill_blank(self, question: Question, user_answer: str) -> bool:
        """Validate fill-in-the-blank answer."""
        user_answer_clean = self._clean_answer(user_answer)

        # Check against the main correct answer
        if self._clean_answer(question.correct_answer) == user_answer_clean:
            return True

        # Check against answer variations if available
        if question.answer_variations:
            for variation in question.answer_variations:
                if self._clean_answer(variation) == user_answer_clean:
                    return True

        return False

    def _clean_answer(self, answer: str) -> str:
        """Clean answer text for comparison (case-insensitive, remove extra spaces/punctuation)."""
        if not answer:
            return ""

        # Convert to lowercase and remove extra whitespace
        cleaned = answer.lower().strip()

        # Remove common punctuation that shouldn't affect correctness
        cleaned = re.sub(r"[.,!?;:]", "", cleaned)

        # Replace multiple spaces with single space
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned

    def format_question_for_discord(self, question: Question) -> Dict[str, Any]:
        """
        Format a question for Discord display.

        Args:
            question: The Question object to format.

        Returns:
            Dictionary containing formatted question data for Discord embed.
        """
        if not question:
            return {}

        # Base embed data
        embed_data = {
            "title": f"🎯 {question.difficulty.title()} Question ({question.point_value} points)",
            "description": question.question_text,
            "color": self._get_difficulty_color(question.difficulty),
            "fields": [
                {
                    "name": "Category",
                    "value": question.category.title(),
                    "inline": True,
                },
                {
                    "name": "Type",
                    "value": question.question_type.replace("_", " ").title(),
                    "inline": True,
                },
            ],
        }

        # Add type-specific formatting
        if question.question_type == "multiple_choice":
            embed_data.update(self._format_multiple_choice(question))
        elif question.question_type == "true_false":
            embed_data.update(self._format_true_false(question))
        elif question.question_type == "fill_blank":
            embed_data.update(self._format_fill_blank(question))

        return embed_data

    def _format_multiple_choice(self, question: Question) -> Dict[str, Any]:
        """Format multiple choice question."""
        if not question.options:
            return {}

        options_text = ""
        emojis = ["🇦", "🇧", "🇨", "🇩"]

        for i, option in enumerate(question.options):
            if i < len(emojis):
                options_text += f"{emojis[i]} {option}\n"

        return {
            "fields": [{"name": "Options", "value": options_text, "inline": False}],
            "footer": {"text": "React with 🇦, 🇧, 🇨, or 🇩 to answer!"},
        }

    def _format_true_false(self, question: Question) -> Dict[str, Any]:
        """Format true/false question."""
        return {"footer": {"text": "React with ✅ for True or ❌ for False!"}}

    def _format_fill_blank(self, question: Question) -> Dict[str, Any]:
        """Format fill-in-the-blank question."""
        return {"footer": {"text": "Type your answer in the chat!"}}

    def _get_difficulty_color(self, difficulty: str) -> int:
        """Get color code for difficulty level."""
        colors = {
            "easy": 0x00FF00,  # Green
            "medium": 0xFFFF00,  # Yellow
            "hard": 0xFF0000,  # Red
        }
        return colors.get(difficulty, 0x0099FF)  # Default blue

    async def add_custom_question(self, question_data: Dict[str, Any]) -> bool:
        """
        Add a custom question to the question pool.

        Args:
            question_data: Dictionary containing question information.

        Returns:
            True if question was added successfully, False otherwise.
        """
        try:
            # Validate required fields
            required_fields = [
                "question",
                "question_type",
                "difficulty",
                "correct_answer",
            ]
            for field in required_fields:
                if field not in question_data:
                    return False

            # Validate question type and difficulty
            if question_data["question_type"] not in QUESTION_TYPES:
                return False
            if question_data["difficulty"] not in DIFFICULTY_LEVELS:
                return False

            # Create Question object
            question = self._convert_to_question_object(question_data)

            # Add to appropriate difficulty cache
            difficulty = question.difficulty
            if difficulty in self._questions_cache:
                # Assign a new ID (simple incremental approach)
                max_id = 0
                for diff_questions in self._questions_cache.values():
                    for q in diff_questions:
                        if q.id and q.id > max_id:
                            max_id = q.id
                question.id = max_id + 1

                self._questions_cache[difficulty].append(question)
                return True

        except Exception as e:
            print(f"Error adding custom question: {e}")

        return False

    def get_question_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the question pool.

        Returns:
            Dictionary containing question pool statistics.
        """
        stats = {
            "total_questions": 0,
            "by_difficulty": {},
            "by_type": {},
            "by_category": {},
        }

        for difficulty, questions in self._questions_cache.items():
            stats["by_difficulty"][difficulty] = len(questions)
            stats["total_questions"] += len(questions)

            for question in questions:
                # Count by type
                q_type = question.question_type
                stats["by_type"][q_type] = stats["by_type"].get(q_type, 0) + 1

                # Count by category
                category = question.category
                stats["by_category"][category] = (
                    stats["by_category"].get(category, 0) + 1
                )

        return stats

    def clear_daily_cache(self) -> None:
        """Clear the daily challenge cache (useful for testing or manual reset)."""
        self._daily_challenge_cache.clear()

    def clear_weekly_cache(self) -> None:
        """Clear the weekly challenge cache (useful for testing or manual reset)."""
        self._weekly_challenge_cache.clear()
