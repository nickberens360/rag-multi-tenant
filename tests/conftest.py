"""
Pytest configuration to streamline local and CI tests without extra env vars.

This file applies lightweight test-time patches only during pytest runs:
- Disable SlowAPI rate limiting decorator to avoid ASGITransport issues
  with streaming responses and to speed up tests.
- Provide centralized Chroma fixtures to avoid ephemeral instance conflicts
"""

from __future__ import annotations

import os
import tempfile

import pytest


def pytest_configure(config):
    """Configure pytest environment to disable rate limiting for all tests."""
    # Set environment variable for high rate limits during testing
    os.environ["RATE_LIMIT"] = "100000/minute"


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Setup test environment with disabled rate limiting."""
    # Ensure environment variable is set for entire test session
    original_rate_limit = os.environ.get("RATE_LIMIT")
    os.environ["RATE_LIMIT"] = "100000/minute"

    yield

    # Restore original value after tests
    if original_rate_limit is not None:
        os.environ["RATE_LIMIT"] = original_rate_limit
    else:
        os.environ.pop("RATE_LIMIT", None)


@pytest.fixture(scope="session")
def session_chroma_dir():
    """Provide a single, consistent Chroma persist directory for all tests in the session."""
    with tempfile.TemporaryDirectory(prefix="chroma_test_session_") as tmpdir:
        yield tmpdir


@pytest.fixture(scope="function")
def isolated_chroma_dir(tmp_path):
    """Provide an isolated Chroma persist directory for each test function."""
    chroma_dir = tmp_path / "chroma_test"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    yield str(chroma_dir)


class MockEmbeddings:
    """Consistent mock embeddings for all tests to avoid different settings."""

    def embed_documents(self, texts):
        return [[0.0] * 384 for _ in texts]  # Consistent dimension

    def embed_query(self, text):
        return [0.0] * 384  # Consistent dimension


@pytest.fixture(scope="session")
def mock_embeddings():
    """Provide consistent mock embeddings for all tests."""
    return MockEmbeddings()


@pytest.fixture(scope="function")
def mock_llm():
    """Provide a consistent mock LLM for all tests."""

    class MockLLM:
        def invoke(self, prompt):
            return "Mock response"

        def __call__(self, prompt):
            return "Mock response"

    return MockLLM()


@pytest.fixture(autouse=True)
def cleanup_chroma_instances():
    """Automatically cleanup any lingering Chroma instances between tests."""
    import gc

    # Pre-test cleanup
    try:
        # Force garbage collection to clean up any previous instances
        gc.collect()
    except Exception:
        pass

    yield

    # Post-test cleanup
    try:
        # Attempt to clean up any Chroma client instances
        import chromadb

        if hasattr(chromadb, "_client_instances"):
            chromadb._client_instances.clear()

        # Force garbage collection after each test
        gc.collect()
    except Exception:
        # If cleanup fails, that's okay - we don't want to fail tests for this
        pass


@pytest.fixture(scope="function")
def reset_chroma_env():
    """Reset Chroma-related environment variables for consistent test behavior."""
    original_env = {}

    # Set consistent Chroma environment for tests
    chroma_env_vars = {
        "CHROMA_AUTO_RESET_ON_CONFIG_ERROR": "true",
        "ALLOW_RESET": "true",  # In case any code checks this
    }

    for key, value in chroma_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(autouse=True, scope="session")
def set_unified_persist_dir_env(session_chroma_dir: str):
    """Ensure the FastAPI app initializer uses a test-scoped persist dir.

    This prevents collisions when tests import backend.main (which initializes Chroma).
    """
    original = os.environ.get("UNIFIED_PERSIST_DIR")
    skip_idx_original = os.environ.get("SKIP_INDEXING")
    os.environ["UNIFIED_PERSIST_DIR"] = session_chroma_dir
    # Speed up tests that import backend.main by skipping indexing on startup
    os.environ["SKIP_INDEXING"] = "1"
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("UNIFIED_PERSIST_DIR", None)
        else:
            os.environ["UNIFIED_PERSIST_DIR"] = original
        if skip_idx_original is None:
            os.environ.pop("SKIP_INDEXING", None)
        else:
            os.environ["SKIP_INDEXING"] = skip_idx_original
