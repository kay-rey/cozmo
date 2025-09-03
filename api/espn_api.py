"""
ESPN API integration for MLS data - Fixed version.
Provides better roster data to complement TheSportsDB.
"""

import aiohttp
from typing import Optional, Dict, Any
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

        # MLS team ID mapping (from ESPN API - verified working IDs)
        self.team_ids = {
            "la galaxy": "187",
            "los angeles galaxy": "187",
            "galaxy": "187",
            "inter miami": "20232",
            "inter miami cf": "20232",
            "miami": "20232",
            "atlanta united": "18418",
            "atlanta united fc": "18418",
            "atlanta": "18418",
            "new york city fc": "3",
            "nycfc": "3",
            "new york city": "3",
            "orlando city": "4",
            "orlando city sc": "4",
            "orlando": "4",
            "new york red bulls": "5",
            "red bulls": "5",
            "ny red bulls": "5",
            "toronto fc": "6",
            "toronto": "6",
            "chicago fire": "7",
            "chicago fire fc": "7",
            "chicago": "7",
            "new england revolution": "8",
            "new england": "8",
            "revolution": "8",
            "columbus crew": "9",
            "columbus": "9",
            "crew": "9",
            "dc united": "10",
            "d.c. united": "10",
            "washington": "10",
            "philadelphia union": "11",
            "philadelphia": "11",
            "union": "11",
            "cf montreal": "12",
            "montreal": "12",
            "sporting kansas city": "13",
            "sporting kc": "13",
            "kansas city": "13",
            "skc": "13",
            "real salt lake": "14",
            "rsl": "14",
            "salt lake": "14",
            "colorado rapids": "15",
            "colorado": "15",
            "rapids": "15",
            "fc dallas": "16",
            "dallas": "16",
            "houston dynamo": "17",
            "houston dynamo fc": "17",
            "houston": "17",
            "dynamo": "17",
            "san jose earthquakes": "18",
            "san jose": "18",
            "earthquakes": "18",
            "seattle sounders": "9726",
            "seattle sounders fc": "9726",
            "seattle": "9726",
            "sounders": "9726",
            "portland timbers": "20",
            "portland": "20",
            "timbers": "20",
            "vancouver whitecaps": "21",
            "vancouver whitecaps fc": "21",
            "vancouver": "21",
            "whitecaps": "21",
            "minnesota united": "22",
            "minnesota united fc": "22",
            "minnesota": "22",
            "mnufc": "22",
            "lafc": "18966",
            "los angeles fc": "18966",
            "fc cincinnati": "24",
            "cincinnati": "24",
            "fcc": "24",
            "nashville sc": "25",
            "nashville": "25",
            "austin fc": "26",
            "austin": "26",
            "charlotte fc": "27",
            "charlotte": "27",
            "st. louis city sc": "29",
            "st louis city": "29",
            "saint louis city": "29",
            "st. louis": "29",
            "stl city": "29",
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
        """Make HTTP request to ESPN API."""
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

    async def find_team_id(self, team_name: str) -> Optional[str]:
        """Find team ID by searching through teams."""
        try:
            # Check our known mappings first
            normalized_name = team_name.lower().strip()
            if normalized_name in self.team_ids:
                return self.team_ids[normalized_name]

            # Search through all teams
            teams_data = await self._make_request("teams")
            sports = teams_data.get("sports", [])
            if not sports:
                return None

            leagues = sports[0].get("leagues", [])
            if not leagues:
                return None

            teams = leagues[0].get("teams", [])

            for team_entry in teams:
                team_info = team_entry.get("team", {})
                team_display = team_info.get("displayName", "").lower()
                team_short = team_info.get("shortDisplayName", "").lower()

                if (
                    normalized_name in team_display
                    or team_name.lower() in team_display
                    or normalized_name in team_short
                ):
                    return team_info.get("id")

            return None

        except Exception as e:
            logger.error(f"Error finding team ID: {e}")
            return None

    async def get_team_roster(self, team_name: str) -> Dict[str, Any]:
        """Get team roster from ESPN."""
        try:
            # Find team ID
            team_id = await self.find_team_id(team_name)
            if not team_id:
                return {
                    "error": True,
                    "message": f"Team '{team_name}' not found in ESPN data",
                }

            # Get roster data
            try:
                roster_data = await self._make_request(f"teams/{team_id}/roster")
            except ESPNAPIError as e:
                if "404" in str(e):
                    return {
                        "error": True,
                        "message": "ESPN roster data not available for this team",
                    }
                raise

            athletes = roster_data.get("athletes", [])
            if not athletes:
                return {"error": True, "message": "No roster data available"}

            # Process roster data - each athlete is a direct object
            players = []
            positions = {}

            for athlete in athletes:
                position_info = athlete.get("position", {})
                position_name = position_info.get("displayName", "Unknown")

                # Extract nationality from citizenship or birthPlace
                nationality = "Unknown"
                if athlete.get("citizenship"):
                    nationality = athlete.get("citizenship", "Unknown")
                elif athlete.get("birthPlace", {}).get("country"):
                    nationality = athlete.get("birthPlace", {}).get(
                        "country", "Unknown"
                    )

                player_info = {
                    "name": athlete.get("displayName", "Unknown"),
                    "position": position_name,
                    "jersey": athlete.get("jersey", ""),
                    "age": athlete.get("age", ""),
                    "height": athlete.get("displayHeight", ""),
                    "weight": athlete.get("displayWeight", ""),
                    "nationality": nationality,
                    "headshot": athlete.get("headshot", {}).get("href", "")
                    if athlete.get("headshot")
                    else "",
                }
                players.append(player_info)

                # Group by position
                if position_name not in positions:
                    positions[position_name] = []
                positions[position_name].append(player_info)

            # Get team info
            team_info = roster_data.get("team", {})

            return {
                "error": False,
                "team_name": team_info.get("displayName", team_name),
                "team_logo": team_info.get("logos", [{}])[0].get("href", "")
                if team_info.get("logos")
                else "",
                "team_color": team_info.get("color", ""),
                "players": players,
                "positions": positions,
                "total_players": len(players),
                "source": "ESPN",
            }

        except ESPNAPIError:
            raise
        except Exception as e:
            logger.error(f"Error fetching ESPN roster: {e}")
            raise ESPNAPIError(f"Failed to get roster: {e}")

    async def get_mls_standings(self) -> Dict[str, Any]:
        """ESPN MLS standings are not available - return error."""
        return {
            "error": True,
            "message": "ESPN MLS standings not available",
            "source": "ESPN",
        }


# Global ESPN client instance
espn_client = ESPNAPIClient()
