# Cozmo - LA Galaxy Discord Bot

A comprehensive Discord bot for LA Galaxy fans, providing match information, team statistics, latest news, and interactive trivia games.

## Features

🏆 **Match Information**

- Get next LA Galaxy match details with `!nextmatch`
- View date, time, opponent, and venue information

📊 **Team Statistics**

- View current MLS standings with `!standings`
- Search player statistics with `!playerstats [player_name]`

📰 **News Updates**

- Get latest news manually with `!news`
- Automatic news updates every 20 minutes
- Duplicate prevention to avoid spam

🎯 **Interactive Trivia**

- Play LA Galaxy trivia games with `!trivia`
- Multiple choice questions with reaction-based answers
- Covers team history and current roster

## Quick Start

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the bot:**

   ```bash
   cp .env.template .env
   # Edit .env with your Discord token, API keys, and channel ID
   ```

3. **Verify setup:**

   ```bash
   python3 tests/verify_bot_setup.py
   ```

4. **Start the bot:**
   ```bash
   python3 main.py
   ```

## Testing

Run the complete test suite:

```bash
python3 tests/run_all_tests.py
```

Individual test categories:

```bash
python3 tests/test_code_structure.py    # Code structure validation
python3 tests/test_bot_final.py         # Integration tests
python3 tests/test_bot_startup.py       # Startup sequence tests
python3 tests/test_bot_commands.py      # Command functionality tests
```

## Documentation

- **[Setup Guide](docs/SETUP_GUIDE.md)** - Detailed installation and configuration instructions
- **[Error Handling Summary](docs/ERROR_HANDLING_SUMMARY.md)** - Error handling implementation details

## Project Structure

```
cozmo-discord-bot/
├── main.py                    # Bot entry point
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── trivia_questions.py        # Trivia game data
├── .env.template              # Environment variables template
├── api/                       # External API integrations
│   ├── __init__.py
│   ├── sports_api.py          # TheSportsDB integration
│   └── news_api.py            # RSS feed integration
├── cogs/                      # Discord bot features (auto-loaded)
│   ├── __init__.py
│   ├── matchday.py            # Match information commands
│   ├── stats.py               # Statistics commands
│   ├── news.py                # News commands and automation
│   └── trivia.py              # Trivia game functionality
├── tests/                     # Comprehensive test suite
│   ├── README.md              # Test documentation
│   ├── run_all_tests.py       # Master test runner
│   ├── verify_bot_setup.py    # Setup verification
│   └── test_*.py              # Individual test files
├── docs/                      # Documentation
│   ├── index.md               # Documentation index
│   ├── SETUP_GUIDE.md         # Detailed setup instructions
│   └── ERROR_HANDLING_SUMMARY.md  # Error handling details
├── data/                      # Runtime data storage
└── .kiro/specs/               # Development specifications
```

## Commands

| Command               | Description                   |
| --------------------- | ----------------------------- |
| `!nextmatch`          | Show next LA Galaxy match     |
| `!standings`          | Display current MLS standings |
| `!playerstats [name]` | Get player statistics         |
| `!news`               | Get latest news article       |
| `!trivia`             | Start trivia game             |

## Requirements

- Python 3.8+
- Discord bot token
- TheSportsDB API key
- Discord server with appropriate permissions

## Contributing

This project follows a spec-driven development approach. See the `.kiro/specs/` directory for detailed requirements, design, and implementation plans.

## License

See [LICENSE](LICENSE) file for details.
