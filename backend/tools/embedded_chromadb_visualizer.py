#!/usr/bin/env python3
# type: ignore
"""
Embedded ChromaDB Visualizer - A web interface to explore embedded ChromaDB collections
Works with local ChromaDB files instead of requiring a ChromaDB server
"""

import os

import chromadb
from flask import Flask, jsonify, render_template_string, request
from langchain_google_genai import GoogleGenerativeAIEmbeddings

app = Flask(__name__)

# Use the same embedded ChromaDB directory as your backend
CHROMA_DIR = "backend/.unified_chroma"

# Use the same embedding model as your backend
try:
    # Try to get the Google API key from environment
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=google_api_key)
        print("Using Google embeddings (models/embedding-001)")
    else:
        print("Warning: GOOGLE_API_KEY not found, using default embeddings")
        embeddings = None
except ImportError:
    print("Warning: langchain_google_genai not available, using default embeddings")
    embeddings = None

# ChromaDB client for embedded database
client = chromadb.PersistentClient(path=CHROMA_DIR)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ChromaDB Visualizer (Embedded)</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .status {
            background-color: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .collections {
            margin: 20px 0;
        }
        .collection-btn {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            cursor: pointer;
            border-radius: 4px;
        }
        .collection-btn:hover {
            background-color: #0056b3;
        }
        .collection-btn.active {
            background-color: #28a745;
        }
        .stats {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
        .documents {
            margin-top: 20px;
        }
        .document {
            border: 1px solid #ddd;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            background-color: #fff;
        }
        .document-id {
            font-weight: bold;
            color: #007bff;
        }
        .metadata {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .document-text {
            margin-top: 10px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
        }
        .search-box {
            margin: 20px 0;
        }
        .search-box input {
            width: 70%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .search-box button {
            padding: 10px 20px;
            font-size: 16px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .distance {
            color: #28a745;
            font-weight: bold;
        }
        .loading {
            text-align: center;
            color: #666;
            padding: 20px;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>ChromaDB Visualizer (Embedded)</h1>

        <div class="status">
            <strong>Data Source:</strong> backend/.unified_chroma (Your backend's embedded ChromaDB)
        </div>

        <div class="collections">
            <h2>Collections</h2>
            <div id="collection-buttons"></div>
        </div>

        <div class="stats" id="stats" style="display:none;">
            <h3>Collection Stats</h3>
            <div id="stats-content"></div>
        </div>

        <div class="search-box" id="search-box" style="display:none;">
            <h3>Search Documents</h3>
            <p><em>Note: Search functionality requires the same embedding model as your backend. Currently
            showing browse-only mode.</em></p>
            <input type="text" id="search-input" placeholder="Search disabled - browse documents below" disabled>
            <button onclick="searchDocuments()" disabled>Search (Disabled)</button>
        </div>

        <div class="documents" id="documents"></div>
    </div>

    <script>
        let currentCollection = null;

        async function loadCollections() {
            try {
                const response = await fetch('/api/collections');
                const collections = await response.json();

                const buttonsDiv = document.getElementById('collection-buttons');
                buttonsDiv.innerHTML = '';

                if (collections.length === 0) {
                    buttonsDiv.innerHTML = '<p class="error">No collections found. Make sure your backend has ' +
                        'created the ChromaDB database.</p>';
                    return;
                }

                collections.forEach(collection => {
                    const btn = document.createElement('button');
                    btn.className = 'collection-btn';
                    btn.textContent = collection.name;
                    btn.onclick = () => selectCollection(collection.name);
                    buttonsDiv.appendChild(btn);
                });
            } catch (error) {
                document.getElementById('collection-buttons').innerHTML =
                    '<p class="error">Error loading collections: ' + error.message + '</p>';
            }
        }

        async function selectCollection(name) {
            currentCollection = name;

            // Update button states
            document.querySelectorAll('.collection-btn').forEach(btn => {
                btn.classList.toggle('active', btn.textContent === name);
            });

            // Show stats and search
            document.getElementById('stats').style.display = 'block';
            document.getElementById('search-box').style.display = 'block';

            // Load collection data
            await loadCollectionStats(name);
            await loadDocuments(name);
        }

        async function loadCollectionStats(name) {
            try {
                const response = await fetch(`/api/collections/${name}/stats`);
                const stats = await response.json();

                document.getElementById('stats-content').innerHTML = `
                    <p><strong>Total Documents:</strong> ${stats.count}</p>
                    <p><strong>Metadata Keys:</strong> ${stats.metadata_keys.join(', ') || 'None'}</p>
                `;
            } catch (error) {
                document.getElementById('stats-content').innerHTML =
                    '<p class="error">Error loading stats: ' + error.message + '</p>';
            }
        }

        async function loadDocuments(name, query = null) {
            const documentsDiv = document.getElementById('documents');
            documentsDiv.innerHTML = '<div class="loading">Loading documents...</div>';

            try {
                let url = `/api/collections/${name}/documents`;
                if (query) {
                    url += `?query=${encodeURIComponent(query)}`;
                }

                const response = await fetch(url);
                const data = await response.json();

                documentsDiv.innerHTML = `<h3>${query ? 'Search Results' : 'Recent Documents'}</h3>`;

                if (data.documents.length === 0) {
                    documentsDiv.innerHTML += '<p>No documents found.</p>';
                    return;
                }

                data.documents.forEach((doc, idx) => {
                    const distance = data.distances ? data.distances[idx] : null;
                    const docDiv = document.createElement('div');
                    docDiv.className = 'document';
                    docDiv.innerHTML = `
                        <div class="document-id">ID: ${doc.id}</div>
                        ${distance !== null ?
                            `<div class="distance">Similarity Score: ${(1 - distance).toFixed(4)}</div>` :
                            ''}
                        <div class="metadata">Metadata: ${JSON.stringify(doc.metadata)}</div>
                        <div class="document-text">${doc.document}</div>
                    `;
                    documentsDiv.appendChild(docDiv);
                });
            } catch (error) {
                documentsDiv.innerHTML = '<p class="error">Error loading documents: ' + error.message + '</p>';
            }
        }

        async function searchDocuments() {
            const query = document.getElementById('search-input').value;
            if (query && currentCollection) {
                await loadDocuments(currentCollection, query);
            }
        }

        // Initialize
        loadCollections();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/collections")
def get_collections():
    try:
        collections = client.list_collections()
        return jsonify([{"name": c.name, "id": str(c.id)} for c in collections])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/collections/<name>/stats")
def get_collection_stats(name):
    try:
        collection = client.get_collection(name)
        count = collection.count()

        # Get sample documents to find metadata keys
        metadata_keys = set()
        if count > 0:
            sample = collection.get(limit=10)
            if sample["metadatas"]:
                for metadata in sample["metadatas"]:
                    if metadata:
                        metadata_keys.update(metadata.keys())

        return jsonify({"count": count, "metadata_keys": list(metadata_keys)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/collections/<name>/documents")
def get_documents(name):
    try:
        collection = client.get_collection(name)
        query = request.args.get("query")

        if query:
            # Search is disabled due to embedding model mismatch
            return jsonify(
                {
                    "documents": [],
                    "error": "Search functionality disabled due to embedding model requirements. Use your "
                    "backend's /query endpoint for search.",
                }
            )
        else:
            # Get all documents (or a large sample)
            data = collection.get(limit=100)  # Increased limit to show more documents
            documents = []
            if data["ids"]:
                for i in range(len(data["ids"])):
                    documents.append(
                        {
                            "id": data["ids"][i],
                            "document": data["documents"][i] if data["documents"] else "",
                            "metadata": data["metadatas"][i] if data["metadatas"] else {},
                        }
                    )

            return jsonify({"documents": documents})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
def get_status():
    try:
        collections = client.list_collections()
        chroma_exists = os.path.exists(CHROMA_DIR)
        return jsonify(
            {
                "chroma_dir": CHROMA_DIR,
                "chroma_exists": chroma_exists,
                "collections_count": len(collections),
                "collections": [c.name for c in collections],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Starting Embedded ChromaDB Visualizer on http://localhost:5556")
    print(f"Data source: {os.path.abspath(CHROMA_DIR)}")
    app.run(debug=True, port=5556)
