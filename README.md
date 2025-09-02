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
   python3 verify_bot_setup.py
   ```

4. **Start the bot:**
   ```bash
   python3 main.py
   ```

For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Architecture

Built with a modular architecture using Discord.py Cogs:

- **Main Bot** (`main.py`) - Entry point and bot lifecycle management
- **Configuration** (`config.py`) - Environment variable management
- **API Layer** (`api/`) - External service integrations
  - Sports API for match data and statistics
  - News API for RSS feed parsing
- **Cogs** (`cogs/`) - Feature modules
  - Matchday - Match information commands
  - Stats - Team and player statistics
  - News - News updates and automation
  - Trivia - Interactive trivia games

## Requirements

- Python 3.8+
- Discord bot token
- TheSportsDB API key
- Discord server with appropriate permissions

## Commands

| Command               | Description                   |
| --------------------- | ----------------------------- |
| `!nextmatch`          | Show next LA Galaxy match     |
| `!standings`          | Display current MLS standings |
| `!playerstats [name]` | Get player statistics         |
| `!news`               | Get latest news article       |
| `!trivia`             | Start trivia game             |

## Contributing

This project follows a spec-driven development approach. See the `.kiro/specs/` directory for detailed requirements, design, and implementation plans.

## License

See [LICENSE](LICENSE) file for details.
