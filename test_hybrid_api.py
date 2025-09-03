#!/usr/bin/env python3
"""
Test script for the hybrid API system.
Tests ESPN API integration and fallback functionality.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from api.espn_api import espn_client, ESPNAPIError
from api.sports_api import get_team_roster_hybrid, get_standings_hybrid, SportsAPIError

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_espn_standings():
    """Test ESPN standings API."""
    print("\n🏆 Testing ESPN Standings API...")
    try:
        standings = await espn_client.get_mls_standings()

        if standings.get("error"):
            print(f"❌ ESPN Standings Error: {standings.get('message')}")
            return False

        west_teams = standings.get("western_conference", [])
        east_teams = standings.get("eastern_conference", [])

        print(f"✅ ESPN Standings Success!")
        print(f"   Western Conference: {len(west_teams)} teams")
        print(f"   Eastern Conference: {len(east_teams)} teams")

        if west_teams:
            print(
                f"   Sample West team: {west_teams[0].get('name')} - {west_teams[0].get('points', 0)} pts"
            )
        if east_teams:
            print(
                f"   Sample East team: {east_teams[0].get('name')} - {east_teams[0].get('points', 0)} pts"
            )

        return True

    except Exception as e:
        print(f"❌ ESPN Standings Failed: {e}")
        return False


async def test_espn_roster():
    """Test ESPN roster API."""
    print("\n👥 Testing ESPN Roster API...")
    try:
        roster = await espn_client.get_team_roster("LA Galaxy")

        if roster.get("error"):
            print(f"❌ ESPN Roster Error: {roster.get('message')}")
            return False

        total_players = roster.get("total_players", 0)
        positions = roster.get("positions", {})

        print(f"✅ ESPN Roster Success!")
        print(f"   Team: {roster.get('team_name')}")
        print(f"   Total Players: {total_players}")
        print(f"   Positions found: {list(positions.keys())}")

        # Check for goalkeepers specifically
        gk_found = any(
            "goalkeeper" in pos.lower() or "keeper" in pos.lower()
            for pos in positions.keys()
        )
        print(f"   Goalkeepers found: {'✅ Yes' if gk_found else '❌ No'}")

        return True

    except Exception as e:
        print(f"❌ ESPN Roster Failed: {e}")
        return False


async def test_hybrid_standings():
    """Test hybrid standings function."""
    print("\n🔄 Testing Hybrid Standings...")
    try:
        standings = await get_standings_hybrid()

        if standings.get("error"):
            print(f"❌ Hybrid Standings Error: {standings.get('message')}")
            return False

        source = standings.get("source", "Unknown")
        west_teams = standings.get("western_conference", [])
        east_teams = standings.get("eastern_conference", [])

        print(f"✅ Hybrid Standings Success!")
        print(f"   Data Source: {source}")
        print(f"   Western Conference: {len(west_teams)} teams")
        print(f"   Eastern Conference: {len(east_teams)} teams")

        return True

    except Exception as e:
        print(f"❌ Hybrid Standings Failed: {e}")
        return False


async def test_hybrid_roster():
    """Test hybrid roster function."""
    print("\n🔄 Testing Hybrid Roster...")
    try:
        roster = await get_team_roster_hybrid("LA Galaxy")

        if roster.get("error"):
            print(f"❌ Hybrid Roster Error: {roster.get('message')}")
            return False

        source = roster.get("source", "Unknown")
        total_players = roster.get("total_players", 0)
        positions = roster.get("positions", {})

        print(f"✅ Hybrid Roster Success!")
        print(f"   Data Source: {source}")
        print(f"   Team: {roster.get('team_name')}")
        print(f"   Total Players: {total_players}")
        print(f"   Positions: {list(positions.keys())}")

        # Check for goalkeepers
        gk_found = any(
            "goalkeeper" in pos.lower() or "keeper" in pos.lower()
            for pos in positions.keys()
        )
        print(f"   Goalkeepers found: {'✅ Yes' if gk_found else '❌ No'}")

        return True

    except Exception as e:
        print(f"❌ Hybrid Roster Failed: {e}")
        return False


async def test_different_teams():
    """Test roster for different teams."""
    print("\n🏟️ Testing Different Teams...")
    teams_to_test = ["Inter Miami CF", "LAFC", "Seattle Sounders FC"]

    for team in teams_to_test:
        try:
            print(f"\n   Testing {team}...")
            roster = await get_team_roster_hybrid(team)

            if roster.get("error"):
                print(f"   ❌ {team}: {roster.get('message')}")
            else:
                source = roster.get("source", "Unknown")
                total = roster.get("total_players", 0)
                print(f"   ✅ {team}: {total} players from {source}")

        except Exception as e:
            print(f"   ❌ {team}: {e}")


async def main():
    """Run all tests."""
    print("🚀 Starting Hybrid API System Tests...")
    print("=" * 50)

    tests = [
        ("ESPN Standings", test_espn_standings),
        ("ESPN Roster", test_espn_roster),
        ("Hybrid Standings", test_hybrid_standings),
        ("Hybrid Roster", test_hybrid_roster),
        ("Different Teams", test_different_teams),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")

    # Cleanup
    try:
        await espn_client.close()
        print("\n🧹 Cleaned up API clients")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")


if __name__ == "__main__":
    asyncio.run(main())
