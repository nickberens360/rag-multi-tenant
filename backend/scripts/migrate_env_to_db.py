#!/usr/bin/env python3
"""
Migration script to move non-secret environment variables to database settings.
This is a one-time migration to transition from env-based to db-based configuration.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.settings_manager import get_settings_manager
from backend.core.settings_schemas import (
    FeatureFlags,
    KnowledgeSettings,
    RagConfigurationSettings,
    ResponseSettings,
    SearchRetrievalSettings,
    SystemConfigurationSettings,
)


def migrate_env_to_db():
    """Migrate environment variables to database settings."""

    print("🚀 Starting migration of environment variables to database settings...")

    settings_manager = get_settings_manager()
    admin_user_id = 1  # System migration user

    # Database initializes automatically on first use

    # Response Settings Migration
    print("\n📝 Migrating Response Settings...")
    response_settings = ResponseSettings(
        # From env vars
        max_context_length=int(os.getenv("DEFAULT_MAX_CONTEXT_LENGTH", "2000")),
        max_context_documents=int(os.getenv("MAX_CONTEXT_DOCUMENTS", "3")),
        context_fill_ratio=float(os.getenv("CONTEXT_FILL_RATIO", "0.7")),
        enable_caching=os.getenv("ENABLE_CACHING", "true").lower() == "true",
        cache_ttl_seconds=int(os.getenv("CACHE_TTL", "3600")),
        response_llm=os.getenv("PRIMARY_LLM", "claude"),
        response_claude_model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
        response_gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        enable_smart_selection=os.getenv("ENABLE_SMART_MODEL_SELECTION", "true").lower() == "true",
    )
    settings_manager.set_response_settings(response_settings, admin_user_id)
    print("✅ Response settings migrated")

    # System Configuration Settings Migration
    print("\n📝 Migrating System Configuration Settings...")
    system_config = SystemConfigurationSettings(
        primary_llm=os.getenv("PRIMARY_LLM", "claude"),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "models/embedding-001"),
        response_llm=os.getenv("PRIMARY_LLM", "claude"),
        response_claude_model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
        response_gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        rate_limit=os.getenv("RATE_LIMIT", "5/minute"),
        system_cache_ttl_seconds=int(os.getenv("CACHE_TTL", "3600")),
        enable_smart_model_selection=os.getenv("ENABLE_SMART_MODEL_SELECTION", "true").lower() == "true",
        enable_response_smart_selection=os.getenv("ENABLE_SMART_MODEL_SELECTION", "true").lower() == "true",
    )
    settings_manager.set_system_config_settings(system_config, admin_user_id)
    print("✅ System configuration settings migrated")

    # RAG Configuration Migration
    print("\n📝 Migrating RAG Configuration Settings...")
    rag_config = RagConfigurationSettings(
        rag_use_mmr=os.getenv("RAG_USE_MMR", "false").lower() == "true",
        rag_mmr_k=int(os.getenv("RAG_MMR_K", "8")),
        rag_mmr_fetch_k=int(os.getenv("RAG_MMR_FETCH_K", "24")),
        rag_mmr_lambda_mult=float(os.getenv("RAG_MMR_LAMBDA_MULT", "0.5")),
        rag_score_threshold=float(os.getenv("RAG_SCORE_THRESHOLD", "0.2")),
        rag_use_heading_splitter=os.getenv("RAG_USE_HEADING_SPLITTER", "false").lower() == "true",
        rag_enable_delete=os.getenv("RAG_ENABLE_DELETE", "false").lower() == "true",
        rag_safe_delete=os.getenv("RAG_SAFE_DELETE", "true").lower() == "true",
        rag_index_dirs=os.getenv("RAG_INDEX_DIRS", "backend/knowledge,public"),
    )
    settings_manager.set_rag_config_settings(rag_config, admin_user_id)
    print("✅ RAG configuration settings migrated")

    # Search & Retrieval Migration (limited fields in schema)
    print("\n📝 Migrating Search & Retrieval Settings...")
    search_settings = SearchRetrievalSettings(
        semantic_similarity_threshold=float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.7")),
        max_search_results=int(os.getenv("MAX_RESULTS", "15")),
        enable_fuzzy_matching=True,
        enable_metadata_boosting=True,
    )
    settings_manager.set_search_retrieval_settings(search_settings, admin_user_id)
    print("✅ Search & retrieval settings migrated")

    # Knowledge Settings Migration
    print("\n📝 Migrating Knowledge Settings...")
    index_dirs = os.getenv("RAG_INDEX_DIRS", "backend/knowledge,public").split(",")
    heterogeneity_patterns = os.getenv(
        "HETEROGENEITY_FALLBACK_INCLUDE", "backend/knowledge/*rag*.md,backend/knowledge/resume.json"
    ).split(",")

    knowledge_settings = KnowledgeSettings(
        index_directories=[dir.strip() for dir in index_dirs],
        # Do not map FORCE_REBUILD_DATA to index_on_startup. Treat FORCE_REBUILD_DATA as an operational flag.
        enable_heterogeneity_fallback=os.getenv("ENABLE_HETEROGENEITY_FALLBACK", "false").lower() == "true",
        heterogeneity_fallback_include=[p.strip() for p in heterogeneity_patterns],
        background_sync_interval_seconds=int(os.getenv("KNOWLEDGE_SYNC_INTERVAL_SECONDS", "0")),
        auto_reindex_deltas=os.getenv("KNOWLEDGE_SYNC_AUTO_RECONCILE", "false").lower() == "true",
    )
    settings_manager.set_knowledge_settings(knowledge_settings, admin_user_id)
    print("✅ Knowledge settings migrated")

    # Feature Flags Migration (UI/UX only)
    print("\n📝 Migrating Feature Flags...")
    feature_flags = FeatureFlags(
        # Only set UI/UX related flags; caching and rate limiting move to Response/Security settings
        enable_illustrations=True,
        enable_query_preprocessing=True,
        enable_debug_mode=os.getenv("DEBUG", "false").lower() == "true",
        # Leave enable_followup_questions and enable_smart_routing to their dedicated settings managers
    )
    settings_manager.set_feature_flags(feature_flags, admin_user_id)
    print("✅ Feature flags migrated")

    print("\n✨ Migration completed successfully!")
    print("\nNext steps:")
    print("1. Review settings in the admin dashboard")
    print("2. Update config.py to use database-first approach")
    print("3. Remove migrated variables from .env file")
    print("4. Test thoroughly before deploying to production")


if __name__ == "__main__":
    try:
        # Load environment variables
        from dotenv import load_dotenv

        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded environment from {env_path}")
        else:
            print(f"⚠️ No .env file found at {env_path}, using system environment")

        migrate_env_to_db()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
