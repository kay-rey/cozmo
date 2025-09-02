# Cozmo Discord Bot Documentation

This directory contains comprehensive documentation for the Cozmo Discord Bot.

## Available Documentation

### Setup and Configuration

- **[Setup Guide](SETUP_GUIDE.md)** - Complete installation and configuration instructions
  - Prerequisites and dependencies
  - Discord bot creation and configuration
  - API key setup (TheSportsDB)
  - Environment configuration
  - Bot permissions and server setup
  - Troubleshooting guide

### Technical Documentation

- **[Error Handling Summary](ERROR_HANDLING_SUMMARY.md)** - Detailed error handling implementation
  - Error handling strategies
  - API error management
  - Discord command error handling
  - Logging and debugging information

## Quick Links

### For Users

- [Main README](../README.md) - Project overview and quick start
- [Setup Guide](SETUP_GUIDE.md) - Detailed setup instructions

### For Developers

- [Error Handling](ERROR_HANDLING_SUMMARY.md) - Error handling implementation
- [Tests Directory](../tests/) - Complete test suite
- [Specs Directory](../.kiro/specs/) - Development specifications

## Project Structure

The bot follows a modular architecture:

```
cozmo-discord-bot/
├── main.py                 # Bot entry point
├── config.py              # Configuration management
├── api/                   # External API integrations
├── cogs/                  # Discord bot features
├── tests/                 # Test suite
├── docs/                  # Documentation (this directory)
└── data/                  # Runtime data storage
```

## Support

If you need help:

1. Check the [Setup Guide](SETUP_GUIDE.md) for common issues
2. Review the [Error Handling Summary](ERROR_HANDLING_SUMMARY.md) for technical details
3. Run the verification script: `python3 tests/verify_bot_setup.py`
4. Check the logs in the `logs/` directory (created when bot runs)
