#!/usr/bin/env python3
"""
Infrastructure Settings Migration Script - Phase 3

This script migrates infrastructure-related settings from database to environment variables
for better deployment practices and Railway environment management.

Classification:
- ENV-ONLY: Settings that should only exist as environment variables
- ADMIN-MANAGED: Settings that remain in database but can be overridden by env vars

The script implements dry-run mode and doesn't change runtime precedence.
"""

import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from core.settings_manager import settings_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class InfraSettingsMigrator:
    """Migrates infrastructure settings from DB to environment variables."""

    # Settings that should ONLY exist as environment variables
    ENV_ONLY_SETTINGS = {
        # API Keys - security critical, should never be in DB
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        # Database configurations
        "DATABASE_URL",
        "REDIS_URL",
        # Application environment
        "ENVIRONMENT",
        "DEBUG",
        "LOG_LEVEL",
        # Railway-specific
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PROJECT_ID",
        "RAILWAY_SERVICE_ID",
    }

    # Settings that can exist in both DB and env (env takes precedence)
    ADMIN_MANAGED_SETTINGS = {
        # System Configuration
        "DEFAULT_LLM_MODEL": "system_config_settings.primary_llm",
        "RESPONSE_LLM": "system_config_settings.response_llm",
        "PROCESSING_LLM": "system_config_settings.processing_llm",
        "CLAUDE_MODEL": "system_config_settings.claude_model",
        "GEMINI_MODEL": "system_config_settings.gemini_model",
        "EMBEDDING_MODEL": "system_config_settings.embedding_model",
        # Performance settings
        "CACHE_TTL_SECONDS": "system_config_settings.system_cache_ttl_seconds",
        "MAX_CACHE_SIZE": "system_config_settings.max_cache_size",
        "RATE_LIMIT": "system_config_settings.rate_limit",
        # Security settings
        "SESSION_TIMEOUT_MINUTES": "security_settings.session_timeout_minutes",
        "MAX_LOGIN_ATTEMPTS": "security_settings.max_login_attempts",
        "LOCKOUT_DURATION": "security_settings.lockout_duration",
        "ENABLE_RATE_LIMITING": "security_settings.enable_rate_limiting",
        "RATE_LIMIT_REQUESTS": "security_settings.rate_limit_requests",
        "RATE_LIMIT_WINDOW": "security_settings.rate_limit_window",
        # Knowledge settings
        "INDEX_ON_STARTUP": "knowledge_settings.index_on_startup",
        "BACKGROUND_SYNC_INTERVAL": "knowledge_settings.background_sync_interval_seconds",
        "AUTO_REINDEX_DELTAS": "knowledge_settings.auto_reindex_deltas",
        "INDEX_DIRECTORIES": "knowledge_settings.index_directories",
    }

    def __init__(self, dry_run: bool = True):
        """Initialize migrator with dry-run mode."""
        self.dry_run = dry_run
        self.migration_log: List[str] = []
        self.current_env_vars: Dict[str, str] = {}
        self.proposed_env_vars: Dict[str, str] = {}
        self.db_settings: Dict[str, Any] = {}

    def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze current state of settings in DB and environment."""
        logger.info("Analyzing current settings state...")

        # Load current environment variables
        self.current_env_vars = dict(os.environ)

        # Load current DB settings
        self.db_settings = self._load_db_settings()

        analysis = {
            "env_vars_count": len(self.current_env_vars),
            "db_settings_count": len(self.db_settings),
            "env_only_missing": [],
            "admin_managed_in_db": [],
            "admin_managed_in_env": [],
            "conflicts": [],
        }

        # Check ENV_ONLY settings
        for env_key in self.ENV_ONLY_SETTINGS:
            if env_key not in self.current_env_vars:
                analysis["env_only_missing"].append(env_key)

        # Check ADMIN_MANAGED settings
        for env_key, db_path in self.ADMIN_MANAGED_SETTINGS.items():
            db_value = self._get_nested_value(self.db_settings, db_path)
            env_value = self.current_env_vars.get(env_key)

            if db_value is not None:
                analysis["admin_managed_in_db"].append({"env_key": env_key, "db_path": db_path, "db_value": db_value})

            if env_value is not None:
                analysis["admin_managed_in_env"].append({"env_key": env_key, "env_value": env_value})

            if db_value is not None and env_value is not None:
                if str(db_value) != str(env_value):
                    analysis["conflicts"].append(
                        {"env_key": env_key, "db_path": db_path, "db_value": db_value, "env_value": env_value}
                    )

        return analysis

    def _load_db_settings(self) -> Dict[str, Any]:
        """Load all relevant settings from database."""
        settings = {}

        try:
            # Load system configuration
            system_config = settings_manager.get_system_config_settings()
            settings["system_config_settings"] = asdict(system_config)

            # Load security settings
            security_settings = settings_manager.get_security_settings()
            settings["security_settings"] = asdict(security_settings)

            # Load knowledge settings
            knowledge_settings = settings_manager.get_knowledge_settings()
            settings["knowledge_settings"] = asdict(knowledge_settings)

            # Load core settings for API key status
            core_settings = settings_manager.get_core_settings()
            settings["core_settings"] = asdict(core_settings)

        except Exception as e:
            logger.error(f"Failed to load DB settings: {e}")

        return settings

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Optional[Any]:
        """Get nested value from dictionary using dot notation."""
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested value in dictionary using dot notation."""
        keys = path.split(".")
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def generate_env_migration_plan(self) -> Dict[str, Any]:
        """Generate plan for migrating settings to environment variables."""
        logger.info("Generating environment migration plan...")

        plan = {
            "proposed_migrations": [],
            "warnings": [],
            "manual_actions": [],
        }

        # For each ADMIN_MANAGED setting, propose env var if it has DB value
        for env_key, db_path in self.ADMIN_MANAGED_SETTINGS.items():
            db_value = self._get_nested_value(self.db_settings, db_path)
            env_value = self.current_env_vars.get(env_key)

            if db_value is not None and env_value is None:
                # Setting exists in DB but not in env - propose migration
                self.proposed_env_vars[env_key] = str(db_value)
                plan["proposed_migrations"].append(
                    {"env_key": env_key, "value": str(db_value), "source_db_path": db_path, "action": "migrate_from_db"}
                )
            elif db_value is not None and env_value is not None:
                if str(db_value) != str(env_value):
                    plan["warnings"].append(
                        {
                            "env_key": env_key,
                            "issue": "value_conflict",
                            "db_value": db_value,
                            "env_value": env_value,
                            "recommendation": "env_takes_precedence",
                        }
                    )

        # Check for missing ENV_ONLY settings
        for env_key in self.ENV_ONLY_SETTINGS:
            if env_key not in self.current_env_vars:
                plan["manual_actions"].append(
                    {"env_key": env_key, "action": "set_manually", "reason": "security_critical_or_deployment_specific"}
                )

        return plan

    def execute_migration(self, target_file: str = ".env.migration") -> bool:
        """Execute the migration by generating environment file."""
        logger.info(f"Executing migration (dry_run={self.dry_run})...")

        try:
            # Generate migration plan
            plan = self.generate_env_migration_plan()

            # Create env file content
            env_content = self._generate_env_file_content(plan)

            if self.dry_run:
                logger.info("DRY RUN: Would create environment file with following content:")
                logger.info(f"\n{env_content}")
                logger.info(f"File would be saved to: {target_file}")
                return True
            else:
                # Write env file
                with open(target_file, "w") as f:
                    f.write(env_content)
                logger.info(f"Environment migration file created: {target_file}")

                # Log migration summary
                self._log_migration_summary(plan)
                return True

        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            return False

    def _generate_env_file_content(self, plan: Dict[str, Any]) -> str:
        """Generate content for .env file based on migration plan."""
        lines = [
            "# Infrastructure Settings Migration - Phase 3",
            "# Generated environment variables from database settings",
            "# IMPORTANT: Review and validate before deploying",
            "",
            "# ============================================================",
            "# ADMIN-MANAGED SETTINGS (migrated from database)",
            "# These can be overridden here but remain configurable in admin UI",
            "# ============================================================",
            "",
        ]

        # Add migrated settings
        for migration in plan["proposed_migrations"]:
            env_key = migration["env_key"]
            value = migration["value"]
            source = migration["source_db_path"]

            lines.append(f"# Migrated from: {source}")
            lines.append(f"{env_key}={value}")
            lines.append("")

        # Add section for manual settings
        lines.extend(
            [
                "# ============================================================",
                "# ENV-ONLY SETTINGS (must be set manually)",
                "# These are security-critical and deployment-specific",
                "# ============================================================",
                "",
            ]
        )

        for action in plan["manual_actions"]:
            env_key = action["env_key"]
            reason = action["reason"]

            lines.append(f"# {reason}")
            lines.append(f"# {env_key}=your_value_here")
            lines.append("")

        # Add warnings section if any
        if plan["warnings"]:
            lines.extend(
                [
                    "# ============================================================",
                    "# WARNINGS - Manual Review Required",
                    "# ============================================================",
                    "",
                ]
            )

            for warning in plan["warnings"]:
                env_key = warning["env_key"]
                warning["issue"]
                db_val = warning["db_value"]
                env_val = warning["env_value"]

                lines.append(f"# WARNING: {env_key} has conflicting values")
                lines.append(f"# Database value: {db_val}")
                lines.append(f"# Current env value: {env_val}")
                lines.append(f"# Resolution: Environment takes precedence")
                lines.append("")

        return "\n".join(lines)

    def _log_migration_summary(self, plan: Dict[str, Any]) -> None:
        """Log summary of migration execution."""
        total_migrations = len(plan["proposed_migrations"])
        total_warnings = len(plan["warnings"])
        total_manual = len(plan["manual_actions"])

        logger.info(f"Migration Summary:")
        logger.info(f"  - Settings migrated to env: {total_migrations}")
        logger.info(f"  - Warnings (conflicts): {total_warnings}")
        logger.info(f"  - Manual actions required: {total_manual}")

        if total_warnings > 0:
            logger.warning("Review warnings for conflicting values!")

        if total_manual > 0:
            logger.info("Remember to set ENV-ONLY settings manually for security")

    def validate_migration(self) -> Tuple[bool, List[str]]:
        """Validate that migration results are correct."""
        errors = []

        try:
            # Re-analyze state after migration
            analysis = self.analyze_current_state()

            # Check that critical env vars are not missing
            critical_missing = [
                env_key for env_key in ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"] if env_key not in self.current_env_vars
            ]

            if critical_missing:
                errors.append(f"Critical API keys missing: {critical_missing}")

            # Check for unresolved conflicts
            if analysis["conflicts"]:
                errors.append(f"Unresolved conflicts: {len(analysis['conflicts'])}")

            is_valid = len(errors) == 0
            return is_valid, errors

        except Exception as e:
            errors.append(f"Validation failed: {e}")
            return False, errors

    def backup_current_settings(self) -> str:
        """Create backup of current settings before migration."""
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"settings_backup_{timestamp}.json"

        backup_data = {
            "timestamp": timestamp,
            "migration_type": "phase3_infra_migration",
            "current_env_vars": {
                k: v
                for k, v in self.current_env_vars.items()
                if k in self.ENV_ONLY_SETTINGS or k in self.ADMIN_MANAGED_SETTINGS
            },
            "db_settings": self.db_settings,
        }

        if self.dry_run:
            logger.info(f"DRY RUN: Would create backup file: {backup_file}")
        else:
            with open(backup_file, "w") as f:
                json.dump(backup_data, f, indent=2, default=str)
            logger.info(f"Settings backup created: {backup_file}")

        return backup_file

    def rollback_migration(self, backup_file: str) -> bool:
        """
        Rollback migration using a backup file.

        This restores database settings from the backup and removes the migration env file.
        """
        try:
            if not os.path.exists(backup_file):
                logger.error(f"Backup file not found: {backup_file}")
                return False

            logger.info(f"Rolling back migration using backup: {backup_file}")

            # Import schema classes needed for restoration
            from core.settings_schemas import (
                CoreSettings,
                KnowledgeSettings,
                SecuritySettings,
                SystemConfigurationSettings,
            )

            # Load backup data
            with open(backup_file, "r") as f:
                backup_data = json.load(f)

            if self.dry_run:
                logger.info("DRY RUN: Would restore the following settings:")
                logger.info(f"Database settings: {len(backup_data.get('db_settings', {}))}")
                logger.info(f"Environment variables: {len(backup_data.get('current_env_vars', {}))}")
                return True

            # Restore database settings
            restored_count = 0
            for setting_type, settings_data in backup_data.get("db_settings", {}).items():
                if settings_data:
                    try:
                        # Map setting types to their schema classes and manager methods
                        settings_mapping = {
                            "system_config_settings": (
                                SystemConfigurationSettings,
                                settings_manager.set_system_config_settings,
                            ),
                            "security_settings": (SecuritySettings, settings_manager.set_security_settings),
                            "knowledge_settings": (KnowledgeSettings, settings_manager.set_knowledge_settings),
                            "core_settings": (CoreSettings, settings_manager.set_core_settings),
                        }

                        if setting_type in settings_mapping:
                            schema_class, setter_method = settings_mapping[setting_type]

                            # Reconstruct the settings object from backup data
                            restored_settings = schema_class(**settings_data)

                            # Save to database (updated_by=0 indicates system restoration)
                            success = setter_method(restored_settings, updated_by=0)

                            if success:
                                logger.info(f"✅ Restored {setting_type}: {len(settings_data)} settings")
                                restored_count += 1
                            else:
                                logger.error(f"❌ Failed to save {setting_type} to database")
                        else:
                            logger.warning(f"⚠️  Unknown setting type: {setting_type} - skipping")

                    except Exception as e:
                        logger.error(f"❌ Failed to restore {setting_type}: {e}")

            # Remove migration env file if it exists
            migration_files = [".env.migration", "env.migration"]
            for env_file in migration_files:
                if os.path.exists(env_file):
                    try:
                        os.remove(env_file)
                        logger.info(f"Removed migration file: {env_file}")
                    except Exception as e:
                        logger.warning(f"Failed to remove {env_file}: {e}")

            logger.info(f"Rollback completed. Restored {restored_count} setting categories.")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False


def main():
    """Main function to run infrastructure settings migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate infrastructure settings from DB to env vars")
    parser.add_argument("--execute", action="store_true", help="Execute migration (default: dry-run)")
    parser.add_argument("--output", default=".env.migration", help="Output env file path")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze current state")
    parser.add_argument("--rollback", help="Rollback migration using specified backup file")
    parser.add_argument("--list-backups", action="store_true", help="List available backup files")

    args = parser.parse_args()

    # Initialize migrator
    migrator = InfraSettingsMigrator(dry_run=not args.execute)

    try:
        # Handle special operations first
        if args.list_backups:
            # List available backup files
            backup_files = [f for f in os.listdir(".") if f.startswith("settings_backup_") and f.endswith(".json")]
            if backup_files:
                print("\n=== AVAILABLE BACKUP FILES ===")
                for backup in sorted(backup_files, reverse=True):
                    print(f"  {backup}")
            else:
                print("No backup files found in current directory.")
            return

        if args.rollback:
            # Perform rollback
            print(f"\n=== ROLLBACK MIGRATION ===")
            success = migrator.rollback_migration(args.rollback)
            if success:
                print(f"✅ Rollback completed successfully!")
            else:
                print(f"❌ Rollback failed!")
                sys.exit(1)
            return

        # Create backup for regular operations
        backup_file = migrator.backup_current_settings()

        if args.analyze_only:
            # Just analyze and report
            analysis = migrator.analyze_current_state()
            print("\n=== CURRENT STATE ANALYSIS ===")
            print(f"Environment variables: {analysis['env_vars_count']}")
            print(f"Database settings loaded: {analysis['db_settings_count']}")
            print(f"Missing ENV-ONLY settings: {len(analysis['env_only_missing'])}")
            print(f"Admin-managed in DB: {len(analysis['admin_managed_in_db'])}")
            print(f"Admin-managed in ENV: {len(analysis['admin_managed_in_env'])}")
            print(f"Conflicts detected: {len(analysis['conflicts'])}")

            if analysis["env_only_missing"]:
                print(f"\nMissing critical env vars: {analysis['env_only_missing']}")

            if analysis["conflicts"]:
                print(f"\nConflicts found:")
                for conflict in analysis["conflicts"]:
                    print(f"  {conflict['env_key']}: DB='{conflict['db_value']}' vs ENV='{conflict['env_value']}'")
        else:
            # Execute migration
            success = migrator.execute_migration(args.output)

            if success:
                # Validate results
                is_valid, errors = migrator.validate_migration()

                if is_valid:
                    print(f"\n✅ Migration completed successfully!")
                    if migrator.dry_run:
                        print(f"🔍 DRY RUN: Review the proposed changes above")
                        print(f"📁 Run with --execute to create {args.output}")
                    else:
                        print(f"📁 Environment file created: {args.output}")
                        print(f"💾 Backup saved: {backup_file}")
                else:
                    print(f"\n⚠️  Migration completed with warnings:")
                    for error in errors:
                        print(f"  - {error}")
            else:
                print(f"\n❌ Migration failed!")
                sys.exit(1)

    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
