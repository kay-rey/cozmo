"""
Data models for the Enhanced Trivia System.
Defines data structures and classes for database entities.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Set
import json


@dataclass
class UserProfile:
    """User profile data model."""

    user_id: int
    total_points: int = 0
    questions_answered: int = 0
    questions_correct: int = 0
    current_streak: int = 0
    best_streak: int = 0
    last_played: Optional[datetime] = None
    daily_challenge_completed: Optional[date] = None
    weekly_challenge_completed: Optional[date] = None
    preferred_difficulty: Optional[str] = None
    created_at: Optional[datetime] = None

    @property
    def accuracy_percentage(self) -> float:
        """Calculate accuracy percentage."""
        if self.questions_answered == 0:
            return 0.0
        return (self.questions_correct / self.questions_answered) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "user_id": self.user_id,
            "total_points": self.total_points,
            "questions_answered": self.questions_answered,
            "questions_correct": self.questions_correct,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "last_played": self.last_played.isoformat() if self.last_played else None,
            "daily_challenge_completed": self.daily_challenge_completed.isoformat()
            if self.daily_challenge_completed
            else None,
            "weekly_challenge_completed": self.weekly_challenge_completed.isoformat()
            if self.weekly_challenge_completed
            else None,
            "preferred_difficulty": self.preferred_difficulty,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """Create UserProfile from dictionary."""
        # Handle datetime parsing
        last_played = None
        if data.get("last_played"):
            last_played = datetime.fromisoformat(data["last_played"])

        daily_challenge_completed = None
        if data.get("daily_challenge_completed"):
            daily_challenge_completed = date.fromisoformat(
                data["daily_challenge_completed"]
            )

        weekly_challenge_completed = None
        if data.get("weekly_challenge_completed"):
            weekly_challenge_completed = date.fromisoformat(
                data["weekly_challenge_completed"]
            )

        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        return cls(
            user_id=data["user_id"],
            total_points=data.get("total_points", 0),
            questions_answered=data.get("questions_answered", 0),
            questions_correct=data.get("questions_correct", 0),
            current_streak=data.get("current_streak", 0),
            best_streak=data.get("best_streak", 0),
            last_played=last_played,
            daily_challenge_completed=daily_challenge_completed,
            weekly_challenge_completed=weekly_challenge_completed,
            preferred_difficulty=data.get("preferred_difficulty"),
            created_at=created_at,
        )


@dataclass
class Question:
    """Question data model."""

    id: Optional[int] = None
    question_text: str = ""
    question_type: str = (
        "multiple_choice"  # "multiple_choice", "true_false", "fill_blank"
    )
    difficulty: str = "medium"  # "easy", "medium", "hard"
    category: str = "general"
    correct_answer: str = ""
    options: Optional[List[str]] = None  # For multiple choice
    answer_variations: Optional[List[str]] = None  # For fill-in-blank
    explanation: Optional[str] = None
    point_value: int = 0
    times_asked: int = 0
    times_correct: int = 0
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Set default point values based on difficulty."""
        if self.point_value == 0:
            point_values = {"easy": 10, "medium": 20, "hard": 30}
            self.point_value = point_values.get(self.difficulty, 20)

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this question."""
        if self.times_asked == 0:
            return 0.0
        return (self.times_correct / self.times_asked) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "question_text": self.question_text,
            "question_type": self.question_type,
            "difficulty": self.difficulty,
            "category": self.category,
            "correct_answer": self.correct_answer,
            "options": json.dumps(self.options) if self.options else None,
            "answer_variations": json.dumps(self.answer_variations)
            if self.answer_variations
            else None,
            "explanation": self.explanation,
            "point_value": self.point_value,
            "times_asked": self.times_asked,
            "times_correct": self.times_correct,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Question":
        """Create Question from dictionary."""
        options = None
        if data.get("options"):
            options = json.loads(data["options"])

        answer_variations = None
        if data.get("answer_variations"):
            answer_variations = json.loads(data["answer_variations"])

        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        return cls(
            id=data.get("id"),
            question_text=data.get("question_text", ""),
            question_type=data.get("question_type", "multiple_choice"),
            difficulty=data.get("difficulty", "medium"),
            category=data.get("category", "general"),
            correct_answer=data.get("correct_answer", ""),
            options=options,
            answer_variations=answer_variations,
            explanation=data.get("explanation"),
            point_value=data.get("point_value", 0),
            times_asked=data.get("times_asked", 0),
            times_correct=data.get("times_correct", 0),
            created_at=created_at,
        )


@dataclass
class UserAchievement:
    """User achievement data model."""

    id: Optional[int] = None
    user_id: int = 0
    achievement_id: str = ""
    unlocked_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "achievement_id": self.achievement_id,
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserAchievement":
        """Create UserAchievement from dictionary."""
        unlocked_at = None
        if data.get("unlocked_at"):
            unlocked_at = datetime.fromisoformat(data["unlocked_at"])

        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", 0),
            achievement_id=data.get("achievement_id", ""),
            unlocked_at=unlocked_at,
        )


@dataclass
class WeeklyRanking:
    """Weekly ranking data model."""

    id: Optional[int] = None
    user_id: int = 0
    week_start: Optional[date] = None
    points: int = 0
    rank: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "week_start": self.week_start.isoformat() if self.week_start else None,
            "points": self.points,
            "rank": self.rank,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeeklyRanking":
        """Create WeeklyRanking from dictionary."""
        week_start = None
        if data.get("week_start"):
            week_start = date.fromisoformat(data["week_start"])

        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", 0),
            week_start=week_start,
            points=data.get("points", 0),
            rank=data.get("rank"),
        )


@dataclass
class GameSession:
    """Game session data model for tracking active games."""

    id: Optional[int] = None
    channel_id: int = 0
    user_id: int = 0
    question_id: Optional[int] = None
    difficulty: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_completed: bool = False
    is_challenge: bool = False

    # Runtime properties (not stored in database)
    question: Optional[Question] = field(default=None, init=False)
    participants: Set[int] = field(default_factory=set, init=False)
    timeout_duration: int = field(default=30, init=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "difficulty": self.difficulty,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "is_completed": self.is_completed,
            "is_challenge": self.is_challenge,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameSession":
        """Create GameSession from dictionary."""
        start_time = None
        if data.get("start_time"):
            start_time = datetime.fromisoformat(data["start_time"])

        end_time = None
        if data.get("end_time"):
            end_time = datetime.fromisoformat(data["end_time"])

        return cls(
            id=data.get("id"),
            channel_id=data.get("channel_id", 0),
            user_id=data.get("user_id", 0),
            question_id=data.get("question_id"),
            difficulty=data.get("difficulty"),
            start_time=start_time,
            end_time=end_time,
            is_completed=data.get("is_completed", False),
            is_challenge=data.get("is_challenge", False),
        )


@dataclass
class AnswerResult:
    """Result of processing a user's answer."""

    is_correct: bool
    points_earned: int
    time_taken: float
    achievement_unlocked: Optional[str] = None
    streak_bonus: int = 0
    explanation: Optional[str] = None


@dataclass
class UserStats:
    """Comprehensive user statistics."""

    user_profile: UserProfile
    accuracy_percentage: float
    points_per_category: Dict[str, int] = field(default_factory=dict)
    difficulty_breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)
    recent_performance: List[bool] = field(default_factory=list)  # Last 10 answers
    achievements_count: int = 0
    current_rank: Optional[int] = None
    rank_change: Optional[int] = None


@dataclass
class LeaderboardEntry:
    """Leaderboard entry data model."""

    rank: int
    user_id: int
    username: str
    total_points: int
    accuracy_percentage: float
    questions_answered: int
    current_streak: int
    rank_change: Optional[int] = None


# Constants for question types and difficulties
QUESTION_TYPES = ["multiple_choice", "true_false", "fill_blank"]
DIFFICULTY_LEVELS = ["easy", "medium", "hard"]
POINT_VALUES = {"easy": 10, "medium": 20, "hard": 30}

# Achievement definitions
ACHIEVEMENTS = {
    "hot_streak": {
        "name": "Hot Streak",
        "description": "Answer 5 questions correctly in a row",
        "requirement": {"type": "streak", "value": 5},
        "reward_points": 50,
        "emoji": "🔥",
    },
    "galaxy_expert": {
        "name": "Galaxy Expert",
        "description": "Answer 10 questions correctly in a row",
        "requirement": {"type": "streak", "value": 10},
        "reward_points": 100,
        "emoji": "⭐",
    },
    "dedicated_fan": {
        "name": "Dedicated Fan",
        "description": "Play trivia for 7 consecutive days",
        "requirement": {"type": "daily_streak", "value": 7},
        "reward_points": 200,
        "emoji": "💙",
    },
    "trivia_master": {
        "name": "Trivia Master",
        "description": "Answer 100 questions correctly",
        "requirement": {"type": "total_correct", "value": 100},
        "reward_points": 500,
        "emoji": "👑",
    },
    "perfectionist": {
        "name": "Perfectionist",
        "description": "Maintain 90% accuracy over 50 questions",
        "requirement": {"type": "accuracy", "value": 90, "min_questions": 50},
        "reward_points": 300,
        "emoji": "💯",
    },
}
