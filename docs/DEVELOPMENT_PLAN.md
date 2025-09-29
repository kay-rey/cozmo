# Cozmo Discord Bot - Development Plan

## 🎯 Project Overview

- **Bot Name**: Cozmo
- **Purpose**: LA Galaxy fan bot providing game schedules, roster info, and player statistics
- **Platform**: Discord with slash commands
- **Deployment**: Docker container on Raspberry Pi 2
- **Language**: Python (optimal for Pi 2's limited resources)
- **Created**: September 2025

---

## 📋 Phase 1: Core Features & Commands

### Primary Slash Commands

1. **`/nextgame`** - Shows upcoming LA Galaxy match

   - Date, time, opponent, venue
   - Countdown timer

2. **`/roster`** - Displays current team roster

   - Player names, positions, jersey numbers
   - Optional: stats, age, nationality
   - Filtering options (by position, etc.)

3. **`/player [name]`** - Detailed player information
   - Basic info (position, number, age, nationality)
   - Current season stats
   - Career highlights
   - Recent performance

### Secondary Commands (Future phases)

4. **`/lastgame`** - Previous match results
5. **`/standings`** - Current MLS standings
6. **`/news`** - Latest LA Galaxy news
7. **`/schedule`** - Full season schedule
8. **`/stats`** - Team statistics

---

## 🏗️ Phase 2: Technical Architecture

### Project Structure

```
cozmo/
├── main.py                 # Bot entry point
├── config.py              # Configuration management
├── requirements.txt        # Dependencies
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Local development
├── .env.example          # Environment variables template
├── cogs/                  # Discord command modules
│   ├── __init__.py
│   ├── games.py          # Game-related commands
│   ├── roster.py         # Roster commands
│   ├── players.py        # Player info commands
│   └── admin.py          # Admin commands
├── data/                  # Data storage
│   ├── players.json      # Player database
│   ├── schedule.json     # Game schedule
│   └── team_info.json    # Team information
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── api_client.py     # External API interactions
│   ├── data_parser.py    # Data parsing utilities
│   └── embeds.py         # Discord embed templates
├── services/              # External services
│   ├── __init__.py
│   ├── mls_api.py        # MLS API integration
│   └── web_scraper.py    # Web scraping fallback
└── tests/                 # Test suite
    ├── __init__.py
    ├── test_commands.py
    └── test_utils.py
```

### Technology Stack

- **Core**: Python 3.9+ (Pi 2 compatible)
- **Discord**: discord.py 2.3+
- **HTTP Client**: aiohttp
- **Data Storage**: JSON files (lightweight for Pi 2)
- **Caching**: Built-in memory cache
- **Container**: Docker with Alpine Linux base

---

## 🔌 Phase 3: Data Sources & APIs

### Primary Data Sources

1. **MLS API** (if available)

   - Official league data
   - Real-time updates
   - Most reliable source

2. **LA Galaxy Official Website**

   - Web scraping for roster/schedule
   - Fallback when API unavailable
   - Player photos and bios

3. **Sports Reference APIs**
   - ESPN, The Athletic, etc.
   - Player statistics
   - Historical data

### Data Management Strategy

- **Caching**: Store data locally to reduce API calls
- **Refresh Schedule**: Update data every 6 hours
- **Fallback Chain**: API → Web Scraping → Cached Data
- **Error Handling**: Graceful degradation when sources fail

---

## 🐳 Phase 4: Docker & Raspberry Pi 2 Optimization

### Docker Configuration

```dockerfile
# Multi-stage build for size optimization
FROM python:3.9-alpine AS builder
# Build dependencies

FROM python:3.9-alpine AS runtime
# Minimal runtime environment
# ~50MB final image size
```

### Pi 2 Optimizations

- **Memory**: Target <512MB RAM usage
- **CPU**: Async operations, avoid blocking
- **Storage**: Minimal disk footprint
- **Network**: Efficient API usage, connection pooling
- **Startup**: Fast boot time (<30 seconds)

### Resource Management

- **Memory**: Garbage collection optimization
- **CPU**: Background tasks during low activity
- **Network**: Rate limiting and retry logic
- **Storage**: Log rotation and cleanup

---

## 🔒 Phase 5: Security & Configuration

### Environment Variables

```bash
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
MLS_API_KEY=optional_api_key
LOG_LEVEL=INFO
CACHE_TTL=21600
```

### Security Measures

- **Token Security**: Environment variables only
- **Permissions**: Minimal required Discord permissions
- **Input Validation**: Sanitize all user inputs
- **Rate Limiting**: Respect Discord and API limits
- **Error Handling**: No sensitive data in error messages

---

## 🧪 Phase 6: Testing Strategy

### Test Categories

1. **Unit Tests**: Individual functions and methods
2. **Integration Tests**: Command interactions
3. **API Tests**: External service integrations
4. **Performance Tests**: Pi 2 resource usage
5. **End-to-End Tests**: Complete user workflows

### Testing Tools

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking external services
- **pytest-cov**: Coverage reporting

---

## 📊 Phase 7: Monitoring & Maintenance

### Logging Strategy

- **Structured Logging**: JSON format for easy parsing
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Log Rotation**: Prevent disk space issues
- **Health Checks**: Bot status monitoring

### Performance Monitoring

- **Memory Usage**: Track RAM consumption
- **Response Times**: Command execution speed
- **API Calls**: Monitor external service usage
- **Error Rates**: Track and alert on failures

---

## 🚀 Phase 8: Deployment Plan

### Development Workflow

1. **Local Development**: Test on development machine
2. **Docker Testing**: Test container locally
3. **Pi 2 Testing**: Deploy to Pi 2 for testing
4. **Production**: Deploy with monitoring

### Deployment Steps

1. Build Docker image on Pi 2
2. Configure environment variables
3. Set up auto-restart on failure
4. Monitor initial deployment
5. Set up log collection

---

## 📈 Phase 9: Future Enhancements

### Advanced Features

- **Interactive Menus**: Button-based navigation
- **Notifications**: Game reminders and updates
- **Statistics**: Advanced analytics and trends
- **Integration**: Other MLS teams, fantasy leagues
- **Voice Commands**: Audio interaction support

### Scalability Considerations

- **Multi-Server Support**: Support multiple Discord servers
- **Database Migration**: Move from JSON to SQLite/PostgreSQL
- **API Rate Limiting**: Handle increased usage
- **Caching Strategy**: Redis for distributed caching

---

## ⏱️ Development Timeline

### Week 1-2: Foundation

- [ ] Project setup and basic bot structure
- [ ] Core slash command framework
- [ ] Basic data models

### Week 3-4: Core Features

- [ ] Implement `/nextgame`, `/roster`, `/player` commands
- [ ] Data source integration
- [ ] Basic error handling

### Week 5-6: Optimization

- [ ] Docker containerization
- [ ] Pi 2 optimization
- [ ] Performance testing

### Week 7-8: Polish & Deploy

- [ ] Testing and bug fixes
- [ ] Documentation
- [ ] Production deployment

---

## 🎯 Success Metrics

### Performance Targets

- **Response Time**: <2 seconds for most commands
- **Memory Usage**: <512MB on Pi 2
- **Uptime**: >99% availability
- **Error Rate**: <1% command failures

### User Experience Goals

- **Intuitive Commands**: Easy to discover and use
- **Rich Embeds**: Visually appealing information display
- **Fast Responses**: Quick command execution
- **Reliable Data**: Accurate and up-to-date information

---

## 📝 Development Notes

### Key Decisions Made

- **Python over Node.js**: Better for Pi 2 resource constraints
- **JSON over Database**: Simpler for initial implementation
- **Slash Commands**: Modern Discord interaction method
- **Modular Architecture**: Easy to maintain and extend

### Potential Challenges

- **API Rate Limits**: Need efficient caching strategy
- **Pi 2 Performance**: Memory and CPU optimization critical
- **Data Freshness**: Balancing real-time updates with performance
- **Error Handling**: Graceful degradation when services fail

### Next Steps

1. Set up development environment
2. Create basic bot structure
3. Implement first slash command
4. Test on local machine
5. Begin Docker containerization

---

_Last Updated: September 29, 2025_
_Status: Planning Phase_
