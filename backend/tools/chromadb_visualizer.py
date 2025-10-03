#!/usr/bin/env python3
# type: ignore
"""
ChromaDB Visualizer - A simple web interface to explore ChromaDB collections
"""


import chromadb
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

# ChromaDB client
client = chromadb.HttpClient(host="localhost", port=8001)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ChromaDB Visualizer</title>
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
    </style>
</head>
<body>
    <div class="container">
        <h1>ChromaDB Visualizer</h1>

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
            <input type="text" id="search-input" placeholder="Enter search query...">
            <button onclick="searchDocuments()">Search</button>
        </div>

        <div class="documents" id="documents"></div>
    </div>

    <script>
        let currentCollection = null;

        async function loadCollections() {
            const response = await fetch('/api/collections');
            const collections = await response.json();

            const buttonsDiv = document.getElementById('collection-buttons');
            buttonsDiv.innerHTML = '';

            collections.forEach(collection => {
                const btn = document.createElement('button');
                btn.className = 'collection-btn';
                btn.textContent = collection.name;
                btn.onclick = () => selectCollection(collection.name);
                buttonsDiv.appendChild(btn);
            });
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
            const response = await fetch(`/api/collections/${name}/stats`);
            const stats = await response.json();

            document.getElementById('stats-content').innerHTML = `
                <p><strong>Total Documents:</strong> ${stats.count}</p>
                <p><strong>Metadata Keys:</strong> ${stats.metadata_keys.join(', ') || 'None'}</p>
            `;
        }

        async function loadDocuments(name, query = null) {
            const documentsDiv = document.getElementById('documents');
            documentsDiv.innerHTML = '<div class="loading">Loading documents...</div>';

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
    collections = client.list_collections()
    return jsonify([{"name": c.name, "id": str(c.id)} for c in collections])


@app.route("/api/collections/<name>/stats")
def get_collection_stats(name):
    collection = client.get_collection(name)
    count = collection.count()

    # Get sample documents to find metadata keys
    metadata_keys = set()
    if count > 0:
        sample = collection.get(limit=10)
        for metadata in sample["metadatas"]:
            if metadata:
                metadata_keys.update(metadata.keys())

    return jsonify({"count": count, "metadata_keys": list(metadata_keys)})


@app.route("/api/collections/<name>/documents")
def get_documents(name):
    collection = client.get_collection(name)
    query = request.args.get("query")

    if query:
        # Search documents
        results = collection.query(query_texts=[query], n_results=10)
        return jsonify(
            {
                "documents": [
                    {
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                    }
                    for i in range(len(results["ids"][0]))
                ],
                "distances": results["distances"][0] if results["distances"] else None,
            }
        )
    else:
        # Get recent documents
        data = collection.get(limit=20)
        return jsonify(
            {
                "documents": [
                    {"id": data["ids"][i], "document": data["documents"][i], "metadata": data["metadatas"][i]}
                    for i in range(len(data["ids"]))
                ]
            }
        )


if __name__ == "__main__":
    print("Starting ChromaDB Visualizer on http://localhost:5555")
    app.run(debug=True, port=5555)
