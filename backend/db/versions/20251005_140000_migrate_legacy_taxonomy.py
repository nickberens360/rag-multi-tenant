"""Migrate data from admin_settings.taxonomy_settings to tenant_taxonomy

Revision ID: migrate_legacy_taxonomy
Revises: add_taxonomy_regex
Create Date: 2025-10-05

This migration consolidates the dual taxonomy system:
- Legacy System: admin_settings table (key: 'taxonomy_settings') + topic_taxonomy.json
- New System: tenant_taxonomy table (unified source of truth)

The migration:
1. Reads taxonomy data from admin_settings.taxonomy_settings
2. Extracts regex patterns and synonyms for each category
3. Updates existing tenant_taxonomy entries with regex patterns
4. Inserts new entries if they don't exist yet
5. Preserves all existing data and merges synonyms

After this migration, content_router.py can switch to database-driven taxonomy.
"""

import json

from alembic import op
from sqlalchemy import text

revision = "migrate_legacy_taxonomy"
down_revision = "add_taxonomy_regex"
branch_labels = None
depends_on = None


def upgrade():
    """
    Migrate legacy taxonomy from admin_settings to tenant_taxonomy.

    This consolidates the dual taxonomy system into a single source of truth.
    """

    conn = op.get_bind()

    # Read legacy taxonomy from admin_settings
    result = conn.execute(
        text(
            """
            SELECT tenant_id, setting_value
            FROM admin_settings
            WHERE setting_key = 'taxonomy_settings'
            """
        )
    )

    for row in result:
        tenant_id = row[0]
        taxonomy_json = row[1]

        try:
            taxonomy_data = json.loads(taxonomy_json)
            categories = taxonomy_data.get("categories", {})

            for category_key, category_data in categories.items():
                # Extract synonyms and regex patterns from legacy data
                synonyms = category_data.get("synonyms", [])
                regex_patterns = category_data.get("regex", [])

                # Check if entry already exists in tenant_taxonomy
                existing = conn.execute(
                    text(
                        """
                        SELECT synonyms, regex FROM tenant_taxonomy
                        WHERE tenant_id = :tid AND key = :key
                        """
                    ),
                    {"tid": tenant_id, "key": category_key},
                ).fetchone()

                if existing:
                    # Merge synonyms: combine existing + new, deduplicate
                    existing_synonyms = existing[0] if existing[0] else []
                    existing_regex = existing[1] if existing[1] else []

                    # Combine and deduplicate synonyms
                    merged_synonyms = list(set(existing_synonyms + synonyms))

                    # Combine and deduplicate regex patterns
                    merged_regex = list(set(existing_regex + regex_patterns))

                    # Update existing entry with merged data
                    conn.execute(
                        text(
                            """
                            UPDATE tenant_taxonomy
                            SET regex = :regex::jsonb,
                                synonyms = :synonyms::jsonb
                            WHERE tenant_id = :tid AND key = :key
                            """
                        ),
                        {
                            "tid": tenant_id,
                            "key": category_key,
                            "regex": json.dumps(merged_regex),
                            "synonyms": json.dumps(merged_synonyms),
                        },
                    )
                else:
                    # Insert new entry from legacy data
                    # Generate a label by converting key to Title Case
                    label = category_key.replace("_", " ").replace("-", " ").title()

                    conn.execute(
                        text(
                            """
                            INSERT INTO tenant_taxonomy
                              (tenant_id, key, label, synonyms, regex, active)
                            VALUES
                              (:tid, :key, :label, :synonyms::jsonb, :regex::jsonb, true)
                            """
                        ),
                        {
                            "tid": tenant_id,
                            "key": category_key,
                            "label": label,
                            "synonyms": json.dumps(synonyms),
                            "regex": json.dumps(regex_patterns),
                        },
                    )

        except json.JSONDecodeError as e:
            # Skip invalid JSON but log for awareness
            print(f"WARNING: Skipping invalid JSON in admin_settings for tenant {tenant_id}: {e}")
            continue
        except Exception as e:
            # Log but continue with other tenants
            print(f"WARNING: Error migrating taxonomy for tenant {tenant_id}: {e}")
            continue


def downgrade():
    """
    Reverting this migration doesn't restore admin_settings entries.
    The data remains in tenant_taxonomy with regex patterns.

    To fully rollback:
    1. Restore content_router.py to use taxonomy_loader.get_topic_taxonomy()
    2. Keep database taxonomy for document metadata (dual system restored)
    """
    pass
