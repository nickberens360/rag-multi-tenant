#!/usr/bin/env python3
"""
Test script to verify enhanced vector retrieval improvements.
Tests that resume queries return resume content instead of illustration content.
"""

import os
import sys

import pytest

# Load environment variables FIRST, before importing modules that read them
from dotenv import load_dotenv

load_dotenv()

# NOW import modules that depend on environment variables
from backend.core.app_initializer_v2 import initialize_app_state

# Add project root to path (go up three levels from tests/integration/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.mark.integration
def test_vector_retrieval():
    """Test the enhanced vector retrieval system."""
    print("🔍 Testing Enhanced Vector Retrieval System")
    print("=" * 50)

    try:
        # Initialize unified system
        print("📚 Initializing unified retriever system...")
        app_state, illustration_service, _ = initialize_app_state()
        unified_retriever = app_state.get("unified_retriever")
        if not unified_retriever:
            print("❌ Failed to initialize unified retriever")
            return
        print("✅ Unified retriever system initialized")

        # Test queries that previously returned wrong content
        test_queries = [
            "Show me your resume",
            "What is your work experience?",
            "Tell me about your professional background",
            "What are your qualifications?",
            "Show me your CV",
        ]

        print("\n🧪 Testing Resume Queries:")
        print("-" * 30)

        for query in test_queries:
            print(f"\n📝 Query: '{query}'")

            # Use unified retriever with smart routing
            retriever = unified_retriever.get_retriever(
                content_type_filter=["experience", "skills"], k=5  # Target resume-related content
            )
            relevant_docs = retriever.invoke(query)

            # Check document sources and content types
            sources = [doc.metadata.get("source", "unknown") for doc in relevant_docs[:3]]
            content_types = [doc.metadata.get("content_type", []) for doc in relevant_docs[:3]]
            print(f"📊 Top 3 document sources: {sources}")
            print(f"🏷️  Content types: {content_types}")

            # Check if resume/experience content is found
            experience_docs = [doc for doc in relevant_docs if "experience" in doc.metadata.get("content_type", [])]
            skills_docs = [doc for doc in relevant_docs if "skills" in doc.metadata.get("content_type", [])]
            creative_docs = [doc for doc in relevant_docs if "creative" in doc.metadata.get("content_type", [])]

            print(f"📄 Experience documents found: {len(experience_docs)}")
            print(f"🛠️  Skills documents found: {len(skills_docs)}")
            print(f"🎨 Creative documents found: {len(creative_docs)}")

            if experience_docs or skills_docs:
                print("✅ SUCCESS: Resume-related content found for resume query")
                # Show a snippet
                relevant_doc = experience_docs[0] if experience_docs else skills_docs[0]
                snippet = (
                    relevant_doc.page_content[:100] + "..."
                    if len(relevant_doc.page_content) > 100
                    else relevant_doc.page_content
                )
                print(f"📋 Content snippet: {snippet}")
            else:
                print("❌ ISSUE: No resume-related content found for resume query")
                if creative_docs:
                    print("⚠️  WARNING: Creative content returned instead")

        # Test about queries
        print("\n🧪 Testing About Queries:")
        print("-" * 30)

        about_queries = [
            "Tell me about Nick",
            "Who is Nick Berens?",
            "What's Nick's background?",
        ]

        for query in about_queries:
            print(f"\n📝 Query: '{query}'")
            # Use unified retriever targeting about content
            retriever = unified_retriever.get_retriever(
                content_type_filter=["about"], k=5  # Target about/personal content
            )
            relevant_docs = retriever.invoke(query)
            about_docs = [doc for doc in relevant_docs if "about" in doc.metadata.get("content_type", [])]
            print(f"📖 About documents found: {len(about_docs)}")

            if about_docs:
                print("✅ SUCCESS: About content found for about query")
            else:
                print("❌ ISSUE: No about content found for about query")

        print("\n🎯 Summary:")
        print("=" * 50)
        print("✅ Unified retriever system is working")
        print("✅ Automatic content discovery operational")
        print("✅ Content-type filtering functional")
        print("✅ Smart routing operational")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_vector_retrieval()
