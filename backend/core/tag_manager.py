"""
Tag Manager - Utility class for folksonomy support.

Provides methods for:
- Tag autocomplete suggestions
- Tag analytics and usage tracking
- Tag promotion to official taxonomy
- Fuzzy matching for typo detection
- Tag co-occurrence analysis
"""

import logging
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text

from .db_session import get_db_session_sync

logger = logging.getLogger(__name__)


class TagManager:
    """Manages user-created tags and controlled vocabulary."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_autocomplete_suggestions(
        self, tenant_id: str, query: str, limit: int = 10
    ) -> List[Dict]:
        """
        Get tag autocomplete suggestions from existing tags in the system.

        Args:
            tenant_id: Tenant UUID
            query: Search query (case-insensitive substring match)
            limit: Maximum results (max 50)

        Returns:
            List of suggestion dicts with tag, usage_count, and source
        """
        try:
            limit = min(limit, 50)  # Cap at 50

            with get_db_session_sync() as session:
                if session is None:
                    self.logger.error("Database session not available")
                    return []

                # Set tenant context for RLS
                session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

                # Get all unique tags from knowledge_files (manual and inferred)
                # Union with tenant_taxonomy tags for official tags
                result = session.execute(
                    text(
                        """
                        WITH all_tags AS (
                            -- Tags from knowledge files (manual)
                            SELECT
                                jsonb_array_elements_text(manual_tags) AS tag,
                                'manual' AS source_type
                            FROM knowledge_files
                            WHERE tenant_id = :tenant_id
                              AND manual_tags IS NOT NULL
                              AND jsonb_array_length(manual_tags) > 0

                            UNION ALL

                            -- Tags from knowledge files (inferred)
                            SELECT
                                jsonb_array_elements_text(inferred_tags) AS tag,
                                'inferred' AS source_type
                            FROM knowledge_files
                            WHERE tenant_id = :tenant_id
                              AND inferred_tags IS NOT NULL
                              AND jsonb_array_length(inferred_tags) > 0

                            UNION ALL

                            -- Official taxonomy entries
                            SELECT
                                key AS tag,
                                'official' AS source_type
                            FROM tenant_taxonomy
                            WHERE tenant_id = :tenant_id
                              AND active = true

                            UNION ALL

                            -- Taxonomy synonyms
                            SELECT
                                jsonb_array_elements_text(synonyms) AS tag,
                                'official' AS source_type
                            FROM tenant_taxonomy
                            WHERE tenant_id = :tenant_id
                              AND active = true
                              AND synonyms IS NOT NULL
                              AND jsonb_array_length(synonyms) > 0
                        )
                        SELECT
                            tag,
                            COUNT(*) AS usage_count,
                            CASE
                                WHEN BOOL_OR(source_type = 'official') THEN 'official'
                                WHEN BOOL_OR(source_type = 'manual') THEN 'manual'
                                ELSE 'inferred'
                            END AS source
                        FROM all_tags
                        WHERE LOWER(tag) LIKE LOWER(:query)
                        GROUP BY tag
                        ORDER BY usage_count DESC, tag ASC
                        LIMIT :limit
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "query": f"%{query}%",
                        "limit": limit,
                    },
                ).fetchall()

                suggestions = []
                for row in result:
                    suggestions.append({
                        "tag": row[0],
                        "usage_count": row[1],
                        "source": row[2],
                    })

                return suggestions

        except Exception as e:
            self.logger.error(f"Failed to get autocomplete suggestions: {e}")
            return []

    def get_tag_analytics(self, tenant_id: str) -> Dict:
        """
        Get comprehensive tag analytics for the tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dictionary with popular_tags, orphans, co_occurring, and coverage metrics
        """
        try:
            with get_db_session_sync() as session:
                if session is None:
                    self.logger.error("Database session not available")
                    return self._empty_analytics()

                # Set tenant context for RLS
                session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

                # 1. Popular tags (top 20)
                popular_result = session.execute(
                    text(
                        """
                        WITH all_tags AS (
                            SELECT jsonb_array_elements_text(manual_tags) AS tag
                            FROM knowledge_files
                            WHERE tenant_id = :tenant_id AND manual_tags IS NOT NULL
                            UNION ALL
                            SELECT jsonb_array_elements_text(inferred_tags) AS tag
                            FROM knowledge_files
                            WHERE tenant_id = :tenant_id AND inferred_tags IS NOT NULL
                        )
                        SELECT
                            tag,
                            COUNT(*) AS count,
                            EXISTS(
                                SELECT 1 FROM tenant_taxonomy
                                WHERE tenant_id = :tenant_id
                                  AND (key = tag OR synonyms @> jsonb_build_array(tag))
                                  AND active = true
                            ) AS official
                        FROM all_tags
                        GROUP BY tag
                        ORDER BY count DESC, tag ASC
                        LIMIT 20
                        """
                    ),
                    {"tenant_id": tenant_id},
                ).fetchall()

                popular_tags = [
                    {"tag": row[0], "count": row[1], "official": row[2]}
                    for row in popular_result
                ]

                # 2. Orphan tags (used only once - possible typos)
                orphan_result = session.execute(
                    text(
                        """
                        WITH all_tags AS (
                            SELECT
                                jsonb_array_elements_text(
                                    COALESCE(manual_tags, inferred_tags)
                                ) AS tag,
                                path
                            FROM knowledge_files
                            WHERE tenant_id = :tenant_id
                              AND (manual_tags IS NOT NULL OR inferred_tags IS NOT NULL)
                        ),
                        tag_counts AS (
                            SELECT tag, COUNT(*) AS count, MIN(path) AS file_path
                            FROM all_tags
                            GROUP BY tag
                        )
                        SELECT tag, file_path
                        FROM tag_counts
                        WHERE count = 1
                        ORDER BY tag
                        LIMIT 50
                        """
                    ),
                    {"tenant_id": tenant_id},
                ).fetchall()

                orphans = [
                    {"tag": row[0], "count": 1, "file_path": row[1]}
                    for row in orphan_result
                ]

                # 3. Tag co-occurrence (tags frequently used together)
                cooccur_result = session.execute(
                    text(
                        """
                        WITH file_tags AS (
                            SELECT
                                path,
                                COALESCE(manual_tags, inferred_tags) AS tags
                            FROM knowledge_files
                            WHERE tenant_id = :tenant_id
                              AND (manual_tags IS NOT NULL OR inferred_tags IS NOT NULL)
                        ),
                        tag_pairs AS (
                            SELECT
                                t1.tag AS tag1,
                                t2.tag AS tag2,
                                COUNT(*) AS count
                            FROM file_tags ft
                            CROSS JOIN LATERAL jsonb_array_elements_text(ft.tags) AS t1(tag)
                            CROSS JOIN LATERAL jsonb_array_elements_text(ft.tags) AS t2(tag)
                            WHERE t1.tag < t2.tag  -- Avoid duplicates and self-pairs
                            GROUP BY t1.tag, t2.tag
                            HAVING COUNT(*) >= 2  -- Must occur together at least twice
                        )
                        SELECT
                            tag1,
                            tag2,
                            count,
                            ROUND(
                                count::numeric / NULLIF(
                                    (SELECT COUNT(DISTINCT path)
                                     FROM file_tags
                                     WHERE tags @> jsonb_build_array(tag1)
                                        OR tags @> jsonb_build_array(tag2)
                                    ), 0
                                ),
                                2
                            ) AS correlation
                        FROM tag_pairs
                        ORDER BY count DESC, correlation DESC
                        LIMIT 20
                        """
                    ),
                    {"tenant_id": tenant_id},
                ).fetchall()

                co_occurring = [
                    {
                        "tag1": row[0],
                        "tag2": row[1],
                        "count": row[2],
                        "correlation": float(row[3]) if row[3] else 0.0,
                    }
                    for row in cooccur_result
                ]

                # 4. Coverage metrics
                coverage_result = session.execute(
                    text(
                        """
                        SELECT
                            COUNT(*) AS total_files,
                            COUNT(CASE
                                WHEN manual_tags IS NOT NULL
                                  OR inferred_tags IS NOT NULL
                                THEN 1
                            END) AS files_with_tags
                        FROM knowledge_files
                        WHERE tenant_id = :tenant_id
                        """
                    ),
                    {"tenant_id": tenant_id},
                ).fetchone()

                total_files = coverage_result[0] if coverage_result else 0
                files_with_tags = coverage_result[1] if coverage_result else 0
                coverage_percentage = (
                    (files_with_tags / total_files * 100) if total_files > 0 else 0.0
                )

                return {
                    "popular_tags": popular_tags,
                    "orphans": orphans,
                    "co_occurring": co_occurring,
                    "coverage": {
                        "total_files": total_files,
                        "files_with_tags": files_with_tags,
                        "coverage_percentage": round(coverage_percentage, 2),
                    },
                }

        except Exception as e:
            self.logger.error(f"Failed to get tag analytics: {e}")
            return self._empty_analytics()

    def promote_tag_to_official(
        self,
        tenant_id: str,
        tag: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Promote a user-created tag to official taxonomy entry.

        Args:
            tenant_id: Tenant UUID
            tag: Tag to promote
            metadata: Optional metadata (label, synonyms, regex, description)

        Returns:
            True if successful, False otherwise
        """
        try:
            metadata = metadata or {}
            label = metadata.get("label", tag.replace("-", " ").replace("_", " ").title())
            synonyms = metadata.get("synonyms", [])
            regex_patterns = metadata.get("regex", [])
            description = metadata.get("description", "")

            with get_db_session_sync() as session:
                if session is None:
                    self.logger.error("Database session not available")
                    return False

                # Set tenant context for RLS
                session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

                # Check if already exists
                existing = session.execute(
                    text(
                        """
                        SELECT key FROM tenant_taxonomy
                        WHERE tenant_id = :tenant_id AND key = :key
                        """
                    ),
                    {"tenant_id": tenant_id, "key": tag},
                ).fetchone()

                if existing:
                    self.logger.warning(f"Tag '{tag}' already exists in taxonomy")
                    return False

                # Count current usage
                usage_count_result = session.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM knowledge_files
                        WHERE tenant_id = :tenant_id
                          AND (manual_tags @> jsonb_build_array(:tag)
                               OR inferred_tags @> jsonb_build_array(:tag))
                        """
                    ),
                    {"tenant_id": tenant_id, "tag": tag},
                ).scalar()

                usage_count = usage_count_result or 0

                # Insert new taxonomy entry
                session.execute(
                    text(
                        """
                        INSERT INTO tenant_taxonomy
                          (tenant_id, key, label, synonyms, regex, active, user_created, usage_count)
                        VALUES
                          (:tenant_id, :key, :label, :synonyms::jsonb, :regex::jsonb, true, false, :usage_count)
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "key": tag,
                        "label": label,
                        "synonyms": synonyms,
                        "regex": regex_patterns,
                        "usage_count": usage_count,
                    },
                )

                self.logger.info(
                    f"Promoted tag '{tag}' to official taxonomy for tenant {tenant_id} with usage count {usage_count}"
                )
                return True

        except Exception as e:
            self.logger.error(f"Failed to promote tag '{tag}': {e}")
            return False

    def increment_tag_usage(self, tenant_id: str, tag: str) -> None:
        """
        Increment usage count for a tag in tenant_taxonomy if it exists.

        Args:
            tenant_id: Tenant UUID
            tag: Tag to increment
        """
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return

                # Set tenant context for RLS
                session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

                # Increment if exists in taxonomy
                session.execute(
                    text(
                        """
                        UPDATE tenant_taxonomy
                        SET usage_count = usage_count + 1
                        WHERE tenant_id = :tenant_id AND key = :tag
                        """
                    ),
                    {"tenant_id": tenant_id, "tag": tag},
                )

        except Exception as e:
            self.logger.warning(f"Failed to increment tag usage for '{tag}': {e}")

    def find_similar_tags(
        self, tag: str, existing_tags: List[str], threshold: float = 0.8
    ) -> List[str]:
        """
        Find similar tags using fuzzy string matching (for typo detection).

        Args:
            tag: Tag to check
            existing_tags: List of existing tags to compare against
            threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            List of similar tags above the threshold
        """
        similar = []

        for existing_tag in existing_tags:
            ratio = SequenceMatcher(None, tag.lower(), existing_tag.lower()).ratio()
            if ratio >= threshold and tag.lower() != existing_tag.lower():
                similar.append(existing_tag)

        return similar

    def get_co_occurring_tags(
        self, tenant_id: str, min_correlation: float = 0.5
    ) -> List[Dict]:
        """
        Get pairs of tags that frequently occur together.

        Args:
            tenant_id: Tenant UUID
            min_correlation: Minimum correlation threshold

        Returns:
            List of tag pairs with correlation scores
        """
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return []

                # Set tenant context for RLS
                session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

                result = session.execute(
                    text(
                        """
                        WITH file_tags AS (
                            SELECT
                                path,
                                COALESCE(manual_tags, inferred_tags) AS tags
                            FROM knowledge_files
                            WHERE tenant_id = :tenant_id
                              AND (manual_tags IS NOT NULL OR inferred_tags IS NOT NULL)
                        ),
                        tag_pairs AS (
                            SELECT
                                t1.tag AS tag1,
                                t2.tag AS tag2,
                                COUNT(*) AS count
                            FROM file_tags ft
                            CROSS JOIN LATERAL jsonb_array_elements_text(ft.tags) AS t1(tag)
                            CROSS JOIN LATERAL jsonb_array_elements_text(ft.tags) AS t2(tag)
                            WHERE t1.tag < t2.tag
                            GROUP BY t1.tag, t2.tag
                            HAVING COUNT(*) >= 2
                        )
                        SELECT
                            tag1,
                            tag2,
                            count,
                            ROUND(
                                count::numeric / NULLIF(
                                    (SELECT COUNT(DISTINCT path)
                                     FROM file_tags
                                     WHERE tags @> jsonb_build_array(tag1)
                                        OR tags @> jsonb_build_array(tag2)
                                    ), 0
                                ),
                                2
                            ) AS correlation
                        FROM tag_pairs
                        WHERE ROUND(
                            count::numeric / NULLIF(
                                (SELECT COUNT(DISTINCT path)
                                 FROM file_tags
                                 WHERE tags @> jsonb_build_array(tag1)
                                    OR tags @> jsonb_build_array(tag2)
                                ), 0
                            ), 2
                        ) >= :min_correlation
                        ORDER BY count DESC, correlation DESC
                        LIMIT 50
                        """
                    ),
                    {"tenant_id": tenant_id, "min_correlation": min_correlation},
                ).fetchall()

                return [
                    {
                        "tag1": row[0],
                        "tag2": row[1],
                        "count": row[2],
                        "correlation": float(row[3]) if row[3] else 0.0,
                    }
                    for row in result
                ]

        except Exception as e:
            self.logger.error(f"Failed to get co-occurring tags: {e}")
            return []

    def _empty_analytics(self) -> Dict:
        """Return empty analytics structure."""
        return {
            "popular_tags": [],
            "orphans": [],
            "co_occurring": [],
            "coverage": {
                "total_files": 0,
                "files_with_tags": 0,
                "coverage_percentage": 0.0,
            },
        }


# Singleton instance
tag_manager = TagManager()
