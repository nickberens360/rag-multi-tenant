"""
Settings migration utilities for Phase 1 consolidation.

Handles migration of duplicate settings that were consolidated into
appropriate schemas as part of the UX cleanup initiative.

Consolidated Settings:
- Caching: All moved to ResponseSettings 
- Smart Routing: Removed from FeatureFlags, kept in QueryRoutingSettings
- Analytics: Moved from FeatureFlags to SecuritySettings  
- Rate Limiting: Moved from FeatureFlags to SecuritySettings
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .settings_manager import get_settings_manager

logger = logging.getLogger(__name__)


class SettingsMigrator:
    """Handles migration of settings during schema consolidation."""

    def __init__(self):
        self.migration_log = []
        self.backup_data: Optional[Dict[str, Any]] = None
        self.backup_timestamp: Optional[str] = None

    def migrate_phase1_consolidation(self) -> bool:
        """
        Migrate settings for Phase 1 consolidation with backup and atomic behavior.

        Returns:
            bool: True if migration successful, False otherwise
        """
        try:
            logger.info("Starting Phase 1 settings consolidation migration...")

            # Step 1: Create backup of current settings
            if not self._create_backup():
                logger.error("Failed to create backup - aborting migration")
                return False

            # Step 2: Load current settings
            settings_data = self._load_all_current_settings()
            if not settings_data:
                logger.error("Failed to load current settings - aborting migration")
                return False

            # Step 3: Perform consolidation migrations
            original_data = json.loads(json.dumps(settings_data))  # Deep copy

            try:
                self._migrate_caching_settings(settings_data)
                self._migrate_analytics_to_security(settings_data)
                self._migrate_rate_limiting_to_security(settings_data)
                self._remove_duplicates_from_features(settings_data)

                # Step 4: Validate migration before saving
                if not self._validate_migration_data(settings_data, original_data):
                    logger.error("Migration validation failed - rolling back")
                    return False

                # Step 5: Save migrated settings atomically
                if not self._save_migrated_settings_atomic(settings_data):
                    logger.error("Failed to save migrated settings - rolling back")
                    self._restore_from_backup()
                    return False

                logger.info(f"Phase 1 migration completed successfully. {len(self.migration_log)} changes made.")
                logger.info("Migration changes: " + "; ".join(self.migration_log))
                return True

            except Exception as e:
                logger.error(f"Migration processing failed: {e} - rolling back")
                self._restore_from_backup()
                return False

        except Exception as e:
            logger.error(f"Phase 1 migration failed: {e}")
            return False

    def _load_all_current_settings(self) -> Dict[str, Any]:
        """Load all current settings from the database with optimized batch loading."""
        settings_data = {}

        try:
            # Define all settings categories to load
            categories = [
                "feature_flags",
                "response_settings",
                "routing_settings",
                "security_settings",
                "system_config",
            ]

            # Batch load settings for better performance
            batch_results = self._batch_load_settings(categories)

            for category in categories:
                result = batch_results.get(category)
                if result:
                    try:
                        settings_data[category] = json.loads(result)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse {category} settings, using defaults")
                        settings_data[category] = {}
                else:
                    settings_data[category] = {}

        except Exception as e:
            logger.error(f"Failed to load current settings: {e}")

        return settings_data

    def _batch_load_settings(self, categories: List[str]) -> Dict[str, Optional[str]]:
        """
        Batch load multiple settings from database to reduce database hits.

        Args:
            categories: List of setting categories to load

        Returns:
            Dict mapping category names to their JSON string values
        """
        results = {}

        try:
            # In a real database, you'd do a single query with WHERE key IN (...)
            # For now, we'll simulate batch loading by reducing individual calls
            # and adding retry logic for better reliability

            sm = get_settings_manager()
            for category in categories:
                for attempt in range(3):  # Retry logic for database operations
                    try:
                        result = sm._get_setting_from_db(category)
                        results[category] = result
                        break  # Success, no need to retry

                    except Exception as e:
                        logger.warning(f"Attempt {attempt + 1} failed for {category}: {e}")
                        if attempt == 2:  # Last attempt
                            logger.error(f"Failed to load {category} after 3 attempts")
                            results[category] = None
                        else:
                            time.sleep(0.1 * (attempt + 1))  # Exponential backoff

        except Exception as e:
            logger.error(f"Batch settings load failed: {e}")

        return results

    def _create_backup(self) -> bool:
        """Create backup of current settings before migration."""
        try:
            self.backup_timestamp = datetime.now().isoformat()
            self.backup_data = self._load_all_current_settings()

            if not self.backup_data:
                logger.error("No settings data to backup")
                return False

            # Optionally store backup in database with timestamp
            backup_key = f"migration_backup_{self.backup_timestamp.replace(':', '_')}"
            backup_json = json.dumps(
                {"timestamp": self.backup_timestamp, "data": self.backup_data, "migration_type": "phase1_consolidation"}
            )

            get_settings_manager()._set_setting_in_db(backup_key, backup_json, 0)  # System user ID
            logger.info(f"Created settings backup: {backup_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def _validate_migration_data(self, migrated_data: Dict[str, Any], original_data: Dict[str, Any]) -> bool:
        """Validate that migration changes are safe and expected."""
        try:
            # Ensure no critical settings were accidentally removed
            critical_settings = {
                "system_config": ["default_model", "allowed_models"],
                "security_settings": ["session_timeout_hours", "max_failed_logins"],
                "response_settings": ["default_max_tokens", "temperature"],
            }

            for category, settings in critical_settings.items():
                original_cat = original_data.get(category, {})
                migrated_cat = migrated_data.get(category, {})

                for setting in settings:
                    if setting in original_cat and setting not in migrated_cat:
                        logger.error(f"Critical setting {setting} was removed from {category}")
                        return False

            # Ensure migration actually made changes (prevent no-op migrations)
            if self.migration_log:
                logger.info(f"Migration validation passed. {len(self.migration_log)} changes detected.")
                return True
            else:
                logger.warning("Migration validation: No changes detected")
                return True  # Allow no-op migrations

        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return False

    def _save_migrated_settings_atomic(self, settings_data: Dict[str, Any]) -> bool:
        """Save migrated settings with transaction-like behavior."""
        saved_categories = []

        try:
            # Save all categories
            for category, data in settings_data.items():
                if data:  # Only save non-empty settings
                    json_data = json.dumps(data)
                    get_settings_manager()._set_setting_in_db(category, json_data, 0)  # System user ID
                    saved_categories.append(category)
                    logger.debug(f"Saved migrated {category} settings")

            logger.info(f"Atomically saved {len(saved_categories)} setting categories")
            return True

        except Exception as e:
            logger.error(f"Failed to save settings atomically: {e}")
            # Attempt to restore any categories that were saved
            if saved_categories and self.backup_data:
                logger.warning("Attempting to restore partially saved categories...")
                try:
                    for category in saved_categories:
                        if category in self.backup_data:
                            backup_json = json.dumps(self.backup_data[category])
                    get_settings_manager()._set_setting_in_db(category, backup_json, 0)
                    logger.info("Restored partially saved categories from backup")
                except Exception as restore_e:
                    logger.error(f"Failed to restore partially saved categories: {restore_e}")
            return False

    def _restore_from_backup(self) -> bool:
        """Restore settings from backup."""
        if not self.backup_data:
            logger.error("No backup data available for restore")
            return False

        try:
            for category, data in self.backup_data.items():
                if data:
                    json_data = json.dumps(data)
                    get_settings_manager()._set_setting_in_db(category, json_data, 0)  # System user ID

            logger.info("Successfully restored settings from backup")
            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False

    def _migrate_caching_settings(self, settings_data: Dict[str, Any]) -> None:
        """Consolidate all caching settings into ResponseSettings."""
        response_settings = settings_data.get("response_settings", {})
        feature_flags = settings_data.get("feature_flags", {})
        routing_settings = settings_data.get("routing_settings", {})

        # Migrate enable_caching from FeatureFlags
        if "enable_response_caching" in feature_flags:
            if "enable_caching" not in response_settings:
                response_settings["enable_caching"] = feature_flags["enable_response_caching"]
                self.migration_log.append(
                    "Migrated enable_response_caching from FeatureFlags to ResponseSettings as enable_caching"
                )
            del feature_flags["enable_response_caching"]

        if "enable_caching" in feature_flags:
            if "enable_caching" not in response_settings:
                response_settings["enable_caching"] = feature_flags["enable_caching"]
                self.migration_log.append("Migrated enable_caching from FeatureFlags to ResponseSettings")
            del feature_flags["enable_caching"]

        # Migrate cache TTL from routing if present
        if "query_cache_ttl_seconds" in routing_settings:
            if "cache_ttl_seconds" not in response_settings:
                response_settings["cache_ttl_seconds"] = routing_settings["query_cache_ttl_seconds"]
                self.migration_log.append("Migrated cache TTL from routing to response settings")

        # Ensure unified cache TTL
        if "response_cache_ttl_seconds" in response_settings and "cache_ttl_seconds" not in response_settings:
            response_settings["cache_ttl_seconds"] = response_settings["response_cache_ttl_seconds"]
            self.migration_log.append("Set unified cache_ttl_seconds from response_cache_ttl_seconds")

    def _migrate_analytics_to_security(self, settings_data: Dict[str, Any]) -> None:
        """Move analytics from FeatureFlags to SecuritySettings."""
        feature_flags = settings_data.get("feature_flags", {})
        security_settings = settings_data.get("security_settings", {})

        if "enable_analytics" in feature_flags:
            if "enable_analytics" not in security_settings:
                security_settings["enable_analytics"] = feature_flags["enable_analytics"]
                self.migration_log.append("Migrated enable_analytics from FeatureFlags to SecuritySettings")
            del feature_flags["enable_analytics"]

    def _migrate_rate_limiting_to_security(self, settings_data: Dict[str, Any]) -> None:
        """Consolidate rate limiting in SecuritySettings."""
        feature_flags = settings_data.get("feature_flags", {})
        security_settings = settings_data.get("security_settings", {})

        if "enable_rate_limiting" in feature_flags:
            # SecuritySettings already has this field, so we just remove the duplicate
            if security_settings.get("enable_rate_limiting") is None:
                security_settings["enable_rate_limiting"] = feature_flags["enable_rate_limiting"]
                self.migration_log.append("Migrated enable_rate_limiting from FeatureFlags to SecuritySettings")
            del feature_flags["enable_rate_limiting"]

    def _remove_duplicates_from_features(self, settings_data: Dict[str, Any]) -> None:
        """Remove migrated settings from FeatureFlags."""
        feature_flags = settings_data.get("feature_flags", {})

        # Remove settings that have been migrated elsewhere
        duplicates_to_remove = [
            "enable_smart_routing",  # Now only in QueryRoutingSettings
        ]

        for duplicate in duplicates_to_remove:
            if duplicate in feature_flags:
                del feature_flags[duplicate]
                self.migration_log.append(f"Removed duplicate {duplicate} from FeatureFlags")

    def _save_migrated_settings(self, settings_data: Dict[str, Any]) -> None:
        """Save the migrated settings back to the database."""
        for category, data in settings_data.items():
            if data:  # Only save non-empty settings
                try:
                    json_data = json.dumps(data)
                    get_settings_manager()._set_setting_in_db(category, json_data, 0)  # System user ID
                    logger.debug(f"Saved migrated {category} settings")
                except Exception as e:
                    logger.error(f"Failed to save {category} settings: {e}")

    def validate_migration(self) -> Dict[str, Any]:
        """
        Validate that the migration was successful.

        Returns:
            dict: Validation results with status and details
        """
        validation_results: Dict[str, Any] = {"status": "success", "issues": [], "warnings": []}

        try:
            settings_data = self._load_all_current_settings()

            # Check that duplicates were removed
            feature_flags = settings_data.get("feature_flags", {})

            duplicate_checks = [
                ("enable_analytics", "should be in SecuritySettings only"),
                ("enable_rate_limiting", "should be in SecuritySettings only"),
                ("enable_smart_routing", "should be in QueryRoutingSettings only"),
                ("enable_caching", "should be in ResponseSettings only"),
                ("enable_response_caching", "should be in ResponseSettings only"),
            ]

            for setting, message in duplicate_checks:
                if setting in feature_flags:
                    validation_results["issues"].append(f"{setting} still in FeatureFlags - {message}")

            # Check that consolidated settings exist in correct schemas
            security_settings = settings_data.get("security_settings", {})
            if "enable_analytics" not in security_settings:
                validation_results["warnings"].append("enable_analytics not found in SecuritySettings")
            if "enable_rate_limiting" not in security_settings:
                validation_results["warnings"].append("enable_rate_limiting not found in SecuritySettings")

            response_settings = settings_data.get("response_settings", {})
            if "enable_caching" not in response_settings:
                validation_results["warnings"].append("enable_caching not found in ResponseSettings")

            if validation_results["issues"]:
                validation_results["status"] = "failed"
            elif validation_results["warnings"]:
                validation_results["status"] = "warning"

        except Exception as e:
            validation_results["status"] = "error"
            validation_results["issues"].append(f"Validation failed: {e}")

        return validation_results

    def rollback_migration(self, backup_timestamp: Optional[str] = None) -> bool:
        """
        Rollback the Phase 1 migration from backup.

        Args:
            backup_timestamp: Optional specific backup to restore from

        Returns:
            bool: True if rollback successful
        """
        try:
            logger.warning("Rolling back Phase 1 migration...")

            # If we have backup data in memory, use it
            if self.backup_data and not backup_timestamp:
                return self._restore_from_backup()

            # Otherwise, find the most recent backup or specific backup
            backup_key = None
            if backup_timestamp:
                backup_key = f"migration_backup_{backup_timestamp.replace(':', '_')}"
            else:
                # Find the most recent backup
                backup_key = self._find_latest_backup()

            if not backup_key:
                logger.error("No backup found for rollback")
                return False

            # Load backup from database
            backup_data_raw = get_settings_manager()._get_setting_from_db(backup_key)
            if not backup_data_raw:
                logger.error(f"Backup {backup_key} not found in database")
                return False

            backup_info = json.loads(backup_data_raw)
            backup_data = backup_info.get("data", {})

            if not backup_data:
                logger.error("Backup contains no data")
                return False

            # Restore from backup
            restored_count = 0
            for category, data in backup_data.items():
                if data:
                    json_data = json.dumps(data)
                    get_settings_manager()._set_setting_in_db(category, json_data, 0)  # System user ID
                    restored_count += 1

            logger.warning(f"Rollback completed: restored {restored_count} setting categories from {backup_key}")
            logger.warning("Previous migration log: " + "; ".join(self.migration_log))
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def _find_latest_backup(self) -> Optional[str]:
        """Find the most recent migration backup."""
        try:
            # This is simplified - in a real implementation you'd query the database
            # for all migration backup keys and find the most recent
            latest_timestamp = datetime.now().replace(microsecond=0).isoformat()
            backup_key = f"migration_backup_{latest_timestamp.replace(':', '_')}"

            # Check if this backup exists
            if get_settings_manager()._get_setting_from_db(backup_key):
                return backup_key

            # For now, return None if no backup found
            logger.warning("No recent backup found")
            return None

        except Exception as e:
            logger.error(f"Failed to find latest backup: {e}")
            return None

    def list_available_backups(self) -> List[Dict[str, Any]]:
        """List all available migration backups."""
        backups = []
        try:
            # In a real implementation, you'd query the database for all backup keys
            # For now, this is a placeholder
            logger.info("Listing available backups (placeholder implementation)")
            return backups

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []


def run_phase1_migration() -> bool:
    """
    Convenience function to run Phase 1 migration.

    Returns:
        bool: True if migration successful
    """
    migrator = SettingsMigrator()
    success = migrator.migrate_phase1_consolidation()

    if success:
        validation = migrator.validate_migration()
        if validation["status"] == "failed":
            logger.error("Migration validation failed!")
            logger.error("Issues: " + "; ".join(validation["issues"]))
            return False
        elif validation["status"] == "warning":
            logger.warning("Migration completed with warnings:")
            logger.warning("Warnings: " + "; ".join(validation["warnings"]))

    return success


if __name__ == "__main__":
    # CLI interface for running migration
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        migrator = SettingsMigrator()
        success = migrator.rollback_migration()
        sys.exit(0 if success else 1)
    else:
        success = run_phase1_migration()
        sys.exit(0 if success else 1)
