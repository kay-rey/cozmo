# ⭐ Cozmo - The Ultimate LA Galaxy Discord Bot ⭐

> _"Bringing the Galaxy to your Discord server, one command at a time!"_

**Cozmo** is your dedicated LA Galaxy companion bot, packed with everything a Galaxy fan needs: live match updates, MLS standings, player stats, and brain-teasing trivia that'll test even the most devoted supporters. Whether you're tracking the next big match or settling debates about Galaxy history, Cozmo's got your back!

🚀 **Now deployed on Render** with enhanced reliability and 24/7 uptime!

## 🚀 What Makes Cozmo Special?

### 🏟️ **Live Match Intelligence**

- **`!nextmatch`** - Never miss another Galaxy game! Get instant details on upcoming matches
- Real-time opponent info, kickoff times, and venue details
- Smart formatting that works beautifully in Discord

### 📊 **MLS Mastery**

- **`/standings`** - See MLS teams organized by conference with optional filtering
- **`/playerstats [player]`** - Deep dive into your favorite player's performance
- **`/roster [team]`** - View complete team rosters organized by position
- **`/lineup [match_id]`** - Display match lineups and starting XI
- Clean, readable embeds that make stats actually enjoyable

### 🧠 **Enhanced Galaxy Trivia System**

#### **Basic Trivia**

- **`!trivia [difficulty]`** - Start a trivia game with optional difficulty (easy/medium/hard)
- Interactive emoji reactions (🇦 🇧 🇨 🇩) for multiple choice questions
- Type answers for fill-in-the-blank questions
- 45+ questions covering club history, players, matches, stadium, and records

#### **Challenge System**

- **`!dailychallenge`** or **`!daily`** - Daily challenge with **double points**
- **`!weeklychallenge`** or **`!weekly`** - Weekly challenge with **triple points** (5 questions)
- **`!challengeprogress`** or **`!progress`** - Check your challenge status

#### **Statistics & Progress**

- **`!triviastats [@user]`** or **`!stats [@user]`** - View comprehensive trivia statistics
- **`!achievements [@user]`** - Display unlocked achievements with dates
- **`!triviareport`** or **`!report`** - Detailed performance breakdown by category
- **`!leaderboard [period]`** or **`!lb [period]`** - View top players (all/daily/weekly/monthly)
- **`!myrank`** or **`!rank`** - See your current rank and nearby positions

### 🛡️ **Built Like a Tank**

- Comprehensive error handling that keeps the bot running smooth
- Rate limiting to respect API boundaries
- Automatic session management and cleanup
- Detailed logging for troubleshooting

## ⚡ Quick Start Guide

### 1. **Get Your Dependencies**

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync
```

### 2. **Set Up Your Environment**

```bash
cp .env.template .env
# Edit .env with your tokens (see Configuration section below)
```

### 3. **Test Everything Works**

```bash
uv run python tests/verify_bot_setup.py
```

### 4. **Launch Cozmo!**

```bash
uv run python main.py
```

_Watch for "Cozmo is online and ready to cheer for the Galaxy!" - that's your green light!_

## 🚀 Why uv?

This project now uses [uv](https://docs.astral.sh/uv/) - an extremely fast Python package manager written in Rust. Here's why:

- **⚡ 10-100x faster** than pip for dependency resolution and installation
- **🔒 Reproducible builds** with `uv.lock` ensuring consistent environments
- **📦 All-in-one tool** replacing pip, pip-tools, pipx, poetry, pyenv, and more
- **🛠️ Better project management** with `pyproject.toml` configuration
- **💾 Disk efficient** with global caching and dependency deduplication

### Common uv Commands

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add package-name

# Run Python scripts
uv run python script.py

# Run tests
uv run python -m pytest

# Update dependencies
uv lock --upgrade
```

## 🎮 How to Play Enhanced Trivia

### 🚀 **Getting Started**

1. **Basic Trivia**: Type `!trivia` to start with a random difficulty question
2. **Choose Difficulty**: Use `!trivia easy`, `!trivia medium`, or `!trivia hard`
3. **Answer Questions**:
   - **Multiple Choice**: React with 🇦, 🇧, 🇨, or 🇩
   - **True/False**: React with ✅ (true) or ❌ (false)
   - **Fill-in-the-Blank**: Type your answer in chat

### 🏆 **Challenge System**

#### **Daily Challenge**

- Available once per day
- **Double points** for correct answers
- Harder questions (usually medium/hard difficulty)
- Use `!daily` or `!dailychallenge`

#### **Weekly Challenge**

- Available once per week (resets Monday)
- **5 questions** with **triple points**
- Mix of medium and hard questions
- Use `!weekly` or `!weeklychallenge`
- Can be completed over multiple sessions

### 📊 **Scoring & Progression**

- **Easy Questions**: 10 points
- **Medium Questions**: 20 points
- **Hard Questions**: 30 points
- **Daily Challenge**: 2x points
- **Weekly Challenge**: 3x points
- Build streaks for bonus achievements!

### 🏅 **Achievements System**

Unlock achievements by:

- Answering questions correctly
- Building answer streaks
- Completing challenges
- Reaching point milestones
- Mastering specific categories

View your achievements with `!achievements`

### 📈 **Track Your Progress**

- `!stats` - Overall performance and accuracy
- `!report` - Detailed breakdown by category and difficulty
- `!rank` - Your current leaderboard position
- `!lb` - See top players (daily/weekly/monthly/all-time)

## 🎮 Command Arsenal

### Slash Commands (Modern Discord Interface)

| Command                   | What It Does                             | Example                               |
| ------------------------- | ---------------------------------------- | ------------------------------------- |
| `/standings [conference]` | MLS teams by conference (west/east/both) | `/standings conference:west`          |
| `/playerstats [name]`     | Player statistics and detailed info      | `/playerstats player_name:Chicharito` |
| `/roster [team]`          | Team roster organized by position        | `/roster team_name:Inter Miami CF`    |
| `/lineup [match_id]`      | Match lineup and starting XI             | `/lineup match_id:12345`              |

### Prefix Commands (Classic Style)

#### **Match & General Commands**

| Command      | What It Does                           | Example      |
| ------------ | -------------------------------------- | ------------ |
| `!nextmatch` | Shows LA Galaxy's next scheduled match | `!nextmatch` |
| `!sync`      | Sync slash commands (owner only)       | `!sync`      |

#### **Enhanced Trivia Commands**

| Command                 | What It Does                                  | Example            |
| ----------------------- | --------------------------------------------- | ------------------ |
| `!trivia [difficulty]`  | Start trivia game (easy/medium/hard)          | `!trivia medium`   |
| `!dailychallenge`       | Daily challenge (double points)               | `!daily`           |
| `!weeklychallenge`      | Weekly challenge (triple points, 5 questions) | `!weekly`          |
| `!triviastats [@user]`  | View trivia statistics                        | `!stats @username` |
| `!achievements [@user]` | Display unlocked achievements                 | `!achievements`    |
| `!triviareport`         | Performance breakdown by category             | `!report`          |
| `!leaderboard [period]` | View leaderboard (all/daily/weekly/monthly)   | `!lb weekly`       |
| `!myrank`               | Show your current rank                        | `!rank`            |
| `!challengeprogress`    | Check challenge status                        | `!progress`        |

## 🔧 Configuration Deep Dive

### Required Environment Variables

Create your `.env` file with these essentials:

```bash
# Your Discord bot token (get from Discord Developer Portal)
DISCORD_TOKEN="your_discord_bot_token_here"

# TheSportsDB API key (get from thesportsdb.com)
SPORTS_API_KEY="your_sports_api_key_here"

# Optional: Channel ID for news updates (currently disabled)
NEWS_CHANNEL_ID=your_news_channel_id_here
```

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and bot
3. Enable these **Privileged Gateway Intents**:
   - ✅ Message Content Intent
   - ✅ Server Members Intent (optional)
4. Copy your bot token to `.env`
5. Invite bot with these permissions:
   - Send Messages
   - Use Slash Commands
   - Use External Emojis
   - Add Reactions
   - Read Message History
   - Embed Links

### API Keys

- **TheSportsDB**: Free tier available at [thesportsdb.com](https://www.thesportsdb.com/api.php)

  - 🎯 **Used for**: Player statistics and detailed player information
  - ⚠️ **Note**: Free tier has limited roster data
  - 💰 **Pro version** ($3/month) provides complete data access

- **ESPN API**: No key required (unofficial public API)
  - 🏟️ **Used for**: Complete team rosters and live standings
  - ✅ **Provides**: Full roster data with positions and player details
  - 🔄 **Fallback**: Automatically falls back to TheSportsDB if unavailable

## 🧪 Testing & Quality Assurance

### Full Test Suite

```bash
python3 tests/run_all_tests.py
```

### Individual Test Categories

```bash
python3 tests/test_code_structure.py    # Code architecture validation
python3 tests/test_bot_final.py         # End-to-end integration tests
```

### Verify Your Setup

```bash
python3 tests/verify_bot_setup.py       # Pre-flight checks
```

## 📚 Documentation Hub

- **[Features Summary](docs/FEATURES_SUMMARY.md)** - Complete feature breakdown
- **[Enhanced Error Handling](docs/ENHANCED_ERROR_HANDLING_SUMMARY.md)** - Advanced error recovery and logging
- **[Security Guidelines](docs/SECURITY_GUIDELINES.md)** - Keep your bot secure
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Production deployment instructions
- **[Cleanup Summary](docs/CLEANUP_SUMMARY.md)** - Recent project organization improvements

## 🏗️ Architecture Overview

Cozmo is built with a modular, scalable architecture that makes adding new features a breeze:

```
cozmo/
├── 🤖 main.py                    # Bot brain & startup logic
├── ⚙️ config.py                  # Environment & configuration management
├── 🌐 health_server.py           # Render deployment health check
├── 📦 pyproject.toml             # Python dependencies and project config
├── 🔒 uv.lock                    # Locked dependency versions
├── 🚀 render.yaml               # Render deployment configuration
├── 📋 .env.template              # Configuration template
│
├── 🌐 api/                       # External service integrations
│   ├── sports_api.py             # TheSportsDB client
│   ├── espn_api.py               # ESPN API client
│   └── news_api.py               # RSS feed client
│
├── 🎯 cogs/                      # Feature modules (auto-loaded)
│   ├── matchday.py               # Match schedules & info
│   ├── stats.py                  # Player stats & MLS standings
│   ├── trivia.py                 # Interactive trivia games
│   ├── enhanced_trivia.py        # Advanced trivia system
│   ├── achievement_commands.py   # Achievement system
│   └── leaderboard_commands.py   # Leaderboard functionality
│
├── 🗃️ data/                      # Data storage
│   ├── trivia_questions.py       # 45+ Galaxy trivia questions
│   └── trivia.db                 # SQLite database
│
├── 🛠️ utils/                     # Core utilities
│   ├── question_engine.py        # Question management
│   ├── scoring_engine.py         # Scoring system
│   ├── user_manager.py           # User data management
│   ├── achievement_system.py     # Achievement tracking
│   └── database.py               # Database operations
│
├── 🧪 tests/                     # Streamlined test suite
│   ├── run_all_tests.py          # Master test runner
│   ├── test_bot_final.py         # Integration tests
│   └── verify_bot_setup.py       # Setup validation
│
├── 📖 docs/                      # Comprehensive documentation
│   ├── FEATURES_SUMMARY.md       # Feature overview
│   ├── DEPLOYMENT_GUIDE.md       # Production deployment
│   ├── CLEANUP_SUMMARY.md        # Project organization
│   └── SECURITY_GUIDELINES.md    # Security practices
│
├── 📊 logs/                      # Runtime logs & debugging
├── 🔧 scripts/                   # Utility scripts
└── 📝 .kiro/specs/               # Development specifications
```

## 🔧 Technical Requirements

- **Python**: 3.8+ (tested on 3.9, 3.10, 3.11)
- **Discord.py**: 2.3.0+ (for modern Discord features)
- **API Access**: TheSportsDB account (free tier works great)
- **Permissions**: Bot needs message & reaction permissions

### Required Discord Permissions

For full functionality, ensure your bot has these permissions:

- ✅ **Send Messages** - Basic bot communication
- ✅ **Read Message History** - Context for commands
- ✅ **Add Reactions** - Trivia game interactions
- ✅ **Manage Messages** - Clear reactions after trivia (prevents clutter)
- ✅ **Use Slash Commands** - Modern Discord interface
- ✅ **Embed Links** - Rich content display
- ✅ **Attach Files** - Image support in trivia

**Troubleshooting**: If you see "Missing permissions to clear reactions" warnings, grant the **Manage Messages** permission to fix this.

## 🚀 Deployment Options

### Local Development

```bash
python3 main.py
```

### Production Deployment

- **Render**: `render.yaml` included for one-click deployment (recommended) ✅ **Currently Deployed**
- **Heroku**: Compatible with Python buildpack
- **Railway**: Compatible with Python buildpack
- **Docker**: Optional containerization support available

#### Render Deployment Features

- 🌐 **Web service** with health check endpoint
- 🔄 **Auto-restart** on failures
- 📊 **Built-in logging** and monitoring
- 🆓 **Free tier** compatible (750 hours/month)
- ⚡ **Instant deployment** from GitHub

## 🎯 What's Next?

### Recently Added Features ✨

- 🚀 **Production Deployment**: Successfully deployed on Render with 24/7 uptime
- 🧹 **Project Cleanup**: Streamlined codebase with organized file structure
- 🔧 **Enhanced Trivia System**: 45+ questions across three difficulty levels
- 🛡️ **Robust Error Handling**: Advanced error recovery and logging system
- 🆕 **Modern Slash Commands**: Native Discord slash command support
- 👥 **Complete Team Rosters**: Full team rosters using hybrid API approach
- 📋 **Match Lineups**: Starting XI and substitute information
- 🏟️ **Live Standings**: Real-time MLS standings with comprehensive stats
- 🔄 **Hybrid API System**: Multiple data sources for complete information
- ⚡ **Health Monitoring**: Built-in health check for deployment reliability

### Planned Features

- 📰 **News System**: Re-enable automated news updates
- 🏆 **Match Predictions**: AI-powered match outcome predictions
- 📱 **Mobile Notifications**: Push notifications for important matches
- 📈 **Analytics Dashboard**: Track bot usage and popular commands
- 🎯 **Enhanced Match Data**: Live scores and match events

### Contributing

Cozmo follows **spec-driven development**! Check out `.kiro/specs/` for:

- Feature requirements and user stories
- Technical design documents
- Implementation task breakdowns

Want to add a feature? Start by creating a spec!

## 🛡️ Security & Best Practices

- 🔐 **Token Security**: Never commit tokens to git
- 🚦 **Rate Limiting**: Built-in API rate limiting
- 🧹 **Session Management**: Automatic cleanup of HTTP sessions
- 📝 **Comprehensive Logging**: Full audit trail for debugging
- ⚡ **Error Recovery**: Graceful handling of API failures

## 📄 License

This project is open source - see [LICENSE](LICENSE) for details.

---

## 💫 Fun Facts About Cozmo

- 🎯 **45+ Trivia Questions**: Comprehensive Galaxy knowledge across three difficulty levels
- ⚡ **Modern Slash Commands**: Native Discord interface with autocomplete
- 🛡️ **99.9% Uptime**: Production-ready deployment on Render with health monitoring
- 🌟 **Galaxy Focused**: Every feature designed with LA Galaxy fans in mind
- 🤖 **Smart Caching**: Reduces API calls while keeping data fresh
- 👥 **Complete MLS Coverage**: All 29 MLS teams supported for rosters and stats
- 📊 **Rich Embeds**: Beautiful, branded Discord embeds with team badges
- 🧹 **Clean Codebase**: Recently streamlined with organized file structure
- 🔧 **Enhanced Systems**: Advanced trivia, achievements, and leaderboards
- 🚀 **Cloud Native**: Built for modern deployment with health checks and monitoring

**Ready to bring the Galaxy to your Discord server? Let's get Cozmo running! ⭐**
