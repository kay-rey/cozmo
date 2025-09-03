#!/usr/bin/env python3
"""
Find LA Galaxy team ID in ESPN API.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.espn_api import espn_client


async def find_galaxy_team():
    """Find LA Galaxy team ID and test roster endpoint."""

    print("🔍 Finding LA Galaxy team ID...")

    try:
        teams_data = await espn_client._make_request("teams")

        sports = teams_data.get("sports", [])
        if not sports:
            print("❌ No sports data found")
            return

        leagues = sports[0].get("leagues", [])
        if not leagues:
            print("❌ No leagues data found")
            return

        teams = leagues[0].get("teams", [])
        if not teams:
            print("❌ No teams data found")
            return

        print(f"📊 Found {len(teams)} MLS teams")

        # Look for LA Galaxy
        galaxy_team = None
        for team_entry in teams:
            team_info = team_entry.get("team", {})
            team_name = team_info.get("displayName", "").lower()

            if "galaxy" in team_name:
                galaxy_team = team_info
                print(f"🌟 Found LA Galaxy!")
                print(f"   ID: {team_info.get('id')}")
                print(f"   Name: {team_info.get('displayName')}")
                print(f"   Slug: {team_info.get('slug')}")
                break

        if not galaxy_team:
            print("❌ LA Galaxy not found")
            # Print first few teams for reference
            print("Available teams:")
            for i, team_entry in enumerate(teams[:10]):
                team_info = team_entry.get("team", {})
                print(
                    f"   {i + 1}. {team_info.get('displayName')} (ID: {team_info.get('id')})"
                )
            return

        # Test roster endpoint
        team_id = galaxy_team.get("id")
        print(f"\n🏟️ Testing roster endpoint for team {team_id}...")

        try:
            roster_data = await espn_client._make_request(f"teams/{team_id}/roster")
            print(f"✅ Roster endpoint works!")
            print(f"   Data keys: {list(roster_data.keys())}")

            athletes = roster_data.get("athletes", [])
            print(f"   Athletes groups: {len(athletes)}")

            for i, group in enumerate(athletes[:3]):  # Show first 3 groups
                position = group.get("position", {}).get("displayName", "Unknown")
                items = group.get("items", [])
                print(f"   Group {i + 1}: {position} ({len(items)} players)")

                # Show first player in group
                if items:
                    player = items[0]
                    print(f"      Sample: {player.get('displayName', 'Unknown')}")

        except Exception as e:
            print(f"❌ Roster endpoint failed: {e}")

            # Try alternative endpoints
            alt_endpoints = [
                f"teams/{team_id}",
                f"teams/{team_id}/athletes",
                f"teams/{team_id}/schedule",
            ]

            for endpoint in alt_endpoints:
                try:
                    print(f"\n🔄 Trying {endpoint}...")
                    data = await espn_client._make_request(endpoint)
                    print(f"✅ {endpoint} works! Keys: {list(data.keys())}")
                except Exception as e:
                    print(f"❌ {endpoint} failed: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    try:
        await find_galaxy_team()
    finally:
        await espn_client.close()


if __name__ == "__main__":
    asyncio.run(main())
