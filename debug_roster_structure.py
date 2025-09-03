#!/usr/bin/env python3
"""
Debug the exact structure of ESPN roster data.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.espn_api import espn_client


async def debug_roster_structure():
    """Debug the exact structure of roster data."""

    print("🔍 Debugging ESPN roster structure...")

    try:
        # Get LA Galaxy roster (ID: 187)
        roster_data = await espn_client._make_request("teams/187/roster")

        print("📄 Full roster data structure:")
        print(json.dumps(roster_data, indent=2)[:2000])  # First 2000 chars

        athletes = roster_data.get("athletes", [])
        print(f"\n👥 Athletes array length: {len(athletes)}")

        # Examine first few athlete groups
        for i, group in enumerate(athletes[:5]):
            print(f"\n📋 Group {i + 1}:")
            print(f"   Keys: {list(group.keys())}")

            position = group.get("position")
            if position:
                print(f"   Position: {position}")

            items = group.get("items", [])
            print(f"   Items length: {len(items)}")

            # If items exist, show structure
            if items:
                print(f"   First item keys: {list(items[0].keys())}")
                print(f"   First item sample: {json.dumps(items[0], indent=2)[:500]}")
            else:
                # Maybe the structure is different
                print(f"   Full group structure: {json.dumps(group, indent=2)[:500]}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    try:
        await debug_roster_structure()
    finally:
        await espn_client.close()


if __name__ == "__main__":
    asyncio.run(main())
