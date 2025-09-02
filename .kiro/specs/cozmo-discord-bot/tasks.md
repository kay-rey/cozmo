# Implementation Plan

- [x] 1. Set up project structure and configuration

  - Create directory structure for api/, cogs/, and data/ folders
  - Implement configuration management with environment variable loading
  - Create .env template file with required variables
  - _Requirements: 6.1, 6.2, 7.4_

- [x] 2. Implement core bot infrastructure

  - Create main bot class with proper Discord intents setup
  - Implement automatic Cog loading from cogs directory
  - Add startup message and on_ready event handler
  - _Requirements: 6.3, 7.3_

- [x] 3. Create Sports API integration layer
- [x] 3.1 Implement basic Sports API client

  - Create sports_api.py with HTTP client setup and error handling
  - Implement API key authentication and base URL configuration
  - Add rate limiting and retry logic for API calls
  - _Requirements: 7.4_

- [x] 3.2 Implement next match functionality

  - Create get_next_match() function to fetch LA Galaxy upcoming matches
  - Parse and format match data including date, time, opponent, and venue
  - Handle cases where no upcoming matches are found
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 3.3 Implement standings functionality

  - Create get_standings() function using MLS league ID 4346
  - Format standings data as readable table in Discord code block format
  - Handle API errors and unavailable data scenarios
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3.4 Implement player statistics functionality

  - Create get_player_stats() function with player name search
  - Parse and format player data including position, goals, assists, and description
  - Handle player not found scenarios with appropriate messaging
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Create News API integration layer

  - Implement news_api.py with RSS feed parsing using feedparser
  - Create get_latest_news() function to fetch from LA Galaxy RSS feed
  - Parse RSS data and extract title, link, and publication information
  - _Requirements: 4.1, 4.4_

- [x] 5. Implement Matchday Cog

  - Create MatchdayCog class with discord.py Cog structure
  - Implement !nextmatch command that calls Sports API and formats response
  - Add error handling for API failures and display appropriate user messages
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 6. Implement Stats Cog

  - Create StatsCog class with discord.py Cog structure
  - Implement !standings command that displays formatted MLS standings
  - Implement !playerstats command with player name argument parsing
  - Add input validation and error handling for both commands
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4_

- [ ] 7. Create trivia data and infrastructure
- [ ] 7.1 Create trivia questions data

  - Create trivia_questions.py with QUESTIONS list containing at least 10 LA Galaxy trivia questions
  - Structure each question with question text, 4 options, and correct answer index
  - Ensure questions cover various aspects of LA Galaxy history and current team
  - _Requirements: 5.1, 5.2_

- [ ] 7.2 Implement Trivia Cog core functionality

  - Create TriviaCog class with active games tracking dictionary
  - Implement !trivia command that checks for existing games and starts new ones
  - Add random question selection and Discord embed formatting
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 7.3 Implement trivia reaction handling

  - Add reaction emojis (🇦, 🇧, 🇨, 🇩) to trivia questions automatically
  - Implement on_reaction_add event listener for answer processing
  - Handle correct/incorrect answer logic and winner announcements
  - Clean up completed games from active_games tracking
  - _Requirements: 5.4, 5.5, 5.6, 5.7_

- [ ] 8. Implement News Cog functionality
- [ ] 8.1 Create news tracking infrastructure

  - Create last_article.txt file for duplicate prevention
  - Implement file read/write functions for URL tracking
  - Add error handling for file access operations
  - _Requirements: 4.2, 4.3_

- [ ] 8.2 Implement manual news command

  - Create NewsCog class with discord.py Cog structure
  - Implement !news command that fetches and displays latest article on demand
  - Format news output with title and link for Discord display
  - _Requirements: 4.4_

- [ ] 8.3 Implement automated news checking

  - Create background task using tasks.loop(minutes=20) decorator
  - Implement duplicate checking logic comparing with stored URL
  - Add automatic posting to designated news channel when new articles are found
  - Update last_article.txt with new URLs after successful posting
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 9. Add comprehensive error handling and logging

  - Implement try-catch blocks for all API calls and external operations
  - Add logging for bot startup, command usage, and error scenarios
  - Create user-friendly error messages for common failure scenarios
  - _Requirements: 2.3, 3.3, 1.2_

- [ ] 10. Create bot entry point and integration
  - Complete main.py with bot token loading and startup sequence
  - Integrate all Cogs into the main bot instance
  - Add proper bot shutdown handling and cleanup
  - Test complete bot functionality with all features integrated
  - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 8.1_
