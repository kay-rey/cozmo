#!/usr/bin/env python3
"""
Bot setup verification script.
Verifies that the bot can be initialized and all components are ready.
"""

import sys
import os
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are available."""
    print("Checking dependencies...")

    required_modules = [
        ("discord", "discord.py"),
        ("aiohttp", "aiohttp"),
        ("dotenv", "python-dotenv"),
        ("feedparser", "feedparser"),
    ]

    missing = []
    for module, package in required_modules:
        try:
            __import__(module)
            print(f"✓ {package} is available")
        except ImportError:
            print(f"✗ {package} is missing")
            missing.append(package)

    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False

    return True


def check_configuration():
    """Check if configuration is properly set up."""
    print("\nChecking configuration...")

    # Check .env file exists
    if not Path(".env").exists():
        print("✗ .env file not found")
        print("Copy .env.template to .env and fill in your values")
        return False

    print("✓ .env file exists")

    # Check .env has required variables
    with open(".env", "r") as f:
        env_content = f.read()

    required_vars = ["DISCORD_TOKEN", "SPORTS_API_KEY", "NEWS_CHANNEL_ID"]
    missing_vars = []

    for var in required_vars:
        if var not in env_content:
            missing_vars.append(var)
        elif f"{var}=" in env_content:
            # Check if it has a value (not just the key)
            lines = env_content.split("\n")
            for line in lines:
                if line.startswith(f"{var}=") and "=" in line:
                    value = line.split("=", 1)[1].strip().strip("\"'")
                    if value and not value.startswith("your_") and value != "123":
                        print(f"✓ {var} is configured")
                        break
                    else:
                        print(f"⚠ {var} needs a real value")
                        missing_vars.append(var)
                        break

    if missing_vars:
        print(f"Configuration issues with: {', '.join(missing_vars)}")
        return False

    return True


def check_project_structure():
    """Check if all required files and directories exist."""
    print("\nChecking project structure...")

    required_files = [
        "main.py",
        "config.py",
        "requirements.txt",
        "api/__init__.py",
        "api/sports_api.py",
        "api/news_api.py",
        "cogs/__init__.py",
        "cogs/matchday.py",
        "cogs/stats.py",
        "cogs/news.py",
        "cogs/trivia.py",
        "trivia_questions.py",
    ]

    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path}")
            missing_files.append(file_path)

    if missing_files:
        print(f"Missing files: {', '.join(missing_files)}")
        return False

    return True


def main():
    """Run all verification checks."""
    print("=" * 50)
    print("Cozmo Discord Bot Setup Verification")
    print("=" * 50)

    checks = [
        ("Project Structure", check_project_structure),
        ("Dependencies", check_dependencies),
        ("Configuration", check_configuration),
    ]

    passed = 0
    total = len(checks)

    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        print("-" * len(check_name))

        try:
            if check_func():
                passed += 1
                print(f"✓ {check_name} check passed")
            else:
                print(f"✗ {check_name} check failed")
        except Exception as e:
            print(f"✗ {check_name} check failed with error: {e}")

    print("\n" + "=" * 50)
    print(f"Verification Results: {passed}/{total} checks passed")
    print("=" * 50)

    if passed == total:
        print("🎉 Bot setup is complete and ready to run!")
        print("\nTo start the bot:")
        print(
            "1. Make sure all dependencies are installed: pip install -r requirements.txt"
        )
        print("2. Configure your .env file with real values")
        print("3. Run: python3 main.py")
        return True
    else:
        print("❌ Setup incomplete. Please address the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
