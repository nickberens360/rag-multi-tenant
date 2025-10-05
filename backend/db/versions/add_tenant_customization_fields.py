"""Add tenant customization fields for multi-tenant AI assistants

Revision ID: add_tenant_customization_fields
Revises: add_user_2fa_table
Create Date: 2025-10-04

This migration adds customization fields to the tenants table to enable
tenant-specific AI assistant configuration and remove hardcoded references.
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_tenant_customization_fields"
down_revision = "add_user_2fa_table"
branch_labels = None
depends_on = None


def upgrade():
    """Add tenant customization fields"""

    # Add new columns
    op.add_column("tenants", sa.Column("assistant_name", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("system_prompt_template", sa.Text(), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("tone", sa.String(100), nullable=False, server_default="professional"),
    )
    op.add_column(
        "tenants",
        sa.Column("domain", sa.String(255), nullable=False, server_default="general"),
    )
    op.add_column("tenants", sa.Column("brand_voice", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("tenants", sa.Column("api_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("customization_level", sa.String(50), nullable=False, server_default="basic"),
    )

    # Add check constraints
    op.create_check_constraint(
        "tenants_tone_check", "tenants", "tone IN ('friendly', 'professional', 'technical', 'casual')"
    )

    op.create_check_constraint(
        "tenants_customization_level_check",
        "tenants",
        "customization_level IN ('basic', 'advanced', 'custom')",
    )

    # Create trigger for updated_at (if not already exists)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_tenants_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Drop trigger if it exists, then recreate
    op.execute("DROP TRIGGER IF EXISTS trigger_update_tenants_updated_at ON tenants;")

    op.execute(
        """
        CREATE TRIGGER trigger_update_tenants_updated_at
        BEFORE UPDATE ON tenants
        FOR EACH ROW
        EXECUTE FUNCTION update_tenants_updated_at();
    """
    )

    # Populate default tenant (Nick Berens) with existing behavior
    default_brand_voice = json.dumps(
        {"style": "first-person", "personality": ["friendly", "professional", "approachable"]}
    )

    default_api_metadata = json.dumps(
        {"contact": {"name": "Nick Berens", "email": "nick@nickberens.me", "url": "https://nickberens.me"}}
    )

    op.execute(
        f"""
        UPDATE tenants
        SET
            assistant_name = 'Nick Berens AI Assistant',
            tone = 'friendly',
            domain = 'software engineering and design',
            brand_voice = '{default_brand_voice}'::jsonb,
            api_metadata = '{default_api_metadata}'::jsonb,
            customization_level = 'advanced'
        WHERE slug = 'default';
    """
    )

    # Set generic defaults for other tenants
    op.execute(
        """
        UPDATE tenants
        SET
            tone = 'professional',
            domain = 'general',
            customization_level = 'basic'
        WHERE slug != 'default' AND assistant_name IS NULL;
    """
    )


def downgrade():
    """Remove tenant customization fields"""

    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trigger_update_tenants_updated_at ON tenants;")
    op.execute("DROP FUNCTION IF EXISTS update_tenants_updated_at();")

    # Drop check constraints
    op.drop_constraint("tenants_tone_check", "tenants")
    op.drop_constraint("tenants_customization_level_check", "tenants")

    # Drop columns
    op.drop_column("tenants", "customization_level")
    op.drop_column("tenants", "api_metadata")
    op.drop_column("tenants", "brand_voice")
    op.drop_column("tenants", "domain")
    op.drop_column("tenants", "tone")
    op.drop_column("tenants", "system_prompt_template")
    op.drop_column("tenants", "assistant_name")
