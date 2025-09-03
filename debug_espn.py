#!/usr/bin/env python3
"""
Debug script to examine ESPN API responses.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.espn_api import espn_client


async def debug_espn_endpoints():
    """Debug ESPN API endpoints to see what data is available."""

    print("🔍 Debugging ESPN API endpoints...")

    # Test basic endpoints
    endpoints_to_test = [
        "teams",
        "standings",
        "scoreboard",
        "teams/28/roster",  # LA Galaxy team ID might be 28
    ]

    for endpoint in endpoints_to_test:
        print(f"\n📡 Testing endpoint: {endpoint}")
        try:
            data = await espn_client._make_request(endpoint)
            print(
                f"✅ Success! Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
            )

            # Print first few lines of response for inspection
            json_str = json.dumps(data, indent=2)[:500]
            print(f"📄 Sample data:\n{json_str}...")

        except Exception as e:
            print(f"❌ Failed: {e}")

    # Test teams endpoint specifically
    print(f"\n🏟️ Detailed teams endpoint analysis...")
    try:
        teams_data = await espn_client._make_request("teams")
        print(f"Teams data structure: {json.dumps(teams_data, indent=2)[:1000]}...")

    except Exception as e:
        print(f"❌ Teams endpoint failed: {e}")


async def main():
    try:
        await debug_espn_endpoints()
    finally:
        await espn_client.close()


if __name__ == "__main__":
    asyncio.run(main())
