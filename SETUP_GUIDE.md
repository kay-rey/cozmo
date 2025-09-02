# Cozmo Discord Bot Setup Guide

This guide will help you set up and run the Cozmo Discord Bot for LA Galaxy fans.

## Prerequisites

- Python 3.8 or higher
- A Discord account and server where you can add bots
- Internet connection for API access

## Step 1: Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Required packages:

- `discord.py>=2.3.0` - Discord bot framework
- `python-dotenv>=1.0.0` - Environment variable management
- `aiohttp>=3.8.0` - HTTP client for API calls
- `feedparser>=6.0.0` - RSS feed parsing

## Step 2: Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name (e.g., "Cozmo")
3. Go to the "Bot" section
4. Click "Add Bot"
5. Copy the bot token (you'll need this for the .env file)
6. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent (optional)

## Step 3: Get API Keys

### TheSportsDB API Key

1. Visit [TheSportsDB API](https://www.thesportsdb.com/api.php)
2. Sign up for a free account
3. Get your API key from the dashboard

### Discord Channel ID

1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on the channel where you want news updates
3. Click "Copy ID"

## Step 4: Configure Environment

1. Copy `.env.template` to `.env`:

   ```bash
   cp .env.template .env
   ```

2. Edit `.env` with your actual values:
   ```env
   DISCORD_TOKEN="your_discord_bot_token_here"
   SPORTS_API_KEY="your_thesportsdb_api_key_here"
   NEWS_CHANNEL_ID=your_news_channel_id_here
   ```

## Step 5: Invite Bot to Server

1. In Discord Developer Portal, go to OAuth2 > URL Generator
2. Select scopes: `bot`
3. Select bot permissions:
   - Send Messages
   - Use Slash Commands
   - Add Reactions
   - Read Message History
   - Embed Links
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

## Step 6: Verify Setup

Run the setup verification script:

```bash
python3 verify_bot_setup.py
```

This will check:

- ✅ All required files are present
- ✅ Dependencies are installed
- ✅ Configuration is properly set up

## Step 7: Start the Bot

Run the bot:

```bash
python3 main.py
```

You should see:

```
Cozmo is online and ready to cheer for the Galaxy!
```

## Available Commands

Once the bot is running, you can use these commands in your Discord server:

### Match Information

- `!nextmatch` - Get information about the next LA Galaxy match

### Statistics

- `!standings` - View current MLS standings
- `!playerstats [player_name]` - Get statistics for a specific player

### News

- `!news` - Get the latest LA Galaxy news article
- Automatic news updates every 20 minutes (posted to configured channel)

### Trivia

- `!trivia` - Start a LA Galaxy trivia game
- React with 🇦, 🇧, 🇨, or 🇩 to answer

## Troubleshooting

### Bot doesn't respond to commands

- Check that the bot has "Send Messages" permission in the channel
- Verify the bot is online (green status in Discord)
- Check the console for error messages

### API errors

- Verify your TheSportsDB API key is correct
- Check your internet connection
- API may be temporarily unavailable

### News not posting automatically

- Verify the NEWS_CHANNEL_ID is correct
- Check that the bot has permission to post in that channel
- News updates check every 20 minutes

### Permission errors

- Make sure the bot has the required permissions in your server
- Check that the bot role is high enough in the role hierarchy

## File Structure

```
cozmo-discord-bot/
├── main.py                 # Bot entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from template)
├── .env.template         # Environment template
├── trivia_questions.py   # Trivia game data
├── api/
│   ├── __init__.py
│   ├── sports_api.py     # TheSportsDB integration
│   └── news_api.py       # RSS feed integration
├── cogs/
│   ├── __init__.py
│   ├── matchday.py       # Match information commands
│   ├── stats.py          # Statistics commands
│   ├── news.py           # News commands and automation
│   └── trivia.py         # Trivia game functionality
├── data/                 # Data storage directory
└── logs/                 # Log files (created automatically)
```

## Support

If you encounter issues:

1. Check the logs in the `logs/` directory
2. Run `python3 verify_bot_setup.py` to check your setup
3. Ensure all dependencies are installed
4. Verify your .env configuration
5. Check Discord bot permissions

## Contributing

This bot is built with a modular architecture using Discord.py Cogs. Each feature is separated into its own cog for easy maintenance and extension.

To add new features:

1. Create a new cog in the `cogs/` directory
2. Follow the existing cog patterns
3. The bot will automatically load new cogs on startup
