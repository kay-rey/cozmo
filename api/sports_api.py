"""
Sports API integration layer for TheSportsDB API.
Handles LA Galaxy match data, standings, and player statistics.
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from config import config

logger = logging.getLogger(__name__)


class SportsAPIError(Exception):
    """Custom exception for Sports API related errors."""

    pass


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int = 30):
        self.calls_per_minute = calls_per_minute
        self.calls = []

    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = datetime.now()
        # Remove calls older than 1 minute
        self.calls = [
            call_time
            for call_time in self.calls
            if now - call_time < timedelta(minutes=1)
        ]

        if len(self.calls) >= self.calls_per_minute:
            # Wait until the oldest call is more than 1 minute old
            wait_time = 60 - (now - self.calls[0]).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)

        self.calls.append(now)


class SportsAPIClient:
    """Client for TheSportsDB API with rate limiting and error handling."""

    def __init__(self):
        self.base_url = "https://www.thesportsdb.com/api/v1/json"
        self.api_key = config.SPORTS_API_KEY
        self.rate_limiter = RateLimiter()
        self.session: Optional[aiohttp.ClientSession] = None

        # LA Galaxy team ID in TheSportsDB
        self.la_galaxy_team_id = "134153"
        # MLS league ID
        self.mls_league_id = "4346"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
                logger.info("Sports API client session closed")
            except Exception as e:
                logger.error(f"Error closing sports API session: {e}")

    async def _make_request(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to TheSportsDB API with rate limiting and retry logic.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            SportsAPIError: If request fails after retries
        """
        if params is None:
            params = {}

        url = f"{self.base_url}/{self.api_key}/{endpoint}"

        # Apply rate limiting
        await self.rate_limiter.wait_if_needed()

        session = await self._get_session()

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"API request successful: {endpoint}")
                        return data
                    elif response.status == 429:  # Rate limited
                        wait_time = 2**attempt
                        logger.warning(f"Rate limited, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            f"API request failed with status {response.status}: {endpoint}"
                        )
                        response.raise_for_status()

            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"API request failed after {max_retries} attempts: {e}"
                    )
                    raise SportsAPIError(f"Failed to fetch data from Sports API: {e}")

                wait_time = 2**attempt
                logger.warning(f"Request failed, retrying in {wait_time} seconds: {e}")
                await asyncio.sleep(wait_time)

        raise SportsAPIError("Maximum retry attempts exceeded")


# Global client instance
sports_client = SportsAPIClient()


async def get_next_match() -> Optional[str]:
    """
    Fetch the next LA Galaxy match information.

    Returns:
        Formatted string with match details or None if no upcoming matches

    Raises:
        SportsAPIError: If API request fails
    """
    try:
        # Fetch next events for LA Galaxy
        data = await sports_client._make_request(
            f"eventsnext.php?id={sports_client.la_galaxy_team_id}"
        )

        events = data.get("events")
        if not events:
            logger.info("No upcoming matches found for LA Galaxy")
            return None

        # Get the first (next) match
        next_match = events[0]

        # Extract match information
        date_str = next_match.get("dateEvent", "TBD")
        time_str = next_match.get("strTime", "TBD")
        home_team = next_match.get("strHomeTeam", "Unknown")
        away_team = next_match.get("strAwayTeam", "Unknown")
        venue = next_match.get("strVenue", "TBD")
        competition = next_match.get("strLeague", "MLS")

        # Format the date and time
        formatted_date = "TBD"
        if date_str and date_str != "TBD":
            try:
                # Parse date format YYYY-MM-DD
                match_date = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = match_date.strftime("%A, %B %d, %Y")
            except ValueError:
                formatted_date = date_str

        # Format time
        formatted_time = time_str if time_str and time_str != "TBD" else "TBD"

        # Determine if LA Galaxy is home or away
        is_home = home_team.lower() == "la galaxy"
        opponent = away_team if is_home else home_team
        match_type = "vs" if is_home else "@"

        # Format the response
        match_info = f"""🏆 **Next LA Galaxy Match**
        
**{competition}**
LA Galaxy {match_type} {opponent}

📅 **Date:** {formatted_date}
🕐 **Time:** {formatted_time}
🏟️ **Venue:** {venue}

Go Galaxy! ⭐"""

        logger.info(
            f"Successfully fetched next match: LA Galaxy {match_type} {opponent}"
        )
        return match_info

    except SportsAPIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching next match: {e}")
        raise SportsAPIError(f"Failed to process match data: {e}")


async def get_standings() -> str:
    """
    Fetch current MLS standings by getting all teams from recent events.

    Since the league table API doesn't return complete MLS data,
    we'll get team information from recent season events.

    Returns:
        Formatted string with MLS teams list

    Raises:
        SportsAPIError: If API request fails or data unavailable
    """
    try:
        # Get current season events to find all MLS teams
        current_year = datetime.now().year
        data = await sports_client._make_request(
            f"eventsseason.php?id={sports_client.mls_league_id}&s={current_year}"
        )

        events = data.get("events")
        if not events:
            # Try previous year if current year has no data
            data = await sports_client._make_request(
                f"eventsseason.php?id={sports_client.mls_league_id}&s={current_year - 1}"
            )
            events = data.get("events", [])

        if not events:
            logger.warning("No MLS season data available")
            raise SportsAPIError("MLS season data is currently unavailable")

        # Extract unique teams from events
        teams = set()
        for event in events:
            home_team = event.get("strHomeTeam", "")
            away_team = event.get("strAwayTeam", "")
            league = event.get("strLeague", "").lower()

            # Check if this is an MLS event
            if (
                "major league soccer" in league
                or "mls" in league
                or "american major league soccer" in league
            ):
                if home_team:
                    teams.add(home_team)
                if away_team:
                    teams.add(away_team)

        if not teams:
            logger.warning("No MLS teams found in events")
            raise SportsAPIError("Unable to find MLS teams data")

        # Sort teams alphabetically
        sorted_teams = sorted(teams)

        # Format as a clean list
        standings_text = f"🏆 **MLS Teams ({len(sorted_teams)} teams)**\n\n"

        # Split into two columns for better display
        mid_point = len(sorted_teams) // 2
        left_column = sorted_teams[:mid_point]
        right_column = sorted_teams[mid_point:]

        # Pad right column if needed
        while len(right_column) < len(left_column):
            right_column.append("")

        standings_text += "```\n"
        for i in range(len(left_column)):
            left_team = left_column[i]
            right_team = right_column[i] if i < len(right_column) else ""

            # Highlight LA Galaxy
            left_marker = "►" if "galaxy" in left_team.lower() else " "
            right_marker = "►" if right_team and "galaxy" in right_team.lower() else " "

            left_display = f"{left_marker}{left_team:<28}"
            right_display = f"{right_marker}{right_team}" if right_team else ""

            standings_text += f"{left_display} {right_display}\n"

        standings_text += "```\n\n"
        standings_text += "► = LA Galaxy\n"
        standings_text += f"📊 Total MLS Teams: {len(sorted_teams)}\n"
        standings_text += (
            "💡 *Use `!playerstats [player name]` to get individual player statistics*"
        )

        logger.info(f"Successfully fetched {len(sorted_teams)} MLS teams")
        return standings_text

    except SportsAPIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching MLS teams: {e}")
        raise SportsAPIError(f"Failed to process MLS teams data: {e}")


async def get_player_stats(player_name: str) -> str:
    """
    Search for player statistics by name.

    Args:
        player_name: Name of the player to search for

    Returns:
        Formatted string with player statistics

    Raises:
        SportsAPIError: If API request fails
    """
    try:
        if not player_name or not player_name.strip():
            return "❌ Please provide a player name to search for."

        # Search for player
        data = await sports_client._make_request(
            f"searchplayers.php?p={player_name.strip()}"
        )

        players = data.get("player")
        if not players:
            logger.info(f"No player found with name: {player_name}")
            return f"❌ Player '{player_name}' not found. Please check the spelling and try again."

        # Find LA Galaxy player or use first result
        galaxy_player = None
        for player in players:
            team = player.get("strTeam", "").lower()
            if "galaxy" in team or "la galaxy" in team:
                galaxy_player = player
                break

        # Use first player if no Galaxy player found
        selected_player = galaxy_player if galaxy_player else players[0]

        # Extract player information
        name = selected_player.get("strPlayer", "Unknown")
        position = selected_player.get("strPosition", "Unknown")
        team = selected_player.get("strTeam", "Unknown")
        nationality = selected_player.get("strNationality", "Unknown")
        description = selected_player.get(
            "strDescriptionEN", "No description available"
        )

        # Extract statistics (these may not always be available)
        goals = selected_player.get("intSoccerGoals") or selected_player.get(
            "strGoals", "N/A"
        )
        assists = selected_player.get("intSoccerAssists") or selected_player.get(
            "strAssists", "N/A"
        )

        # Format birth info if available
        birth_date = selected_player.get("dateBorn", "")
        birth_location = selected_player.get("strBirthLocation", "")

        birth_info = ""
        if birth_date or birth_location:
            birth_parts = []
            if birth_date:
                try:
                    # Parse and format birth date
                    parsed_date = datetime.strptime(birth_date, "%Y-%m-%d")
                    birth_parts.append(parsed_date.strftime("%B %d, %Y"))
                except ValueError:
                    birth_parts.append(birth_date)
            if birth_location:
                birth_parts.append(birth_location)
            birth_info = f"\n🎂 **Born:** {' in '.join(birth_parts)}"

        # Truncate description if too long
        if len(description) > 300:
            description = description[:297] + "..."

        # Format the response
        player_info = f"""⚽ **Player Statistics**

👤 **Name:** {name}
🏃 **Position:** {position}
🏟️ **Team:** {team}
🌍 **Nationality:** {nationality}{birth_info}

📊 **Season Stats:**
⚽ Goals: {goals}
🎯 Assists: {assists}

📝 **About:**
{description}"""

        # Add note if not a Galaxy player
        if not galaxy_player and players:
            player_info += "\n\n*Note: This player is not currently with LA Galaxy*"

        logger.info(f"Successfully fetched player stats for: {name}")
        return player_info

    except SportsAPIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching player stats: {e}")
        raise SportsAPIError(f"Failed to process player data: {e}")
