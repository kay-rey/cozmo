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
import pytz

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


async def get_next_match() -> Optional[dict]:
    """
    Fetch the next LA Galaxy match information.

    Returns:
        Dictionary with match details or None if no upcoming matches

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

        # Get additional match details
        event_id = next_match.get("idEvent", "")
        season = next_match.get("strSeason", "")
        round_info = next_match.get("intRound", "")

        # Get team badges/logos if available
        home_badge = next_match.get("strHomeTeamBadge", "")
        away_badge = next_match.get("strAwayTeamBadge", "")

        # Format the date and time with Pacific timezone conversion
        formatted_date = "TBD"
        formatted_time = "TBD"
        pacific_datetime = None

        # Convert both date and time to Pacific timezone
        if date_str and date_str != "TBD" and time_str and time_str != "TBD":
            try:
                # Parse date format YYYY-MM-DD and time format HH:MM:SS
                match_date = datetime.strptime(date_str, "%Y-%m-%d")
                time_parts = time_str.split(":")

                if len(time_parts) >= 2:
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])

                    # Create UTC datetime object
                    utc = pytz.UTC
                    pacific = pytz.timezone("US/Pacific")

                    # Combine date and time, assuming UTC
                    match_datetime = utc.localize(
                        datetime.combine(
                            match_date.date(),
                            datetime.min.time().replace(hour=hours, minute=minutes),
                        )
                    )

                    # Convert to Pacific time
                    pacific_datetime = match_datetime.astimezone(pacific)

                    # Format both date and time in Pacific timezone
                    formatted_date = pacific_datetime.strftime("%A, %B %d, %Y")
                    formatted_time = pacific_datetime.strftime("%I:%M %p PT")

            except (ValueError, IndexError):
                # Fallback to original formatting if conversion fails
                if date_str and date_str != "TBD":
                    try:
                        match_date = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_date = match_date.strftime("%A, %B %d, %Y")
                    except ValueError:
                        formatted_date = date_str
                formatted_time = time_str if time_str else "TBD"
        else:
            # Handle cases where date or time is missing
            if date_str and date_str != "TBD":
                try:
                    match_date = datetime.strptime(date_str, "%Y-%m-%d")
                    formatted_date = match_date.strftime("%A, %B %d, %Y")
                except ValueError:
                    formatted_date = date_str

            if time_str and time_str != "TBD":
                formatted_time = time_str

        # Determine if LA Galaxy is home or away
        is_home = home_team.lower() == "la galaxy" or "galaxy" in home_team.lower()
        opponent = away_team if is_home else home_team
        match_type = "vs" if is_home else "@"

        # Get the appropriate team badge
        galaxy_badge = home_badge if is_home else away_badge
        opponent_badge = away_badge if is_home else home_badge

        # Return structured match data
        match_data = {
            "home_team": home_team,
            "away_team": away_team,
            "opponent": opponent,
            "is_home": is_home,
            "match_type": match_type,
            "date": formatted_date,
            "time": formatted_time,
            "venue": venue,
            "competition": competition,
            "season": season,
            "round": round_info,
            "event_id": event_id,
            "galaxy_badge": galaxy_badge,
            "opponent_badge": opponent_badge,
            "raw_date": date_str,
            "raw_time": time_str,
        }

        logger.info(
            f"Successfully fetched next match: LA Galaxy {match_type} {opponent}"
        )
        return match_data

    except SportsAPIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching next match: {e}")
        raise SportsAPIError(f"Failed to process match data: {e}")


async def get_standings() -> dict:
    """
    Provide MLS conference information since live standings aren't reliably available.

    Returns:
        Dictionary with MLS conference information for creating Discord embeds
    """
    try:
        current_year = datetime.now().year

        # Define current MLS conferences (2025 season)
        western_conference = [
            "Austin FC",
            "Colorado Rapids",
            "FC Dallas",
            "Houston Dynamo FC",
            "LA Galaxy",
            "Los Angeles FC",
            "Minnesota United FC",
            "Portland Timbers",
            "Real Salt Lake",
            "San Jose Earthquakes",
            "Seattle Sounders FC",
            "Sporting Kansas City",
            "Vancouver Whitecaps FC",
            "St. Louis City SC",
        ]

        eastern_conference = [
            "Atlanta United FC",
            "CF Montréal",
            "Charlotte FC",
            "Chicago Fire FC",
            "Columbus Crew",
            "D.C. United",
            "FC Cincinnati",
            "Inter Miami CF",
            "Nashville SC",
            "New England Revolution",
            "New York City FC",
            "New York Red Bulls",
            "Orlando City SC",
            "Philadelphia Union",
            "Toronto FC",
        ]

        # Return conference information
        return {
            "has_standings": False,
            "western_conference": [{"name": team} for team in western_conference],
            "eastern_conference": [{"name": team} for team in eastern_conference],
            "season": current_year,
            "total_teams": len(western_conference) + len(eastern_conference),
            "note": "Live standings data not available. Showing current MLS teams by conference.",
        }

    except Exception as e:
        logger.error(f"Unexpected error in get_standings: {e}")
        raise SportsAPIError(f"Failed to get MLS conference information: {e}")


async def _try_get_standings_for_year(year: int) -> list:
    """Try to get standings data for a specific year."""
    try:
        table_data = await sports_client._make_request(
            f"lookuptable.php?l={sports_client.mls_league_id}&s={year}"
        )
        return table_data.get("table", [])
    except Exception as e:
        logger.warning(f"Failed to get standings for {year}: {e}")
        return []


async def _process_standings_table(table_entries: list, year: int = None) -> dict:
    """Process actual standings table data."""
    # Define MLS conferences
    western_conference = {
        "Austin FC",
        "Colorado Rapids",
        "FC Dallas",
        "Houston Dynamo",
        "LA Galaxy",
        "Los Angeles FC",
        "Minnesota United",
        "Portland Timbers",
        "Real Salt Lake",
        "San Jose Earthquakes",
        "Seattle Sounders FC",
        "Sporting Kansas City",
        "Vancouver Whitecaps",
        "St. Louis City SC",
        "San Diego FC",
    }

    eastern_conference = {
        "Atlanta United",
        "CF Montréal",
        "Charlotte FC",
        "Chicago Fire",
        "Columbus Crew",
        "DC United",
        "FC Cincinnati",
        "Inter Miami",
        "Nashville SC",
        "New England Revolution",
        "New York City FC",
        "New York Red Bulls",
        "Orlando City",
        "Philadelphia Union",
        "Toronto FC",
    }

    west_standings = []
    east_standings = []

    for entry in table_entries:
        team_name = entry.get("strTeam", "")
        normalized_team = team_name.replace("L.A. Galaxy", "LA Galaxy")

        # Create team record
        team_record = {
            "name": team_name,
            "played": entry.get("intPlayed", "0"),
            "wins": entry.get("intWin", "0"),
            "draws": entry.get("intDraw", "0"),
            "losses": entry.get("intLoss", "0"),
            "goals_for": entry.get("intGoalsFor", "0"),
            "goals_against": entry.get("intGoalsAgainst", "0"),
            "goal_difference": entry.get("intGoalDifference", "0"),
            "points": entry.get("intPoints", "0"),
            "position": entry.get("intRank", "0"),
        }

        # Assign to conference
        if normalized_team in western_conference:
            west_standings.append(team_record)
        elif normalized_team in eastern_conference:
            east_standings.append(team_record)

    # Sort by points (descending), then by goal difference
    west_standings.sort(
        key=lambda x: (int(x["points"]), int(x["goal_difference"])), reverse=True
    )
    east_standings.sort(
        key=lambda x: (int(x["points"]), int(x["goal_difference"])), reverse=True
    )

    return {
        "has_standings": True,
        "western_conference": west_standings,
        "eastern_conference": east_standings,
        "season": year or datetime.now().year,
    }


async def _get_team_list_fallback(current_year: int) -> dict:
    """Fallback to team list when standings aren't available."""
    # Get current season events to find all MLS teams
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

    # Define MLS conferences
    western_conference = {
        "Austin FC",
        "Colorado Rapids",
        "FC Dallas",
        "Houston Dynamo",
        "LA Galaxy",
        "Los Angeles FC",
        "Minnesota United",
        "Portland Timbers",
        "Real Salt Lake",
        "San Jose Earthquakes",
        "Seattle Sounders FC",
        "Sporting Kansas City",
        "Vancouver Whitecaps",
        "St. Louis City SC",
        "San Diego FC",
    }

    eastern_conference = {
        "Atlanta United",
        "CF Montréal",
        "Charlotte FC",
        "Chicago Fire",
        "Columbus Crew",
        "DC United",
        "FC Cincinnati",
        "Inter Miami",
        "Nashville SC",
        "New England Revolution",
        "New York City FC",
        "New York Red Bulls",
        "Orlando City",
        "Philadelphia Union",
        "Toronto FC",
    }

    # Categorize teams by conference
    west_teams = []
    east_teams = []

    for team in sorted(teams):
        normalized_team = team.replace("L.A. Galaxy", "LA Galaxy")
        if normalized_team in western_conference:
            west_teams.append({"name": team})
        elif normalized_team in eastern_conference:
            east_teams.append({"name": team})

    return {
        "has_standings": False,
        "western_conference": west_teams,
        "eastern_conference": east_teams,
        "season": current_year,
        "total_teams": len(teams),
    }


async def get_player_stats(player_name: str) -> dict:
    """
    Search for player statistics by name.

    Args:
        player_name: Name of the player to search for

    Returns:
        Dictionary with player data for creating Discord embeds

    Raises:
        SportsAPIError: If API request fails
    """
    try:
        if not player_name or not player_name.strip():
            return {
                "error": True,
                "message": "Please provide a player name to search for.",
            }

        # Search for player
        data = await sports_client._make_request(
            f"searchplayers.php?p={player_name.strip()}"
        )

        players = data.get("player")
        if not players:
            logger.info(f"No player found with name: {player_name}")
            return {
                "error": True,
                "message": f"Player '{player_name}' not found. Please check the spelling and try again.",
            }

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
        description = selected_player.get("strDescriptionEN", "")

        # Extract images
        cutout_image = selected_player.get("strCutout", "")
        thumb_image = selected_player.get("strThumb", "")

        # Extract statistics
        goals = selected_player.get("intSoccerGoals") or selected_player.get(
            "strGoals", ""
        )
        assists = selected_player.get("intSoccerAssists") or selected_player.get(
            "strAssists", ""
        )

        # Extract birth information
        birth_date = selected_player.get("dateBorn", "")
        birth_location = selected_player.get("strBirthLocation", "")

        # Format birth date
        formatted_birth_date = ""
        if birth_date:
            try:
                parsed_date = datetime.strptime(birth_date, "%Y-%m-%d")
                formatted_birth_date = parsed_date.strftime("%B %d, %Y")
            except ValueError:
                formatted_birth_date = birth_date

        # Calculate age if birth date available
        age = ""
        if birth_date:
            try:
                birth_dt = datetime.strptime(birth_date, "%Y-%m-%d")
                today = datetime.now()
                age_years = (
                    today.year
                    - birth_dt.year
                    - ((today.month, today.day) < (birth_dt.month, birth_dt.day))
                )
                age = f"{age_years} years old"
            except ValueError:
                pass

        # Truncate description if too long
        if description and len(description) > 400:
            description = description[:397] + "..."

        # Determine if this is a Galaxy player
        is_galaxy_player = galaxy_player is not None

        # Return structured data
        player_data = {
            "error": False,
            "name": name,
            "position": position,
            "team": team,
            "nationality": nationality,
            "description": description or "No description available",
            "goals": goals or "N/A",
            "assists": assists or "N/A",
            "birth_date": formatted_birth_date,
            "birth_location": birth_location,
            "age": age,
            "cutout_image": cutout_image,
            "thumb_image": thumb_image,
            "is_galaxy_player": is_galaxy_player,
            "player_id": selected_player.get("idPlayer", ""),
            "status": selected_player.get("strStatus", "Unknown"),
        }

        logger.info(f"Successfully fetched player data for: {name}")
        return player_data

    except SportsAPIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching player stats: {e}")
        raise SportsAPIError(f"Failed to process player data: {e}")
