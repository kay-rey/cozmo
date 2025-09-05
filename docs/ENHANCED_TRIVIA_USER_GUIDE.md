# Enhanced Trivia System - User Guide

## Overview

The Enhanced Trivia System transforms Cozmo's basic trivia functionality into a comprehensive gaming experience for LA Galaxy fans. Test your knowledge, earn achievements, compete on leaderboards, and participate in daily and weekly challenges!

## Getting Started

### Basic Trivia Commands

#### `!trivia [difficulty]`

Start a trivia game with optional difficulty selection.

**Usage:**

- `!trivia` - Random difficulty question
- `!trivia easy` - Easy question (10 points)
- `!trivia medium` - Medium question (20 points)
- `!trivia hard` - Hard question (30 points)

**How to Answer:**

- **Multiple Choice:** React with 🇦, 🇧, 🇨, or 🇩
- **True/False:** Type "true" or "false"
- **Fill-in-the-Blank:** Type your answer

**Time Limit:** 30 seconds per question

---

## Statistics & Progress

### `!triviastats [user]`

View comprehensive trivia statistics for yourself or another user.

**Shows:**

- Total points earned
- Questions answered and accuracy percentage
- Current and best streak
- Current leaderboard rank
- Performance breakdown by difficulty
- Recent performance (last 10 questions)

**Example:**

```
!triviastats
!triviastats @username
```

### `!triviareport`

Get a detailed performance analysis with personalized insights.

**Includes:**

- Overall performance metrics
- Difficulty breakdown with points per level
- Top categories by points earned
- Personalized recommendations
- Recent performance trends

---

## Achievements System

### `!achievements [user]`

Display earned achievements with unlock dates.

**Achievement Categories:**

- **Streak Achievements:** For consecutive correct answers
- **Participation:** For regular play and dedication
- **Mastery:** For exceptional performance
- **Challenge:** For completing daily/weekly challenges

**Popular Achievements:**

- 🔥 **Hot Streak** - Answer 5 questions correctly in a row (50 bonus points)
- ⭐ **Galaxy Expert** - Answer 10 questions correctly in a row (100 bonus points)
- 💙 **Dedicated Fan** - Play trivia for 7 consecutive days (200 bonus points)

---

## Leaderboards & Rankings

### `!leaderboard [period]`

View the top players and their rankings.

**Periods:**

- `!leaderboard` or `!leaderboard all` - All-time rankings
- `!leaderboard weekly` - Current week rankings (resets Monday)
- `!leaderboard monthly` - Current month rankings

**Shows:** Rank, username, total points, and accuracy percentage

### `!myrank`

Check your current position in the overall leaderboard and see nearby players.

---

## Challenge System

### Daily Challenges

#### `!dailychallenge`

Participate in the daily challenge for double points!

**Features:**

- One special question per day
- Double point rewards
- 45-second time limit
- Can only be completed once per day
- Resets at midnight

### Weekly Challenges

#### `!weeklychallenge`

Take on the weekly challenge for maximum rewards!

**Features:**

- 5 questions in sequence
- Triple point rewards
- 60-second time limit per question
- Special completion badge
- New challenge every Monday
- Can continue across multiple sessions

---

## Question Types

### Multiple Choice

- Choose from 4 options (A, B, C, D)
- React with the corresponding emoji
- Most common question type

### True/False

- Simple true or false questions
- Type "true" or "false" to answer
- Quick and straightforward

### Fill-in-the-Blank

- Type the missing word or phrase
- Case-insensitive matching
- Multiple acceptable answers possible

---

## Scoring System

### Point Values

- **Easy Questions:** 10 points
- **Medium Questions:** 20 points
- **Hard Questions:** 30 points
- **Daily Challenge:** Double points
- **Weekly Challenge:** Triple points

### Bonus Points

- **Achievement Unlocks:** Varies by achievement
- **Streak Bonuses:** Additional points for consecutive correct answers
- **Challenge Completion:** Extra rewards for completing challenges

### Streaks

- **Current Streak:** Consecutive correct answers
- **Best Streak:** Your all-time best streak
- Streaks reset when you answer incorrectly
- Higher streaks unlock special achievements

---

## Tips for Success

### Improving Your Performance

1. **Start with Easy Questions** - Build confidence and streaks
2. **Play Daily** - Consistency improves knowledge retention
3. **Complete Challenges** - Maximum point opportunities
4. **Learn from Mistakes** - Pay attention to explanations
5. **Study LA Galaxy History** - Many questions focus on team history

### Strategy Tips

1. **Time Management** - Don't rush, but don't overthink
2. **Read Carefully** - Pay attention to question wording
3. **Use Process of Elimination** - For multiple choice questions
4. **Stay Consistent** - Regular play improves performance
5. **Challenge Yourself** - Try harder difficulties as you improve

---

## Frequently Asked Questions

### General Questions

**Q: Can I play multiple games at once?**
A: No, only one trivia game can be active per channel at a time.

**Q: What happens if I don't answer in time?**
A: The question times out and shows the correct answer. No points are awarded.

**Q: Can I change my answer?**
A: No, your first answer is final.

**Q: Do I lose points for wrong answers?**
A: No, you never lose points. Wrong answers just don't add to your score.

### Achievements & Progress

**Q: How do I unlock achievements?**
A: Achievements unlock automatically when you meet their requirements during gameplay.

**Q: Can I see what achievements are available?**
A: Currently, achievements are discovered by playing. More will be revealed as you progress!

**Q: Do my stats carry over if the bot restarts?**
A: Yes, all your progress is saved permanently in the database.

### Challenges

**Q: What if I start a weekly challenge but don't finish?**
A: You can continue your weekly challenge later. Progress is saved between sessions.

**Q: Can I retry a daily challenge if I get it wrong?**
A: No, you get one attempt per day. Come back tomorrow for a new challenge!

**Q: When do challenges reset?**
A: Daily challenges reset at midnight. Weekly challenges reset every Monday.

### Technical Issues

**Q: The bot isn't responding to my answers**
A: Make sure you're using the correct format (reactions for multiple choice, text for others).

**Q: I think my stats are wrong**
A: Contact a server administrator who can check your statistics.

**Q: Can I reset my statistics?**
A: Only server administrators can reset user statistics.

---

## Administrator Commands

_Note: These commands require administrator permissions_

### `!triviaconfig [setting] [value]`

View or modify trivia system settings.

**Examples:**

- `!triviaconfig` - View current settings
- `!triviaconfig timeout 45` - Set question timeout to 45 seconds

### `!resetstats [user]`

Reset a user's trivia statistics (use with caution).

### `!addquestion`

Add custom trivia questions through a guided process.

---

## Support & Feedback

If you encounter any issues or have suggestions for the Enhanced Trivia System:

1. **Check this guide** for common questions and solutions
2. **Contact server administrators** for technical issues
3. **Report bugs** through the appropriate server channels
4. **Suggest new features** to help improve the system

---

## Version Information

**Enhanced Trivia System v2.0**

- Persistent scoring and statistics
- Achievement system with rewards
- Daily and weekly challenges
- Multiple question types
- Comprehensive leaderboards
- Performance analytics and insights

---

_Have fun testing your LA Galaxy knowledge and climbing the leaderboards! 🌟⚽_
