#!/usr/bin/env python3
"""
Debug script to test team name matching in ESPN API
"""

import asyncio
from api.espn_api import espn_client


async def test_team_matching():
    """Test team name matching for various teams."""
    test_teams = [
        "Inter Miami",
        "inter miami",
        "Inter Miami CF",
        "LA Galaxy",
        "la galaxy",
        "LAFC",
        "Los Angeles FC",
    ]

    print("🔍 Testing ESPN API team name matching...")

    for team_name in test_teams:
        print(f"\n📝 Testing: '{team_name}'")

        try:
            # Test find_team_id
            team_id = await espn_client.find_team_id(team_name)
            print(f"   Team ID: {team_id}")

            if team_id:
                # Test get_team_roster
                roster_data = await espn_client.get_team_roster(team_name)
                if roster_data.get("error"):
                    print(f"   ❌ Roster Error: {roster_data.get('message')}")
                else:
                    print(
                        f"   ✅ Roster Success: {roster_data.get('total_players', 0)} players"
                    )
            else:
                print(f"   ❌ Team ID not found")

        except Exception as e:
            print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_team_matching())
