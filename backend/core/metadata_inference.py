"""
Metadata inference service for document classification.

Uses LLM (Claude Haiku by default) to infer content types and tags for documents
based on their content. Maps inferred labels to tenant-scoped taxonomy and stores
confidence scores.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from anthropic import Anthropic
from sqlalchemy import text

from .db_session import get_db_session_sync

logger = logging.getLogger(__name__)


class MetadataInferenceService:
    """Service for inferring document metadata using LLM."""

    def __init__(self, model: str = "claude-3-haiku-20240307"):
        """
        Initialize the metadata inference service.

        Args:
            model: Anthropic model ID to use for inference
        """
        self.model = model
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, metadata inference will fail")
            self.client = None
        else:
            self.client = Anthropic(api_key=api_key)

    def get_tenant_taxonomy(self, tenant_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get the controlled vocabulary for a tenant.

        Args:
            tenant_id: The tenant ID

        Returns:
            Dictionary mapping keys to taxonomy entries with labels and synonyms
        """
        taxonomy = {}
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return taxonomy

                # Set tenant context for RLS
                session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

                # Query tenant taxonomy
                rows = session.execute(
                    text(
                        """
                        SELECT key, label, synonyms
                        FROM tenant_taxonomy
                        WHERE tenant_id = :tenant_id AND active = true
                        """
                    ),
                    {"tenant_id": tenant_id},
                ).fetchall()

                for row in rows:
                    taxonomy[row[0]] = {
                        "label": row[1],
                        "synonyms": row[2] if row[2] else [],
                    }

        except Exception as e:
            logger.error(f"Failed to load tenant taxonomy: {e}")

        return taxonomy

    def read_file_sample(self, path: str, max_chars: int = 4000) -> str:
        """
        Read a sample of the file content for inference.

        Args:
            path: Path to the file
            max_chars: Maximum number of characters to read

        Returns:
            File content sample
        """
        try:
            file_path = Path(path)
            if not file_path.exists():
                logger.warning(f"File not found: {path}")
                return ""

            # For now, only support text-based files
            # TODO: Add PDF, DOCX extraction in future
            text_extensions = {".md", ".txt", ".json", ".html", ".xml", ".csv"}
            if file_path.suffix.lower() not in text_extensions:
                logger.warning(f"Unsupported file type for inference: {file_path.suffix}")
                return ""

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)

            return content

        except Exception as e:
            logger.error(f"Failed to read file sample from {path}: {e}")
            return ""

    def infer_metadata(
        self, path: str, tenant_id: str, content_sample: Optional[str] = None
    ) -> Tuple[Optional[str], List[str], float]:
        """
        Infer content type and tags for a document.

        Args:
            path: Path to the document
            tenant_id: Tenant ID for taxonomy lookup
            content_sample: Optional pre-loaded content sample

        Returns:
            Tuple of (content_type, tags, confidence)
        """
        if self.client is None:
            logger.error("Anthropic client not initialized, cannot infer metadata")
            return None, [], 0.0

        # Load tenant taxonomy
        taxonomy = self.get_tenant_taxonomy(tenant_id)
        if not taxonomy:
            logger.warning(f"No taxonomy found for tenant {tenant_id}, using defaults")
            taxonomy = {
                "technical": {"label": "Technical Documentation", "synonyms": ["docs", "documentation"]},
                "experience": {"label": "Experience & Projects", "synonyms": ["portfolio", "work"]},
                "creative": {"label": "Creative Content", "synonyms": ["blog", "writing"]},
                "personal": {"label": "Personal Information", "synonyms": ["bio", "about"]},
            }

        # Read file sample if not provided
        if content_sample is None:
            content_sample = self.read_file_sample(path)

        if not content_sample:
            logger.warning(f"No content sample for {path}, cannot infer metadata")
            return None, [], 0.0

        # Build taxonomy description for prompt
        taxonomy_desc = "\n".join(
            [
                f"- {key}: {data['label']} (synonyms: {', '.join(data.get('synonyms', []))})"
                for key, data in taxonomy.items()
            ]
        )

        # Construct inference prompt
        filename = Path(path).name
        prompt = f"""You are a document classifier. Analyze this document and classify it according to the provided taxonomy.

Document filename: {filename}
Document content (first 4000 chars):
---
{content_sample[:4000]}
---

Available categories:
{taxonomy_desc}

Instructions:
1. Select ONE primary category that best matches this document
2. Suggest 1-5 relevant tags that describe the content
3. Provide a confidence score (0.0-1.0) for your classification

Respond in this exact format:
CONTENT_TYPE: <category_key>
TAGS: <tag1>, <tag2>, <tag3>
CONFIDENCE: <score>

Example:
CONTENT_TYPE: technical
TAGS: python, fastapi, backend, api
CONFIDENCE: 0.92
"""

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.0,  # Deterministic classification
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = response.content[0].text.strip()
            logger.debug(f"LLM inference response: {response_text}")

            content_type = None
            tags = []
            confidence = 0.5  # Default if parsing fails

            for line in response_text.split("\n"):
                line = line.strip()
                if line.startswith("CONTENT_TYPE:"):
                    content_type = line.split(":", 1)[1].strip()
                elif line.startswith("TAGS:"):
                    tag_str = line.split(":", 1)[1].strip()
                    tags = [t.strip() for t in tag_str.split(",") if t.strip()]
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.split(":", 1)[1].strip())
                    except ValueError:
                        confidence = 0.5

            # Validate content_type against taxonomy
            if content_type and content_type not in taxonomy:
                logger.warning(f"Inferred content_type '{content_type}' not in taxonomy, setting to None")
                content_type = None

            logger.info(f"Inferred metadata for {filename}: type={content_type}, tags={tags}, confidence={confidence}")
            return content_type, tags, confidence

        except Exception as e:
            logger.error(f"Failed to infer metadata for {path}: {e}")
            return None, [], 0.0

    def update_file_metadata(
        self,
        path: str,
        tenant_id: str,
        content_type: Optional[str],
        tags: List[str],
        confidence: float,
        updated_by: Optional[str] = None,
    ) -> bool:
        """
        Update the inferred metadata for a file in the database.

        Args:
            path: File path
            tenant_id: Tenant ID
            content_type: Inferred content type
            tags: Inferred tags
            confidence: Confidence score
            updated_by: Optional user ID who triggered the inference

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return False

                # Set tenant context for RLS
                session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

                # Update inferred fields
                session.execute(
                    text(
                        """
                        UPDATE knowledge_files
                        SET inferred_content_type = :content_type,
                            inferred_tags = :tags::jsonb,
                            inferred_confidence = :confidence,
                            metadata_updated_at = NOW(),
                            metadata_updated_by = :updated_by,
                            metadata_version = metadata_version + 1,
                            status = 'discovered'
                        WHERE path = :path
                          AND tenant_id = :tenant_id
                        """
                    ),
                    {
                        "path": path,
                        "tenant_id": tenant_id,
                        "content_type": content_type,
                        "tags": tags if tags else [],
                        "confidence": confidence,
                        "updated_by": updated_by,
                    },
                )

                logger.info(f"Updated inferred metadata for {path} and marked for reindex")
                return True

        except Exception as e:
            logger.error(f"Failed to update file metadata in DB: {e}")
            return False

    def infer_and_store(
        self, path: str, tenant_id: str, updated_by: Optional[str] = None, content_sample: Optional[str] = None
    ) -> bool:
        """
        Infer metadata and store it in the database.

        Args:
            path: File path
            tenant_id: Tenant ID
            updated_by: Optional user ID who triggered the inference
            content_sample: Optional pre-loaded content sample

        Returns:
            True if successful, False otherwise
        """
        content_type, tags, confidence = self.infer_metadata(path, tenant_id, content_sample)

        return self.update_file_metadata(path, tenant_id, content_type, tags, confidence, updated_by)


def infer_metadata_background(path: str, tenant_id: str, updated_by: Optional[str] = None) -> None:
    """
    Background task to infer metadata for a file.

    Args:
        path: File path
        tenant_id: Tenant ID
        updated_by: Optional user ID who triggered the inference
    """
    try:
        # Get model from environment or use default
        model = os.getenv("METADATA_INFERENCE_MODEL", "claude-3-haiku-20240307")

        service = MetadataInferenceService(model=model)
        success = service.infer_and_store(path, tenant_id, updated_by)

        if success:
            logger.info(f"Background metadata inference completed for {path}")
        else:
            logger.warning(f"Background metadata inference failed for {path}")

    except Exception as e:
        logger.error(f"Background metadata inference task crashed for {path}: {e}")
