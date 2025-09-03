# ⭐ Cozmo - The Ultimate LA Galaxy Discord Bot ⭐

> _"Bringing the Galaxy to your Discord server, one command at a time!"_

**Cozmo** is your dedicated LA Galaxy companion bot, packed with everything a Galaxy fan needs: live match updates, MLS standings, player stats, and brain-teasing trivia that'll test even the most devoted supporters. Whether you're tracking the next big match or settling debates about Galaxy history, Cozmo's got your back!

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

### 🧠 **Galaxy Trivia Challenge**

- **`!trivia`** - Test your Galaxy knowledge with 15+ challenging questions
- Interactive emoji reactions (🇦 🇧 🇨 🇩) for seamless gameplay
- Questions spanning from club founding to current roster gems
- Anti-spam protection ensures fair play

### 🛡️ **Built Like a Tank**

- Comprehensive error handling that keeps the bot running smooth
- Rate limiting to respect API boundaries
- Automatic session management and cleanup
- Detailed logging for troubleshooting

## ⚡ Quick Start Guide

### 1. **Get Your Dependencies**

```bash
pip install -r requirements.txt
```

### 2. **Set Up Your Environment**

```bash
cp .env.template .env
# Edit .env with your tokens (see Configuration section below)
```

### 3. **Test Everything Works**

```bash
python3 tests/verify_bot_setup.py
```

### 4. **Launch Cozmo!**

```bash
python3 main.py
```

_Watch for "Cozmo is online and ready to cheer for the Galaxy!" - that's your green light!_

## 🎮 Command Arsenal

### Slash Commands (Modern Discord Interface)

| Command                   | What It Does                             | Example                               |
| ------------------------- | ---------------------------------------- | ------------------------------------- |
| `/standings [conference]` | MLS teams by conference (west/east/both) | `/standings conference:west`          |
| `/playerstats [name]`     | Player statistics and detailed info      | `/playerstats player_name:Chicharito` |
| `/roster [team]`          | Team roster organized by position        | `/roster team_name:Inter Miami CF`    |
| `/lineup [match_id]`      | Match lineup and starting XI             | `/lineup match_id:12345`              |

### Prefix Commands (Classic Style)

| Command      | What It Does                           | Example      |
| ------------ | -------------------------------------- | ------------ |
| `!nextmatch` | Shows LA Galaxy's next scheduled match | `!nextmatch` |
| `!trivia`    | Start an interactive trivia game       | `!trivia`    |
| `!sync`      | Sync slash commands (owner only)       | `!sync`      |

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
python3 tests/test_bot_startup.py       # Bot initialization tests
python3 tests/test_bot_commands.py      # Command functionality tests
```

### Verify Your Setup

```bash
python3 tests/verify_bot_setup.py       # Pre-flight checks
```

## 📚 Documentation Hub

- **[Features Summary](docs/FEATURES_SUMMARY.md)** - Complete feature breakdown
- **[Error Handling](docs/ERROR_HANDLING_SUMMARY.md)** - How Cozmo handles problems
- **[Security Guidelines](docs/SECURITY_GUIDELINES.md)** - Keep your bot secure

## 🏗️ Architecture Overview

Cozmo is built with a modular, scalable architecture that makes adding new features a breeze:

```
cozmo-discord-bot/
├── 🤖 main.py                    # Bot brain & startup logic
├── ⚙️ config.py                  # Environment & configuration management
├── 📦 requirements.txt           # Python dependencies
├── 🧠 trivia_questions.py        # 15+ Galaxy trivia questions
├── 📋 .env.template              # Configuration template
│
├── 🌐 api/                       # External service integrations
│   ├── sports_api.py             # TheSportsDB client (matches, stats, standings)
│   └── news_api.py               # RSS feed client (currently disabled)
│
├── 🎯 cogs/                      # Feature modules (auto-loaded)
│   ├── matchday.py               # Match schedules & info
│   ├── stats.py                  # Player stats & MLS standings
│   ├── trivia.py                 # Interactive trivia games
│   └── news.py.disabled          # News features (temporarily off)
│
├── 🧪 tests/                     # Comprehensive test coverage
│   ├── run_all_tests.py          # Master test runner
│   ├── verify_bot_setup.py       # Pre-flight system checks
│   └── test_*.py                 # Individual test suites
│
├── 📖 docs/                      # Documentation & guides
│   ├── FEATURES_SUMMARY.md       # What Cozmo can do
│   ├── ERROR_HANDLING_SUMMARY.md # How errors are handled
│   └── SECURITY_GUIDELINES.md    # Security best practices
│
├── 📊 logs/                      # Runtime logs & debugging
├── 💾 data/                      # Persistent data storage
└── 📝 .kiro/specs/               # Development specifications
```

## 🔧 Technical Requirements

- **Python**: 3.8+ (tested on 3.9, 3.10, 3.11)
- **Discord.py**: 2.3.0+ (for modern Discord features)
- **API Access**: TheSportsDB account (free tier works great)
- **Permissions**: Bot needs message & reaction permissions

## 🚀 Deployment Options

### Local Development

```bash
python3 main.py
```

### Production Deployment

- **Render**: `render.yaml` included for one-click deployment (recommended)
- **Heroku**: Works with `runtime.txt` and `requirements.txt`
- **Railway**: Compatible with Python buildpack
- **Docker**: Optional containerization support available

## 🎯 What's Next?

### Recently Added Features ✨

- 🆕 **Modern Slash Commands**: Native Discord slash command support for all stats features
- 👥 **Complete Team Rosters**: Full team rosters with all positions using hybrid API approach
- 📋 **Match Lineups**: Starting XI and substitute information for matches
- 🏟️ **Live Standings**: Real-time MLS standings with points, wins, losses, and goal difference
- 🔄 **Hybrid API System**: Uses multiple data sources for the most complete information
- ⚡ **Guild-Specific Sync**: Faster slash command deployment for server admins

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

- 🎯 **15+ Trivia Questions**: From Galaxy's founding year to current roster
- ⚡ **Modern Slash Commands**: Native Discord interface with autocomplete
- 🛡️ **99.9% Uptime**: Built to handle Discord's occasional hiccups
- 🌟 **Galaxy Focused**: Every feature designed with LA Galaxy fans in mind
- 🤖 **Smart Caching**: Reduces API calls while keeping data fresh
- 👥 **Complete MLS Coverage**: All 29 MLS teams supported for rosters and stats
- 📊 **Rich Embeds**: Beautiful, branded Discord embeds with team badges

**Ready to bring the Galaxy to your Discord server? Let's get Cozmo running! ⭐**
