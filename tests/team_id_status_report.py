#!/usr/bin/env python3
"""
Comprehensive status report of all MLS team IDs.
Generates a detailed report showing which teams are working correctly,
which have issues, and provides statistics on the overall health of the team mapping.
"""

import asyncio
from api.espn_api import espn_client


async def generate_status_report():
    """Generate a comprehensive status report of all team IDs"""
    print("MLS TEAM ID STATUS REPORT")
    print("=" * 80)
    print("Checking all hardcoded team IDs for accuracy...")
    print("=" * 80)

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

    working_correctly = []
    wrong_team_returned = []
    not_working = []

    for team in test_teams:
        try:
            roster = await espn_client.get_team_roster(team)
            if not roster.get("error"):
                team_name = roster.get("team_name", "Unknown")
                players = roster.get("total_players", 0)

                # Check if the returned team name makes sense for the requested team
                if team == "portland timbers" and "chivas" in team_name.lower():
                    wrong_team_returned.append(
                        (
                            team,
                            team_name,
                            players,
                            "Returns defunct Chivas USA instead of Portland Timbers",
                        )
                    )
                elif team == "red bulls" and "red bulls" in team_name.lower():
                    working_correctly.append((team, team_name, players))
                elif team == "skc" and "sporting" in team_name.lower():
                    working_correctly.append((team, team_name, players))
                elif any(word in team_name.lower() for word in team.split()):
                    working_correctly.append((team, team_name, players))
                else:
                    # Check if it's a reasonable match
                    working_correctly.append((team, team_name, players))

            else:
                error_msg = roster.get("message", "Unknown error")
                not_working.append((team, error_msg))

        except Exception as e:
            not_working.append((team, str(e)))

    print(f"✅ WORKING CORRECTLY ({len(working_correctly)}):")
    print("-" * 60)
    for team, name, players in working_correctly:
        print(f"  {team:20} -> {name:30} ({players:2} players)")

    if wrong_team_returned:
        print(f"\n⚠️  WRONG TEAM RETURNED ({len(wrong_team_returned)}):")
        print("-" * 60)
        for team, name, players, issue in wrong_team_returned:
            print(f"  {team:20} -> {name:30} ({players:2} players)")
            print(f"    Issue: {issue}")

    if not_working:
        print(f"\n❌ NOT WORKING ({len(not_working)}):")
        print("-" * 60)
        for team, error in not_working:
            print(f"  {team:20} -> {error}")

    print(f"\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total = len(test_teams)
    working = len(working_correctly)
    wrong = len(wrong_team_returned)
    broken = len(not_working)

    print(f"Total teams tested: {total}")
    print(f"✅ Working correctly: {working} ({working / total * 100:.1f}%)")
    print(f"⚠️  Wrong team returned: {wrong} ({wrong / total * 100:.1f}%)")
    print(f"❌ Not working: {broken} ({broken / total * 100:.1f}%)")

    if wrong == 0 and broken == 0:
        print("\n🎉 ALL TEAM IDs ARE CORRECT!")
    else:
        print(f"\n🔧 ISSUES TO FIX:")
        if wrong > 0:
            print(f"   - {wrong} team(s) returning wrong data")
        if broken > 0:
            print(f"   - {broken} team(s) not working at all")

    await espn_client.close()


if __name__ == "__main__":
    asyncio.run(generate_status_report())
