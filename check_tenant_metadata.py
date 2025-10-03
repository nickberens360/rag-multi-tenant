#!/usr/bin/env python3
"""Check if ChromaDB documents have tenant_id metadata."""

import sys
from pathlib import Path

backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Initialize
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
vector_store = Chroma(
    collection_name="langchain", embedding_function=embeddings, persist_directory="backend/.unified_chroma"
)

# Get some documents
docs_and_scores = vector_store.similarity_search_with_score("contact", k=10)

print(f"Checking {len(docs_and_scores)} documents for tenant metadata:\n")

tenant_counts = {}
for doc, score in docs_and_scores:
    tenant_id = doc.metadata.get("tenant_id", "NONE")
    source = doc.metadata.get("source", "unknown")[:60]

    if tenant_id not in tenant_counts:
        tenant_counts[tenant_id] = 0
    tenant_counts[tenant_id] += 1

    print(f"tenant_id: {tenant_id[:36] if tenant_id != 'NONE' else 'NONE':36} | source: {source}")

print(f"\n{'='*80}")
print("Summary:")
for tid, count in sorted(tenant_counts.items()):
    print(f"  {tid}: {count} documents")
