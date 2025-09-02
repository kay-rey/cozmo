#!/usr/bin/env python3
"""
Master test runner for Cozmo Discord Bot.
Runs all test suites to verify complete functionality.
"""

import asyncio
import subprocess
import sys
from pathlib import Path


def run_test_script(script_name):
    """Run a test script and return success status."""
    print(f"\n{'=' * 60}")
    print(f"Running {script_name}")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, script_name], capture_output=False, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to run {script_name}: {e}")
        return False


def main():
    """Run all test suites."""
    print("🚀 Cozmo Discord Bot - Complete Test Suite")
    print("=" * 60)
    print("Running comprehensive tests to verify bot functionality...")

    # Change to project root directory for tests to work properly
    project_root = Path(__file__).parent.parent
    original_cwd = Path.cwd()

    try:
        import os

        os.chdir(project_root)

        test_scripts = [
            ("Code Structure Tests", "tests/test_code_structure.py"),
            ("Final Integration Tests", "tests/test_bot_final.py"),
            ("Bot Startup Tests", "tests/test_bot_startup.py"),
            ("Command Functionality Tests", "tests/test_bot_commands.py"),
        ]

        results = []

        for test_name, script_name in test_scripts:
            if Path(script_name).exists():
                success = run_test_script(script_name)
                results.append((test_name, success))
            else:
                print(f"⚠ Test script {script_name} not found")
                results.append((test_name, False))

    finally:
        # Restore original working directory
        os.chdir(original_cwd)

    # Summary
    print(f"\n{'=' * 60}")
    print("TEST SUITE SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {test_name}")
        if success:
            passed += 1

    print(f"\nOverall Results: {passed}/{total} test suites passed")

    if passed == total:
        print("\n🎉 ALL TEST SUITES PASSED!")
        print("\nCozmo Discord Bot is fully functional and ready for deployment!")
        print("\n📋 What's been verified:")
        print("• ✅ Code structure and syntax")
        print("• ✅ Module imports and dependencies")
        print("• ✅ Configuration management")
        print("• ✅ API client initialization")
        print("• ✅ Bot initialization and setup")
        print("• ✅ Cog loading and registration")
        print("• ✅ Command registration")
        print("• ✅ Error handling")
        print("• ✅ Trivia questions format")
        print("• ✅ Startup sequence")
        print("• ✅ Shutdown and cleanup")

        print("\n🚀 Next Steps:")
        print("1. Configure .env with real Discord token and API keys")
        print("2. Invite bot to your Discord server with proper permissions")
        print("3. Run: python3 main.py")
        print("4. Test commands: !nextmatch, !standings, !playerstats, !news, !trivia")

        return True
    else:
        print(f"\n❌ {total - passed} test suite(s) failed.")
        print("Please review the test output above and fix any issues.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
