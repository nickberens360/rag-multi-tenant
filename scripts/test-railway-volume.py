#!/usr/bin/env python3
"""
Test script to verify Railway persistent volume access and database initialization.
Run this on your Railway deployment to diagnose database path issues.
"""

import logging
import os
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_path_access(path: Path) -> bool:
    """Test if we can read/write to a path."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test"
        test_file.write_text("Railway volume test")
        test_file.read_text()
        test_file.unlink()
        logger.info(f"✅ Path {path} is writable")
        return True
    except Exception as e:
        logger.error(f"❌ Path {path} failed: {e}")
        return False


def test_sqlite_creation(path: Path) -> bool:
    """Test SQLite database creation with proper resource management."""
    db_path = path / "test_admin.db"
    try:
        # Test write using context manager for safety
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test (name) VALUES ('Railway Test')")

        # Test read using separate context manager
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM test WHERE id = 1")
            result = cursor.fetchone()

        if result and result[0] == "Railway Test":
            logger.info(f"✅ SQLite database works at {path}")
            return True
        else:
            logger.error(f"❌ SQLite database read/write failed at {path}")
            return False
    except Exception as e:
        logger.error(f"❌ SQLite test failed at {path}: {e}")
        return False
    finally:
        # Ensure cleanup happens even if tests fail
        if db_path.exists():
            try:
                db_path.unlink()
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up test database {db_path}: {cleanup_error}")


def main():
    """Run Railway volume tests."""
    logger.info("🚀 Starting Railway persistent volume tests...")

    # Check environment
    railway_env = os.getenv("RAILWAY_ENVIRONMENT_NAME")
    if railway_env:
        logger.info(f"📍 Running in Railway environment: {railway_env}")
    else:
        logger.info("📍 Running in local development environment")

    # Test various paths (prioritizing persistent storage)
    persistent_paths = [
        Path("/data"),  # Standard Railway volume mount (PERSISTENT)
        Path("/app/data"),  # Alternative mount (PERSISTENT)
    ]

    ephemeral_paths = [
        Path("/tmp"),  # Temporary storage (EPHEMERAL - lost on restart)
        Path("/app/backend/logs"),  # Application directory (EPHEMERAL - overwritten on deploy)
        Path.cwd() / "backend" / "logs",  # Current working directory (EPHEMERAL)
    ]

    persistent_paths + ephemeral_paths

    persistent_working = []
    ephemeral_working = []

    # Test persistent paths first
    logger.info("🔍 Testing PERSISTENT storage paths:")
    for path in persistent_paths:
        logger.info(f"   Testing: {path}")
        if test_path_access(path) and test_sqlite_creation(path):
            persistent_working.append(path)
            logger.info(f"   ✅ {path} works (PERSISTENT)")
        else:
            logger.info(f"   ❌ {path} failed")

    # Test ephemeral paths
    logger.info("\n🔍 Testing EPHEMERAL storage paths (NOT RECOMMENDED):")
    for path in ephemeral_paths:
        logger.info(f"   Testing: {path}")
        if test_path_access(path) and test_sqlite_creation(path):
            ephemeral_working.append(path)
            logger.info(f"   ⚠️  {path} works (EPHEMERAL - data will be lost!)")
        else:
            logger.info(f"   ❌ {path} failed")

    logger.info("\n" + "=" * 60)
    if persistent_working:
        logger.info("✅ PERSISTENT storage found (RECOMMENDED):")
        for path in persistent_working:
            logger.info(f"   - {path} (data survives restarts/deploys)")
        logger.info(f"\n💡 Using: {persistent_working[0]} for database storage")
    elif ephemeral_working:
        logger.warning("⚠️  Only EPHEMERAL storage found:")
        for path in ephemeral_working:
            logger.warning(f"   - {path} (data will be LOST on restart/deploy)")
        logger.error("\n🚨 CRITICAL: No persistent volume configured!")
        logger.error("🔧 Configure Railway persistent volume or data will be lost!")
    else:
        logger.error("❌ No working paths found for database storage!")
        logger.error("🔧 Check Railway persistent volume and permissions")

    # Show current directory and permissions
    cwd = Path.cwd()
    logger.info(f"\n📂 Current working directory: {cwd}")
    logger.info(f"📂 Directory exists: {cwd.exists()}")
    logger.info(f"📂 Directory is writable: {os.access(cwd, os.W_OK)}")

    # Check Railway volume mount
    data_path = Path("/data")
    logger.info(f"💾 /data exists: {data_path.exists()}")
    if data_path.exists():
        logger.info(f"💾 /data is writable: {os.access(data_path, os.W_OK)}")
        try:
            contents = list(data_path.iterdir())
            logger.info(f"💾 /data contents: {contents}")
        except PermissionError:
            logger.error("💾 /data permission denied for listing contents")


if __name__ == "__main__":
    main()
