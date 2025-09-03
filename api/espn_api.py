"""
ESPN API integration for MLS data.
Provides better roster and standings data to complement TheSportsDB.
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ESPNAPIError(Exception):
    """Custom exception for ESPN API related errors."""

    pass


class ESPNAPIClient:
    """Client for ESPN's unofficial API with better MLS coverage."""

    def __init__(self):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1"
        self.session: Optional[aiohttp.ClientSession] = None

        # MLS team mapping for better searches
        self.team_mapping = {
            "la galaxy": "la-galaxy",
            "lafc": "los-angeles-fc",
            "los angeles fc": "los-angeles-fc",
            "inter miami": "inter-miami-cf",
            "inter miami cf": "inter-miami-cf",
            "atlanta united": "atlanta-united-fc",
            "atlanta united fc": "atlanta-united-fc",
            "new york city fc": "new-york-city-fc",
            "nycfc": "new-york-city-fc",
            "new york red bulls": "new-york-red-bulls",
            "seattle sounders": "seattle-sounders-fc",
            "seattle sounders fc": "seattle-sounders-fc",
            "portland timbers": "portland-timbers",
            "sporting kansas city": "sporting-kansas-city",
            "real salt lake": "real-salt-lake",
            "colorado rapids": "colorado-rapids",
            "minnesota united": "minnesota-united-fc",
            "minnesota united fc": "minnesota-united-fc",
            "houston dynamo": "houston-dynamo-fc",
            "houston dynamo fc": "houston-dynamo-fc",
            "fc dallas": "fc-dallas",
            "austin fc": "austin-fc",
            "san jose earthquakes": "san-jose-earthquakes",
            "vancouver whitecaps": "vancouver-whitecaps-fc",
            "vancouver whitecaps fc": "vancouver-whitecaps-fc",
            "columbus crew": "columbus-crew",
            "chicago fire": "chicago-fire-fc",
            "chicago fire fc": "chicago-fire-fc",
            "dc united": "dc-united",
            "cf montreal": "cf-montreal",
            "toronto fc": "toronto-fc",
            "new england revolution": "new-england-revolution",
            "philadelphia union": "philadelphia-union",
            "orlando city": "orlando-city-sc",
            "orlando city sc": "orlando-city-sc",
            "nashville sc": "nashville-sc",
            "charlotte fc": "charlotte-fc",
            "fc cincinnati": "fc-cincinnati",
            "st louis city sc": "st-louis-city-sc",
            "st. louis city sc": "st-louis-city-sc",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
                logger.info("ESPN API client session closed")
            except Exception as e:
                logger.error(f"Error closing ESPN API session: {e}")

    async def _make_request(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to ESPN API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            ESPNAPIError: If request fails
        """
        if params is None:
            params = {}

        url = f"{self.base_url}/{endpoint}"
        session = await self._get_session()

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"ESPN API request successful: {endpoint}")
                    return data
                else:
                    logger.error(
                        f"ESPN API request failed with status {response.status}: {endpoint}"
                    )
                    raise ESPNAPIError(f"ESPN API returned status {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"ESPN API request failed: {e}")
            raise ESPNAPIError(f"Failed to fetch data from ESPN API: {e}")

    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize team name for ESPN API lookup."""
        normalized = team_name.lower().strip()
        return self.team_mapping.get(normalized, normalized.replace(" ", "-"))

    async def get_mls_standings(self) -> Dict[str, Any]:
        """
        Get current MLS standings from ESPN.

        Returns:
            Dictionary with standings data
        """
        try:
            data = await self._make_request("standings")

            if not data.get("children"):
                logger.warning("No standings data found in ESPN response")
                return {"error": True, "message": "No standings data available"}

            western_teams = []
            eastern_teams = []

            # ESPN organizes by conferences
            for conference in data["children"]:
                conf_name = conference.get("name", "").lower()
                standings = conference.get("standings", {}).get("entries", [])

                for entry in standings:
                    team_data = entry.get("team", {})
                    stats = entry.get("stats", [])

                    # Extract team info
                    team_info = {
                        "name": team_data.get("displayName", "Unknown"),
                        "abbreviation": team_data.get("abbreviation", ""),
                        "logo": team_data.get("logo", ""),
                        "position": entry.get("position", 0),
                    }

                    # Extract stats (points, wins, losses, etc.)
                    for stat in stats:
                        stat_name = stat.get("name", "").lower()
                        if stat_name == "points":
                            team_info["points"] = stat.get("value", 0)
                        elif stat_name == "wins":
                            team_info["wins"] = stat.get("value", 0)
                        elif stat_name == "losses":
                            team_info["losses"] = stat.get("value", 0)
                        elif stat_name == "ties":
                            team_info["draws"] = stat.get("value", 0)
                        elif stat_name == "gamesplayed":
                            team_info["played"] = stat.get("value", 0)
                        elif stat_name == "goaldifferential":
                            team_info["goal_difference"] = stat.get("value", 0)

                    # Assign to conference
                    if "west" in conf_name:
                        western_teams.append(team_info)
                    elif "east" in conf_name:
                        eastern_teams.append(team_info)

            return {
                "error": False,
                "has_standings": True,
                "western_conference": western_teams,
                "eastern_conference": eastern_teams,
                "season": datetime.now().year,
                "source": "ESPN",
            }

        except Exception as e:
            logger.error(f"Error fetching ESPN standings: {e}")
            raise ESPNAPIError(f"Failed to get standings: {e}")

    async def get_team_roster(self, team_name: str) -> Dict[str, Any]:
        """
        Get team roster from ESPN.

        Args:
            team_name: Name of the team

        Returns:
            Dictionary with roster data
        """
        try:
            # First get teams list to find the team ID
            teams_data = await self._make_request("teams")

            target_team = None
            normalized_name = self._normalize_team_name(team_name)

            # Find the team
            for team in (
                teams_data.get("sports", [{}])[0]
                .get("leagues", [{}])[0]
                .get("teams", [])
            ):
                team_info = team.get("team", {})
                if (
                    normalized_name in team_info.get("slug", "").lower()
                    or normalized_name in team_info.get("displayName", "").lower()
                    or team_name.lower() in team_info.get("displayName", "").lower()
                ):
                    target_team = team_info
                    break

            if not target_team:
                return {
                    "error": True,
                    "message": f"Team '{team_name}' not found in ESPN data",
                }

            team_id = target_team.get("id")
            if not team_id:
                return {"error": True, "message": "Could not find team ID"}

            # Get roster data
            roster_data = await self._make_request(f"teams/{team_id}/roster")

            athletes = roster_data.get("athletes", [])
            if not athletes:
                return {"error": True, "message": "No roster data available"}

            # Process roster data
            players = []
            positions = {}

            for athlete_group in athletes:
                position_name = athlete_group.get("position", {}).get(
                    "displayName", "Unknown"
                )
                group_athletes = athlete_group.get("items", [])

                position_players = []
                for athlete in group_athletes:
                    player_info = {
                        "name": athlete.get("displayName", "Unknown"),
                        "position": position_name,
                        "jersey": athlete.get("jersey", ""),
                        "age": athlete.get("age", ""),
                        "height": athlete.get("displayHeight", ""),
                        "weight": athlete.get("displayWeight", ""),
                        "nationality": "Unknown",  # ESPN doesn't always provide this
                        "headshot": athlete.get("headshot", {}).get("href", ""),
                    }
                    players.append(player_info)
                    position_players.append(player_info)

                if position_players:
                    positions[position_name] = position_players

            return {
                "error": False,
                "team_name": target_team.get("displayName", team_name),
                "team_logo": target_team.get("logo", ""),
                "team_color": target_team.get("color", ""),
                "players": players,
                "positions": positions,
                "total_players": len(players),
                "source": "ESPN",
            }

        except Exception as e:
            logger.error(f"Error fetching ESPN roster: {e}")
            raise ESPNAPIError(f"Failed to get roster: {e}")


# Global ESPN client instance
espn_client = ESPNAPIClient()
