#!/usr/bin/env python3
"""Debug script to inspect ChromaDB vector store tenant metadata."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from chromadb import PersistentClient

# Load ChromaDB from default location
chroma_dir = backend_path / ".unified_chroma"
client = PersistentClient(path=str(chroma_dir))
collection = client.get_or_create_collection(name="unified_knowledge", metadata={"hnsw:space": "cosine"})

# Get all documents
results = collection.get(limit=10, include=["metadatas", "documents"])

print(f"Total documents in collection: {collection.count()}\n")
print("=" * 80)

# Show first 10 documents with metadata
for i, (doc_id, metadata, content) in enumerate(zip(results["ids"], results["metadatas"], results["documents"]), 1):
    print(f"\nDocument {i}:")
    print(f"  ID: {doc_id}")
    print(f"  Content preview: {content[:100]}...")
    print(f"  Metadata:")
    for key, value in metadata.items():
        if key in ["tenant_id", "tenant_slug", "scope", "source"]:
            print(f"    {key}: {value}")
    print("-" * 80)
