#!/usr/bin/env python3
"""
Migration testing script for edge cases and production-like scenarios.

Tests various edge cases for settings migration including:
- Missing settings data
- Corrupt JSON data  
- Database connection failures
- Large settings payloads
- Rollback scenarios
"""

import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.admin_database import admin_db_manager
from backend.core.settings_migration import SettingsMigrator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class MigrationTestRunner:
    """Test runner for migration edge cases."""

    def __init__(self):
        self.test_results = []
        self.migrator = SettingsMigrator()

    def run_all_tests(self) -> bool:
        """Run all migration test scenarios."""
        tests = [
            ("test_normal_migration", self.test_normal_migration),
            ("test_missing_settings", self.test_missing_settings),
            ("test_corrupt_json", self.test_corrupt_json),
            ("test_large_payload", self.test_large_payload),
            ("test_rollback_scenario", self.test_rollback_scenario),
            ("test_partial_migration_failure", self.test_partial_migration_failure),
            ("test_backup_creation", self.test_backup_creation),
        ]

        logger.info("Starting migration edge case testing...")

        for test_name, test_func in tests:
            try:
                logger.info(f"Running {test_name}...")
                result = test_func()
                self.test_results.append((test_name, "PASS" if result else "FAIL"))
                logger.info(f"{test_name}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                logger.error(f"{test_name}: ERROR - {e}")
                self.test_results.append((test_name, f"ERROR: {e}"))

        # Print summary
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        total = len(self.test_results)

        logger.info(f"\nTest Summary: {passed}/{total} passed")
        for test_name, result in self.test_results:
            status_icon = "✓" if result == "PASS" else "✗"
            logger.info(f"  {status_icon} {test_name}: {result}")

        return passed == total

    def test_normal_migration(self) -> bool:
        """Test normal migration flow with typical settings."""
        # Setup test data
        test_settings = {
            "feature_flags": {"enable_analytics": True, "enable_caching": True, "enable_rate_limiting": False},
            "security_settings": {"session_timeout_hours": 24},
            "response_settings": {"default_max_tokens": 4000},
        }

        # Mock the settings in database
        for category, data in test_settings.items():
            admin_db_manager.set_admin_setting(category, json.dumps(data), 0)

        # Run migration
        migrator = SettingsMigrator()
        result = migrator.migrate_phase1_consolidation()

        if not result:
            return False

        # Validate migration occurred
        validation = migrator.validate_migration()
        return validation["status"] in ["success", "warning"]

    def test_missing_settings(self) -> bool:
        """Test migration with missing settings data."""
        # Clear settings to simulate missing data
        categories = ["feature_flags", "security_settings", "response_settings"]
        for category in categories:
            admin_db_manager.set_admin_setting(category, "", 0)  # Empty string for None

        migrator = SettingsMigrator()
        # Migration should handle missing data gracefully
        return migrator.migrate_phase1_consolidation()

    def test_corrupt_json(self) -> bool:
        """Test migration with corrupt JSON data."""
        # Set corrupt JSON data
        admin_db_manager.set_admin_setting("feature_flags", '{"invalid": json}', 0)
        admin_db_manager.set_admin_setting("security_settings", "not json at all", 0)

        migrator = SettingsMigrator()
        # Should handle corrupt data without crashing
        result = migrator.migrate_phase1_consolidation()

        # Even with corrupt data, migration should complete
        # (using defaults for corrupt settings)
        return result

    def test_large_payload(self) -> bool:
        """Test migration with large settings payload."""
        # Create large settings payload
        large_settings = {
            "feature_flags": {
                f"test_setting_{i}": f"value_{i}" * 100 for i in range(100)  # 100 settings with long values
            }
        }

        admin_db_manager.set_admin_setting("feature_flags", json.dumps(large_settings["feature_flags"]), 0)

        migrator = SettingsMigrator()
        return migrator.migrate_phase1_consolidation()

    def test_rollback_scenario(self) -> bool:
        """Test rollback functionality."""
        # Setup initial settings
        initial_settings = {
            "feature_flags": {"enable_analytics": True},
            "security_settings": {"enable_analytics": False},
        }

        for category, data in initial_settings.items():
            admin_db_manager.set_admin_setting(category, json.dumps(data), 0)

        migrator = SettingsMigrator()

        # Run migration to create backup
        if not migrator.migrate_phase1_consolidation():
            return False

        # Test rollback
        return migrator.rollback_migration()

    def test_partial_migration_failure(self) -> bool:
        """Test handling of partial migration failures."""
        # This would simulate database connection failure mid-migration
        # For now, we'll test that the migration handles exceptions gracefully

        migrator = SettingsMigrator()

        # Override a method to simulate failure
        migrator._save_migrated_settings_atomic

        def failing_save(*args, **kwargs):
            raise Exception("Simulated database failure")

        migrator._save_migrated_settings_atomic = failing_save

        # Migration should fail gracefully and attempt rollback
        result = migrator.migrate_phase1_consolidation()

        # Should return False due to simulated failure
        return not result  # We expect this to fail

    def test_backup_creation(self) -> bool:
        """Test backup creation and restoration."""
        test_data = {"system_config": {"test": "value"}}

        admin_db_manager.set_admin_setting("system_config", json.dumps(test_data["system_config"]), 0)

        migrator = SettingsMigrator()

        # Test backup creation
        if not migrator._create_backup():
            return False

        # Verify backup data exists
        if not migrator.backup_data:
            return False

        # Test restoration
        return migrator._restore_from_backup()


def main():
    """Main test runner."""
    if len(sys.argv) > 1 and sys.argv[1] == "--verbose":
        logging.getLogger().setLevel(logging.DEBUG)

    runner = MigrationTestRunner()
    success = runner.run_all_tests()

    if success:
        logger.info("✅ All migration tests passed!")
        return 0
    else:
        logger.error("❌ Some migration tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
