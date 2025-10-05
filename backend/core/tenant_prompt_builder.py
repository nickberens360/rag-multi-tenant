"""
Tenant-aware prompt builder service.

This module provides dynamic prompt generation based on tenant configuration,
replacing hardcoded references with tenant-specific customization.

Features:
- Template-based prompt generation
- Tenant metadata interpolation
- Caching for performance
- Fallback to generic defaults
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import text

from .db_session import get_db_session_sync

logger = logging.getLogger(__name__)


class TenantPromptBuilder:
    """
    Builds customized prompts for each tenant.

    This service fetches tenant configuration from the database and generates
    appropriate system prompts, response guidelines, and follow-up prompts
    based on the tenant's customization settings.
    """

    # Cache TTL (5 minutes)
    CACHE_TTL = timedelta(minutes=5)

    # Template cache (in-memory)
    _tenant_cache: Dict[str, tuple[Dict, datetime]] = {}

    # Default templates for different prompt types
    GENERIC_TEMPLATES = {
        "system": """You are {assistant_name}, an AI assistant for {organization_name}.
You help visitors learn about {organization_name}'s {domain}.

Use the following pieces of context to answer the question. If you don't know the answer
based on the context provided, just say you don't have that information.

Context: {context}

Respond in a {tone} tone. Keep responses concise but informative.""",
        "technical": """You are {assistant_name}, a technical AI assistant for {organization_name}.

You provide detailed, technical information about {organization_name}'s {domain}.

Context: {context}

Provide thorough, technically accurate responses. Include relevant details, code examples
when appropriate, and technical specifications.""",
        "creative": """You are {assistant_name}, showcasing {organization_name}'s creative work.

You help visitors explore and understand {organization_name}'s portfolio, projects, and
creative achievements.

Context: {context}

Describe work in an engaging, {tone} manner while maintaining accuracy.""",
        "simple_response": """Answer the question directly and concisely about {organization_name}.
If the information is in the context, provide it clearly. If not, say you don't have that information.

Context: {context}""",
        "detailed_response": """Provide a comprehensive answer about {organization_name}'s {domain}.
Use all relevant information from the context. Structure your response clearly with:
- Main points
- Supporting details
- Examples when available

Context: {context}""",
    }

    def _get_tenant(self, tenant_id: UUID) -> Dict:
        """
        Get tenant from cache or database.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dictionary with tenant data

        Raises:
            ValueError: If tenant not found
        """
        tenant_id_str = str(tenant_id)

        # Check cache
        if tenant_id_str in self._tenant_cache:
            tenant_data, cached_at = self._tenant_cache[tenant_id_str]
            if datetime.utcnow() - cached_at < self.CACHE_TTL:
                logger.debug(f"Using cached tenant data for {tenant_id_str}")
                return tenant_data

        # Fetch from database
        with get_db_session_sync() as session:
            if session is None:
                logger.warning("Database session not available, using fallback tenant")
                return self._get_fallback_tenant()

            result = session.execute(
                text(
                    """
                SELECT
                    id, slug, name,
                    assistant_name, tone, domain,
                    brand_voice, api_metadata,
                    customization_level, system_prompt_template
                FROM tenants
                WHERE id = :tenant_id AND deleted_at IS NULL
                LIMIT 1
            """
                ),
                {"tenant_id": tenant_id_str},
            )

            row = result.fetchone()

            if not row:
                logger.error(f"Tenant {tenant_id_str} not found")
                raise ValueError(f"Tenant {tenant_id} not found")

            # Convert to dict
            tenant_data = {
                "id": str(row[0]),
                "slug": row[1],
                "name": row[2],
                "assistant_name": row[3],
                "tone": row[4],
                "domain": row[5],
                "brand_voice": row[6] if row[6] else {},
                "api_metadata": row[7] if row[7] else {},
                "customization_level": row[8],
                "system_prompt_template": row[9],
            }

            # Cache it
            self._tenant_cache[tenant_id_str] = (tenant_data, datetime.utcnow())
            logger.debug(f"Fetched and cached tenant data for {tenant_id_str}")

            return tenant_data

    def _get_fallback_tenant(self) -> Dict:
        """Get fallback tenant configuration when database is unavailable."""
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "slug": "default",
            "name": "Organization",
            "assistant_name": None,
            "tone": "professional",
            "domain": "general",
            "brand_voice": {},
            "api_metadata": {},
            "customization_level": "basic",
            "system_prompt_template": None,
        }

    def _get_template_variables(self, tenant: Dict) -> Dict[str, str]:
        """
        Build template variables from tenant metadata.

        Args:
            tenant: Tenant data dictionary

        Returns:
            Dictionary of template variables
        """
        # Use assistant_name if provided, otherwise create default
        assistant_name = tenant.get("assistant_name")
        if not assistant_name:
            assistant_name = f"{tenant['name']} Assistant"

        return {
            "organization_name": tenant["name"],
            "assistant_name": assistant_name,
            "domain": tenant.get("domain") or "general information",
            "tone": tenant.get("tone") or "professional",
        }

    def build_system_prompt(self, tenant_id: UUID, prompt_type: str = "system", **extra_vars) -> str:
        """
        Build tenant-specific system prompt.

        Args:
            tenant_id: Tenant UUID
            prompt_type: Type of prompt (system, technical, creative, etc.)
            **extra_vars: Additional template variables (like context)

        Returns:
            Populated system prompt string

        Example:
            >>> builder = TenantPromptBuilder()
            >>> prompt = builder.build_system_prompt(
            ...     tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            ...     prompt_type="system",
            ...     context="Sample context"
            ... )
        """
        try:
            tenant = self._get_tenant(tenant_id)
        except ValueError as e:
            logger.error(f"Failed to get tenant: {e}, using fallback")
            tenant = self._get_fallback_tenant()

        # Check for custom template
        if tenant.get("customization_level") == "custom" and tenant.get("system_prompt_template"):
            template = tenant["system_prompt_template"]
            logger.info(f"Using custom prompt template for tenant {tenant['slug']}")
        else:
            # Use generic template
            template = self.GENERIC_TEMPLATES.get(prompt_type, self.GENERIC_TEMPLATES["system"])
            logger.debug(f"Using generic '{prompt_type}' template for tenant {tenant['slug']}")

        # Build variables
        variables = self._get_template_variables(tenant)
        variables.update(extra_vars)

        # Populate template
        try:
            prompt = template.format(**variables)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            # Fallback to minimal template
            context = variables.get("context", "{context}")
            prompt = f"You are an AI assistant for {tenant['name']}.\n\nContext: {context}"

        return prompt

    def build_response_guidelines(self, tenant_id: UUID, complexity: str = "simple") -> str:
        """
        Build response format guidelines based on query complexity.

        Args:
            tenant_id: Tenant UUID
            complexity: Query complexity (simple, moderate, complex)

        Returns:
            Response formatting guidelines
        """
        try:
            tenant = self._get_tenant(tenant_id)
        except ValueError as e:
            logger.error(f"Failed to get tenant: {e}, using fallback")
            tenant = self._get_fallback_tenant()

        # Get brand voice guidelines
        brand_voice = tenant.get("brand_voice", {})

        guidelines = []

        # Complexity-based guidelines
        if complexity == "simple":
            template_key = "simple_response"
        else:
            template_key = "detailed_response"

        base_guideline = self.GENERIC_TEMPLATES[template_key]
        variables = self._get_template_variables(tenant)

        try:
            base_formatted = base_guideline.format(**variables)
            guidelines.append(base_formatted)
        except KeyError:
            pass

        # Add brand voice guidelines
        if brand_voice.get("style") == "first-person":
            guidelines.append("Use first-person perspective when appropriate.")
        elif brand_voice.get("style") == "third-person":
            guidelines.append("Always use third-person perspective.")

        if brand_voice.get("prefer"):
            prefer_phrases = ", ".join(brand_voice["prefer"][:3])
            guidelines.append(f"Prefer phrases like: {prefer_phrases}")

        if brand_voice.get("avoid"):
            avoid_phrases = ", ".join(brand_voice["avoid"][:3])
            guidelines.append(f"Avoid phrases like: {avoid_phrases}")

        return "\n\n".join(guidelines)

    def get_followup_prompt(self, tenant_id: UUID) -> str:
        """
        Get prompt for generating follow-up questions.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Follow-up question generation prompt
        """
        try:
            tenant = self._get_tenant(tenant_id)
        except ValueError as e:
            logger.error(f"Failed to get tenant: {e}, using fallback")
            tenant = self._get_fallback_tenant()

        variables = self._get_template_variables(tenant)

        template = """Based on the conversation about {organization_name}, generate 2-3 relevant
follow-up questions that would help the user learn more about {organization_name}'s {domain}.

Questions should be:
- Specific and actionable
- Related to the current topic
- Appropriate for a {tone} conversation"""

        return template.format(**variables)

    @classmethod
    def clear_cache(cls, tenant_id: Optional[UUID] = None):
        """
        Clear prompt cache.

        Args:
            tenant_id: Specific tenant to clear, or None for all
        """
        if tenant_id:
            tenant_id_str = str(tenant_id)
            cls._tenant_cache.pop(tenant_id_str, None)
            logger.debug(f"Cleared cache for tenant {tenant_id_str}")
        else:
            cls._tenant_cache.clear()
            logger.debug("Cleared all tenant cache")


# Singleton instance
_prompt_builder = None


def get_prompt_builder() -> TenantPromptBuilder:
    """Get singleton TenantPromptBuilder instance."""
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = TenantPromptBuilder()
    return _prompt_builder
