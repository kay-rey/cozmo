#!/usr/bin/env python3
"""
Code structure validation for Cozmo Discord Bot.
Tests that all required files exist and have proper structure.
"""

import ast
import sys
from pathlib import Path


def test_file_exists(file_path: str) -> bool:
    """Test if a file exists."""
    path = Path(file_path)
    exists = path.exists()
    print(f"{'✓' if exists else '✗'} {file_path} {'exists' if exists else 'missing'}")
    return exists


def test_python_syntax(file_path: str) -> bool:
    """Test if a Python file has valid syntax."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        ast.parse(content)
        print(f"✓ {file_path} has valid Python syntax")
        return True
    except SyntaxError as e:
        print(f"✗ {file_path} has syntax error: {e}")
        return False
    except Exception as e:
        print(f"✗ {file_path} validation failed: {e}")
        return False


def test_main_py_structure():
    """Test main.py has required components."""
    print("\nTesting main.py structure:")
    print("-" * 25)

    if not test_file_exists("main.py"):
        return False

    if not test_python_syntax("main.py"):
        return False

    try:
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Check for required components
        required_components = [
            ("CozmoBot class", "class CozmoBot"),
            ("setup_hook method", "async def setup_hook"),
            ("on_ready method", "async def on_ready"),
            ("main function", "async def main"),
            (
                "Bot startup message",
                "Cozmo is online and ready to cheer for the Galaxy!",
            ),
            ("Error handling", "on_command_error"),
            ("Cog loading", "load_extension"),
            ("API cleanup", "sports_client.close()"),
        ]

        passed = 0
        for name, pattern in required_components:
            if pattern in content:
                print(f"✓ {name} found")
                passed += 1
            else:
                print(f"✗ {name} missing")

        print(
            f"Main.py structure: {passed}/{len(required_components)} components found"
        )
        return passed == len(required_components)

    except Exception as e:
        print(f"✗ Failed to analyze main.py: {e}")
        return False


def test_config_structure():
    """Test config.py has required components."""
    print("\nTesting config.py structure:")
    print("-" * 26)

    if not test_file_exists("config.py"):
        return False

    if not test_python_syntax("config.py"):
        return False

    try:
        with open("config.py", "r", encoding="utf-8") as f:
            content = f.read()

        required_components = [
            ("Config class", "class Config"),
            ("DISCORD_TOKEN", "DISCORD_TOKEN"),
            ("SPORTS_API_KEY", "SPORTS_API_KEY"),
            ("NEWS_CHANNEL_ID", "NEWS_CHANNEL_ID"),
            ("Environment loading", "load_dotenv"),
            ("Global config instance", "config = Config"),
        ]

        passed = 0
        for name, pattern in required_components:
            if pattern in content:
                print(f"✓ {name} found")
                passed += 1
            else:
                print(f"✗ {name} missing")

        print(
            f"Config.py structure: {passed}/{len(required_components)} components found"
        )
        return passed == len(required_components)

    except Exception as e:
        print(f"✗ Failed to analyze config.py: {e}")
        return False


def test_api_structure():
    """Test API files have required components."""
    print("\nTesting API structure:")
    print("-" * 21)

    api_files = ["api/sports_api.py", "api/news_api.py"]
    all_passed = True

    for api_file in api_files:
        if not test_file_exists(api_file):
            all_passed = False
            continue

        if not test_python_syntax(api_file):
            all_passed = False
            continue

        try:
            with open(api_file, "r", encoding="utf-8") as f:
                content = f.read()

            if "sports_api" in api_file:
                required = [
                    ("SportsAPIClient class", "class SportsAPIClient"),
                    ("get_next_match function", "async def get_next_match"),
                    ("get_standings function", "async def get_standings"),
                    ("get_player_stats function", "async def get_player_stats"),
                    ("Global client", "sports_client ="),
                ]
            else:  # news_api
                required = [
                    ("NewsAPIClient class", "class NewsAPIClient"),
                    ("get_latest_news function", "async def get_latest_news"),
                    ("Global client", "news_client ="),
                ]

            passed = 0
            for name, pattern in required:
                if pattern in content:
                    passed += 1
                else:
                    print(f"✗ {api_file}: {name} missing")
                    all_passed = False

            if passed == len(required):
                print(f"✓ {api_file} structure complete")

        except Exception as e:
            print(f"✗ Failed to analyze {api_file}: {e}")
            all_passed = False

    return all_passed


def test_cogs_structure():
    """Test that all required cogs exist."""
    print("\nTesting cogs structure:")
    print("-" * 22)

    required_cogs = ["matchday.py", "stats.py", "news.py", "trivia.py"]
    all_passed = True

    for cog in required_cogs:
        cog_path = f"cogs/{cog}"
        if not test_file_exists(cog_path):
            all_passed = False
            continue

        if not test_python_syntax(cog_path):
            all_passed = False
            continue

        print(f"✓ {cog} structure valid")

    return all_passed


def test_env_template():
    """Test .env.template exists with required variables."""
    print("\nTesting environment configuration:")
    print("-" * 33)

    if not test_file_exists(".env.template"):
        return False

    try:
        with open(".env.template", "r", encoding="utf-8") as f:
            content = f.read()

        required_vars = ["DISCORD_TOKEN", "SPORTS_API_KEY", "NEWS_CHANNEL_ID"]
        passed = 0

        for var in required_vars:
            if var in content:
                print(f"✓ {var} template found")
                passed += 1
            else:
                print(f"✗ {var} template missing")

        return passed == len(required_vars)

    except Exception as e:
        print(f"✗ Failed to analyze .env.template: {e}")
        return False


def main():
    """Run all structure tests."""
    print("=" * 50)
    print("Cozmo Discord Bot Code Structure Tests")
    print("=" * 50)

    tests = [
        ("Main Bot Structure", test_main_py_structure),
        ("Configuration Structure", test_config_structure),
        ("API Structure", test_api_structure),
        ("Cogs Structure", test_cogs_structure),
        ("Environment Template", test_env_template),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"\n✓ {test_name} PASSED")
            else:
                print(f"\n✗ {test_name} FAILED")
        except Exception as e:
            print(f"\n✗ {test_name} FAILED with exception: {e}")

    print("\n" + "=" * 50)
    print(f"Structure Test Results: {passed}/{total} tests passed")
    print("=" * 50)

    if passed == total:
        print("🎉 All structure tests passed! Bot code is properly organized.")
        return True
    else:
        print("❌ Some structure tests failed. Please check the code organization.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
