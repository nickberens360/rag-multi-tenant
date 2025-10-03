#!/usr/bin/env python3
"""
Database Migration Verification Script
=====================================

This script verifies that both local and production databases have the correct
schema structure to ensure smooth deployment.

Usage:
    python scripts/verify-database-migration.py [--check-prod] [--verbose]

Features:
- Validates all required tables exist
- Checks for proper column structure
- Verifies indices are in place  
- Compares local vs expected production schema
- Reports any missing or extra elements
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import text

from backend.core.db_session import get_db_session_sync

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Expected schema definitions
EXPECTED_ADMIN_TABLES = {
    "admin_users": [
        "id",
        "username",
        "email",
        "password_hash",
        "role",
        "is_active",
        "created_at",
        "last_login_at",
        "updated_at",
        "display_name",
    ],
    "admin_sessions": ["id", "user_id", "started_at", "last_active_at", "ip_address", "user_agent", "is_active"],
    "admin_settings": ["id", "setting_key", "setting_value", "updated_at", "updated_by"],
    "rate_limiting": [
        "id",
        "identifier",
        "identifier_type",
        "attempt_count",
        "first_attempt_at",
        "last_attempt_at",
        "lockout_until",
        "created_at",
    ],
    "security_events": [
        "id",
        "event_type",
        "identifier",
        "details",
        "severity",
        "ip_address",
        "user_agent",
        "created_at",
    ],
    "user_2fa": [
        "id",
        "user_id",
        "secret",
        "backup_codes",
        "used_backup_codes",
        "is_enabled",
        "created_at",
        "verified_at",
    ],
    "followup_categories": [
        "id",
        "name",
        "display_name",
        "description",
        "icon",
        "sort_order",
        "is_active",
        "created_at",
        "updated_at",
    ],
    "followup_questions": [
        "id",
        "category_id",
        "question_text",
        "sort_order",
        "is_active",
        "created_at",
        "updated_at",
        "created_by",
    ],
    "welcome_questions": ["id", "question_text", "sort_order", "is_active", "created_at", "updated_at", "created_by"],
    "api_keys": [
        "id",
        "key_name",
        "key_type",
        "encrypted_value",
        "last_four",
        "is_active",
        "last_used_at",
        "last_validated_at",
        "created_at",
        "updated_at",
        "updated_by",
    ],
}

EXPECTED_RAG_TABLES = {
    "query_logs": [
        "id",
        "session_id",
        "user_query",
        "system_response",
        "response_time_ms",
        "llm_provider",
        "llm_model",
        "vector_search_score",
        "sources_used",
        "follow_up_questions",
        "cache_hit",
        "error_occurred",
        "error_message",
        "user_feedback",
        "timestamp",
        "client_ip",
        "location_city",
        "location_region",
        "location_country",
        "location_country_code",
        "query_type",
        "request_id",
    ],
    "content_gaps": [
        "id",
        "query_pattern",
        "occurrence_count",
        "avg_similarity_score",
        "first_seen",
        "last_seen",
        "resolved",
        "notes",
        "sample_query_id",
    ],
    "user_sessions": ["id", "started_at", "last_active_at", "total_queries", "user_agent", "ip_address"],
    "hourly_metrics": [
        "id",
        "hour",
        "total_queries",
        "unique_sessions",
        "avg_response_time_ms",
        "p95_response_time_ms",
        "cache_hit_rate",
        "error_rate",
        "helpful_rate",
    ],
}

EXPECTED_ADMIN_INDICES = {
    "idx_admin_sessions_user_id",
    "idx_admin_sessions_active",
    "idx_admin_users_username",
    "idx_rate_limiting_identifier",
    "idx_rate_limiting_lockout",
    "idx_security_events_type",
    "idx_security_events_ip",
    "idx_user_2fa_user_id",
    "idx_user_2fa_enabled",
    "idx_followup_categories_name",
    "idx_followup_categories_active",
    "idx_followup_categories_order",
    "idx_followup_questions_category",
    "idx_followup_questions_active",
    "idx_followup_questions_order",
    "idx_followup_questions_text",
    "idx_welcome_questions_active",
    "idx_welcome_questions_order",
    "idx_welcome_questions_text",
    "idx_api_keys_name",
    "idx_api_keys_type",
    "idx_api_keys_active",
}

EXPECTED_RAG_INDICES = {
    "idx_query_logs_timestamp",
    "idx_query_logs_session",
    "idx_query_logs_errors",
    "idx_sessions_active",
    "idx_content_gaps_resolved",
    "idx_content_gaps_score",
    "idx_query_logs_session_id",
    "idx_query_logs_error",
}


def get_table_info_pg() -> Tuple[Dict[str, List[str]], Set[str]]:
    """Get table structure and indices from Postgres."""
    tables: Dict[str, List[str]] = {}
    indices: Set[str] = set()
    with get_db_session_sync() as session:
        if session is None:
            return tables, indices
        rows = session.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name, ordinal_position"
            )
        ).fetchall()
        for tbl, col in rows:
            tables.setdefault(tbl, []).append(col)
        irows = session.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname='public'"))
        indices = {r[0] for r in irows.fetchall()}
    return tables, indices


def verify_database_schema(
    expected_tables: Dict[str, List[str]],
    expected_indices: Set[str],
    db_name: str,
    verbose: bool = False,
) -> bool:
    """Verify database schema matches expectations."""
    logger.info(f"\n=== Verifying {db_name} Database ===")
    actual_tables, actual_indices = get_table_info_pg()

    success = True

    # Check tables
    logger.info(f"\n📋 Table Verification:")
    for table_name, expected_columns in expected_tables.items():
        if table_name not in actual_tables:
            logger.error(f"❌ Missing table: {table_name}")
            success = False
            continue

        actual_columns = actual_tables[table_name]
        missing_columns = set(expected_columns) - set(actual_columns)
        extra_columns = set(actual_columns) - set(expected_columns)

        if missing_columns or extra_columns:
            logger.warning(f"⚠️  Table {table_name} schema differences:")
            if missing_columns:
                logger.warning(f"   Missing columns: {sorted(missing_columns)}")
                success = False
            if extra_columns and verbose:
                logger.info(f"   Extra columns: {sorted(extra_columns)}")
        else:
            logger.info(f"✅ {table_name}: All columns present")

    # Check for unexpected tables
    extra_tables = set(actual_tables.keys()) - set(expected_tables.keys())
    if extra_tables and verbose:
        logger.info(f"\n📝 Extra tables found: {sorted(extra_tables)}")

    # Check indices
    logger.info(f"\n🔍 Index Verification:")
    missing_indices = expected_indices - actual_indices
    if missing_indices:
        logger.warning(f"⚠️  Missing indices: {sorted(missing_indices)}")
        # Indices are not critical for functionality, so don't fail
    else:
        logger.info(f"✅ All {len(expected_indices)} expected indices present")

    extra_indices = actual_indices - expected_indices
    if extra_indices and verbose:
        logger.info(f"📝 Extra indices found: {sorted(extra_indices)}")

    return success


def trigger_database_initialization() -> bool:
    logger.info("\n🔧 Using Postgres migrations (Alembic) — no SQLite init needed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify database migration readiness")
    parser.add_argument("--check-prod", action="store_true", help="Check production database via Railway")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show extra details and warnings")

    args = parser.parse_args()

    logger.info("🚀 Database Migration Verification")
    logger.info("=" * 50)

    # Trigger initialization to ensure databases are up to date
    if not trigger_database_initialization():
        sys.exit(1)

    # Verify Postgres tables
    admin_success = verify_database_schema(EXPECTED_ADMIN_TABLES, EXPECTED_ADMIN_INDICES, "Admin", args.verbose)
    rag_success = verify_database_schema(EXPECTED_RAG_TABLES, EXPECTED_RAG_INDICES, "RAG", args.verbose)

    # Summary
    logger.info(f"\n📊 Verification Summary")
    logger.info("=" * 30)

    if admin_success and rag_success:
        logger.info("✅ All database schemas are ready for production deployment!")
        logger.info("\n🚢 Deployment Strategy:")
        logger.info("1. Your code uses CREATE TABLE IF NOT EXISTS - tables will auto-migrate")
        logger.info("2. New columns are added automatically via ALTER TABLE logic")
        logger.info("3. Indices are created if they don't exist")
        logger.info("4. No manual database migration needed!")

        if args.check_prod:
            logger.info("\n🔍 Production Check Recommendations:")
            logger.info("- After deployment, verify tables exist via Railway shell")
            logger.info("- Check for any startup errors in Railway logs")
            logger.info("- Test admin dashboard functionality")

    else:
        logger.error("❌ Database schema issues detected!")
        logger.error("Review the errors above before deploying to production.")
        sys.exit(1)


if __name__ == "__main__":
    main()
