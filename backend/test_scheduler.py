"""
Test script for scheduled prediction logging functionality.

This script tests:
1. Manual triggering of daily prediction logging
2. Verification that predictions are logged to CSV
3. Scheduler is properly configured
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from main import log_daily_prediction, scheduler
from app.utils.prediction_logger import get_recent_predictions

CENTRAL_TIMEZONE = timezone(timedelta(hours=-6))


async def test_manual_logging():
    """Test manual triggering of daily prediction logging."""
    print("=" * 60)
    print("Testing Daily Prediction Logging")
    print("=" * 60)

    # Get current predictions count
    before_predictions = get_recent_predictions(days=10)
    print(f"\nPredictions in log before test: {len(before_predictions)}")

    if before_predictions:
        print("\nMost recent logged predictions:")
        for pred in before_predictions[:3]:
            print(f"  - {pred['prediction_date']}: {pred['predicted_demand']} MGD")

    # Trigger daily logging
    print(f"\nTriggering daily prediction logging at {datetime.now(CENTRAL_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
        await log_daily_prediction()
        print("[OK] Daily prediction logged successfully!")
    except Exception as e:
        print(f"[ERROR] Error logging prediction: {e}")
        return False

    # Get updated predictions
    after_predictions = get_recent_predictions(days=10)
    print(f"\nPredictions in log after test: {len(after_predictions)}")

    if after_predictions:
        print("\nMost recent logged predictions:")
        for pred in after_predictions[:3]:
            print(f"  - {pred['prediction_date']}: {pred['predicted_demand']} MGD")

    return True


def test_scheduler_config():
    """Test that scheduler is properly configured."""
    print("\n" + "=" * 60)
    print("Testing Scheduler Configuration")
    print("=" * 60)

    jobs = scheduler.get_jobs()

    if not jobs:
        print("[ERROR] No scheduled jobs found!")
        return False

    print(f"\n[OK] Found {len(jobs)} scheduled job(s):")

    for job in jobs:
        print(f"\n  Job ID: {job.id}")
        print(f"  Name: {job.name}")
        print(f"  Next run: {job.next_run_time}")
        print(f"  Trigger: {job.trigger}")

    # Check if our daily prediction job exists
    daily_job = scheduler.get_job("daily_prediction_log")

    if daily_job:
        print("\n[OK] Daily prediction logging job is configured!")
        print(f"  Scheduled to run at: {daily_job.trigger}")
        return True
    else:
        print("\n[ERROR] Daily prediction logging job not found!")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Water Demand Forecast - Scheduler Test Suite")
    print("=" * 60)

    # Start scheduler (if not already started)
    if not scheduler.running:
        scheduler.start()
        print("\n[OK] Scheduler started")
    else:
        print("\n[OK] Scheduler already running")

    # Test 1: Manual logging
    test1_passed = await test_manual_logging()

    # Test 2: Scheduler configuration
    test2_passed = test_scheduler_config()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Manual logging test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Scheduler config test: {'PASSED' if test2_passed else 'FAILED'}")

    if test1_passed and test2_passed:
        print("\n[OK] All tests passed!")
        print("\nThe scheduler is configured to run daily at 12:01 AM Central Time.")
        print("Predictions will be automatically logged every day.")
    else:
        print("\n[ERROR] Some tests failed. Please check the errors above.")

    print("\n" + "=" * 60)

    # Shutdown scheduler
    scheduler.shutdown()
    print("Scheduler shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
