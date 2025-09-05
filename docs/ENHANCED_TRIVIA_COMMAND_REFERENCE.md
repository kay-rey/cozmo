# Enhanced Trivia System - Command Reference

## Quick Reference

| Command            | Description         | Usage                                 | Permissions |
| ------------------ | ------------------- | ------------------------------------- | ----------- |
| `!trivia`          | Start trivia game   | `!trivia [easy\|medium\|hard]`        | Everyone    |
| `!triviastats`     | View statistics     | `!triviastats [@user]`                | Everyone    |
| `!achievements`    | View achievements   | `!achievements [@user]`               | Everyone    |
| `!triviareport`    | Performance report  | `!triviareport`                       | Everyone    |
| `!leaderboard`     | View rankings       | `!leaderboard [all\|weekly\|monthly]` | Everyone    |
| `!myrank`          | Your current rank   | `!myrank`                             | Everyone    |
| `!dailychallenge`  | Daily challenge     | `!dailychallenge`                     | Everyone    |
| `!weeklychallenge` | Weekly challenge    | `!weeklychallenge`                    | Everyone    |
| `!triviaconfig`    | System settings     | `!triviaconfig [setting] [value]`     | Admin       |
| `!resetstats`      | Reset user stats    | `!resetstats @user`                   | Admin       |
| `!addquestion`     | Add custom question | `!addquestion`                        | Admin       |

---

## User Commands

### Game Commands

#### `!trivia [difficulty]`

**Description:** Start a new trivia game with optional difficulty selection.

**Parameters:**

- `difficulty` (optional): `easy`, `medium`, or `hard`

**Examples:**

```
!trivia
!trivia easy
!trivia medium
!trivia hard
```

**Response:** Displays a trivia question with appropriate answer format.

**Notes:**

- If no difficulty specified, uses random or user preference
- Only one game per channel at a time
- 30-second time limit per question

---

#### `!dailychallenge`

**Aliases:** `!daily`

**Description:** Start today's daily challenge for double points.

**Parameters:** None

**Example:**

```
!dailychallenge
```

**Response:** Special daily question with double point reward.

**Notes:**

- One attempt per day per user
- 45-second time limit
- Resets at midnight
- Cannot retry if failed

---

#### `!weeklychallenge`

**Aliases:** `!weekly`

**Description:** Start or continue this week's challenge (5 questions, triple points).

**Parameters:** None

**Example:**

```
!weeklychallenge
```

**Response:** Current weekly challenge question or progress status.

**Notes:**

- 5 questions total
- Triple point rewards
- 60-second time limit per question
- Can continue across sessions
- Resets every Monday

---

### Statistics Commands

#### `!triviastats [user]`

**Aliases:** `!stats`

**Description:** Display comprehensive trivia statistics.

**Parameters:**

- `user` (optional): Discord user mention or ID

**Examples:**

```
!triviastats
!triviastats @username
!triviastats 123456789012345678
```

**Response:** Detailed statistics embed showing:

- Total points and accuracy
- Current and best streaks
- Leaderboard rank
- Difficulty breakdown
- Recent performance

---

#### `!triviareport`

**Aliases:** `!report`

**Description:** Generate detailed performance analysis with insights.

**Parameters:** None

**Example:**

```
!triviareport
```

**Response:** Comprehensive report including:

- Overall performance metrics
- Category and difficulty breakdowns
- Personalized recommendations
- Performance trends

---

#### `!achievements [user]`

**Description:** Display earned achievements with unlock dates.

**Parameters:**

- `user` (optional): Discord user mention or ID

**Examples:**

```
!achievements
!achievements @username
```

**Response:** Achievement showcase organized by category with:

- Achievement names and descriptions
- Unlock dates
- Progress completion percentage

---

### Leaderboard Commands

#### `!leaderboard [period]`

**Description:** Display top players and rankings.

**Parameters:**

- `period` (optional): `all`, `weekly`, or `monthly`

**Examples:**

```
!leaderboard
!leaderboard all
!leaderboard weekly
!leaderboard monthly
```

**Response:** Formatted leaderboard showing:

- Player ranks and usernames
- Total points
- Accuracy percentages

**Notes:**

- Default shows all-time rankings
- Weekly resets every Monday
- Monthly resets on the 1st

---

#### `!myrank`

**Description:** Show your current leaderboard position and nearby players.

**Parameters:** None

**Example:**

```
!myrank
```

**Response:** Your rank with context showing players above and below you.

---

## Administrator Commands

### Configuration Commands

#### `!triviaconfig [setting] [value]`

**Description:** View or modify trivia system configuration.

**Permissions:** Administrator

**Parameters:**

- `setting` (optional): Configuration setting name
- `value` (optional): New value for the setting

**Examples:**

```
!triviaconfig
!triviaconfig timeout 45
!triviaconfig points_easy 15
```

**Available Settings:**

- `timeout`: Question timeout in seconds (default: 30)
- `points_easy`: Points for easy questions (default: 10)
- `points_medium`: Points for medium questions (default: 20)
- `points_hard`: Points for hard questions (default: 30)
- `daily_multiplier`: Daily challenge point multiplier (default: 2)
- `weekly_multiplier`: Weekly challenge point multiplier (default: 3)

**Response:** Current configuration or confirmation of changes.

---

### User Management Commands

#### `!resetstats <user>`

**Description:** Reset a user's trivia statistics (use with extreme caution).

**Permissions:** Administrator

**Parameters:**

- `user` (required): Discord user mention or ID

**Examples:**

```
!resetstats @username
!resetstats 123456789012345678
```

**Response:** Confirmation of statistics reset.

**Warning:** This action is irreversible and will delete all user progress.

---

### Content Management Commands

#### `!addquestion`

**Description:** Add custom trivia questions through guided process.

**Permissions:** Administrator

**Parameters:** None

**Example:**

```
!addquestion
```

**Response:** Interactive question creation wizard that prompts for:

- Question text
- Question type (multiple choice, true/false, fill-in-blank)
- Difficulty level
- Category
- Correct answer
- Options (for multiple choice)
- Answer variations (for fill-in-blank)
- Explanation (optional)

---

## Response Formats

### Question Display Format

**Multiple Choice:**

```
🎯 Trivia Question (Medium - 20 points)

Who is LA Galaxy's all-time leading goalscorer?

🇦 Landon Donovan
🇧 Carlos Vela
🇨 Robbie Keane
🇩 David Beckham

React with 🇦, 🇧, 🇨, or 🇩 to answer!
Time remaining: 30 seconds
```

**True/False:**

```
🎯 Trivia Question (Easy - 10 points)

LA Galaxy was founded in 1996.

Type 'true' or 'false' to answer!
Time remaining: 30 seconds
```

**Fill-in-the-Blank:**

```
🎯 Trivia Question (Hard - 30 points)

LA Galaxy's home stadium is called _______ Stadium.

Type your answer!
Time remaining: 30 seconds
```

### Result Display Format

**Correct Answer:**

```
✅ Correct!

You earned 20 points!
Current streak: 3
Total points: 1,250

The answer was: Landon Donovan
Explanation: Landon Donovan scored 145 goals for LA Galaxy...
```

**Incorrect Answer:**

```
❌ Incorrect

The correct answer was: Landon Donovan
Explanation: Landon Donovan scored 145 goals for LA Galaxy...

Better luck next time! Your streak has been reset.
```

**Timeout:**

```
⏰ Time's Up!

The correct answer was: Landon Donovan
Explanation: Landon Donovan scored 145 goals for LA Galaxy...

Try again with !trivia
```

---

## Error Messages

### Common Error Responses

**Game Already Active:**

```
🎮 Game Already Active
There's already a trivia game active in this channel!
Finish it first or wait for it to timeout.
```

**Challenge Already Completed:**

```
✅ Daily Challenge Complete
You've already completed today's daily challenge!
Come back tomorrow for a new one.
```

**Invalid Difficulty:**

```
❌ Invalid Difficulty
Please choose from: easy, medium, hard
```

**Permission Denied:**

```
❌ Permission Denied
You don't have permission to use this command.
```

**User Not Found:**

```
❌ User Not Found
Could not find the specified user.
```

---

## Status Indicators

### Game Status Icons

- 🎯 Active trivia question
- 🌟 Daily challenge
- 👑 Weekly challenge
- ✅ Correct answer
- ❌ Incorrect answer
- ⏰ Timeout
- 🎮 Game already active

### Achievement Icons

- 🔥 Streak achievements
- ⭐ Mastery achievements
- 💙 Dedication achievements
- 🏆 Special achievements
- 📈 Progress achievements

### Leaderboard Icons

- 🥇 1st place
- 🥈 2nd place
- 🥉 3rd place
- 📊 General ranking

---

## Integration Notes

### Discord Permissions Required

- Send Messages
- Embed Links
- Add Reactions
- Read Message History
- Use External Emojis (optional)

### Channel Compatibility

- Works in any text channel where bot has permissions
- One game per channel limitation
- Cross-channel user statistics

### Data Persistence

- All user data persists across bot restarts
- Statistics stored in SQLite database
- Automatic backup system for data protection

---

_For technical support or feature requests, contact your server administrators._
