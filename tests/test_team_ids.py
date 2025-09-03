#!/usr/bin/env python3
"""
Test script to verify all hardcoded MLS team IDs in ESPN API.
This script tests all teams in the hardcoded mapping to ensure they return correct data.
"""

import asyncio
import aiohttp
from api.espn_api import espn_client


async def test_all_hardcoded_teams():
    """Test all teams in the hardcoded mapping"""
    # All unique team names from the mapping
    test_teams = [
        "la galaxy",
        "inter miami",
        "lafc",
        "atlanta united",
        "seattle sounders",
        "portland timbers",
        "nycfc",
        "skc",
        "real salt lake",
        "colorado rapids",
        "fc dallas",
        "houston dynamo",
        "san jose earthquakes",
        "vancouver whitecaps",
        "minnesota united",
        "fc cincinnati",
        "nashville sc",
        "austin fc",
        "charlotte fc",
        "st. louis city sc",
        "orlando city",
        "red bulls",
        "toronto fc",
        "chicago fire",
        "new england revolution",
        "columbus crew",
        "dc united",
        "philadelphia union",
        "cf montreal",
    ]

    working_teams = []
    broken_teams = []

    print("Testing all hardcoded MLS team IDs...")
    print("=" * 60)

    for team in test_teams:
        try:
            roster = await espn_client.get_team_roster(team)
            if not roster.get("error"):
                players = roster.get("total_players", 0)
                team_name = roster.get("team_name", "Unknown")
                working_teams.append((team, team_name, players))
                print(f"✅ {team:20} -> {team_name} ({players} players)")
            else:
                error_msg = roster.get("message", "Unknown error")
                broken_teams.append((team, error_msg))
                print(f"❌ {team:20} -> {error_msg}")
        except Exception as e:
            broken_teams.append((team, str(e)))
            print(f"❌ {team:20} -> Exception: {str(e)}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(
        f"Working teams: {len(working_teams)}/{len(test_teams)} ({len(working_teams) / len(test_teams) * 100:.1f}%)"
    )

    if broken_teams:
        print(f"\nBroken teams ({len(broken_teams)}):")
        for team, error in broken_teams:
            print(f"  - {team}: {error}")
    else:
        print("\n🎉 ALL TEAMS WORKING!")

    await espn_client.close()


async def find_correct_portland_id():
    """Try to find the correct Portland Timbers ID"""
    print("\nSearching for correct Portland Timbers ID...")
    print("=" * 50)

    # Test various potential IDs for Portland
    test_ids = ["4772", "188", "192", "20", "4770", "4771", "4773", "4774", "4775"]

    async with aiohttp.ClientSession() as session:
        for test_id in test_ids:
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/mls/teams/{test_id}/roster"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        team_name = data.get("team", {}).get("displayName", "Unknown")
                        players = len(data.get("athletes", []))
                        print(f"ID {test_id:4}: {team_name} ({players} players)")

                        # Check if this might be Portland
                        if (
                            "portland" in team_name.lower()
                            or "timbers" in team_name.lower()
                        ):
                            print(f"  ⭐ POTENTIAL MATCH for Portland Timbers!")
                    else:
                        print(f"ID {test_id:4}: HTTP {response.status}")
            except Exception as e:
                print(f"ID {test_id:4}: Error - {e}")


if __name__ == "__main__":
    print("MLS Team ID Verification Script")
    print("=" * 60)

    # Run the main test
    asyncio.run(test_all_hardcoded_teams())

    # Try to find Portland's correct ID
    asyncio.run(find_correct_portland_id())
