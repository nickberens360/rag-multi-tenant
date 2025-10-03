#!/usr/bin/env python3
"""
Simple startup script for the RAG Admin Dashboard backend.
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    # Set default environment variables
    os.environ.setdefault("ADMIN_PORT", "8001")

    # Admin dashboard uses session-based authentication
    print("🔐 Admin authentication: Session-based (no tokens required)")

    try:
        import uvicorn

        port = int(os.environ.get("ADMIN_PORT", 8000))

        print("🚀 Starting RAG Admin Dashboard (Integrated Backend)...")
        print(f"   Backend API: http://localhost:{port}/admin/api")
        print(f"   API Docs: http://localhost:{port}/docs")
        print(f"   Health Check: http://localhost:{port}/admin/api/health")
        print()

        print("📊 Dashboard will be available at the frontend URL after building")
        print("🔑 Login with admin credentials to access the dashboard")
        print()

        uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True, log_level="info")

    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Install with: pip install fastapi uvicorn sqlite3 python-multipart")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
