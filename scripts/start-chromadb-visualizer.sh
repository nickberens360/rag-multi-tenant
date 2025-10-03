#!/bin/bash
# Start ChromaDB and Visualizer

echo "Starting ChromaDB..."
pkill -f "chroma run" 2>/dev/null
nohup chroma run --path backend/.chroma --port 8001 > /tmp/chroma.log 2>&1 &
echo "ChromaDB started on port 8001"

echo "Waiting for ChromaDB to initialize..."
sleep 3

echo "Starting ChromaDB Visualizer..."
pkill -f "chromadb_visualizer.py" 2>/dev/null
source .venv/bin/activate
nohup python backend/tools/chromadb_visualizer.py > /tmp/visualizer.log 2>&1 &
echo "Visualizer started on http://localhost:5555"

echo ""
echo "Services started!"
echo "- ChromaDB API: http://localhost:8001"
echo "- ChromaDB Visualizer: http://localhost:5555"
echo ""
echo "Logs:"
echo "- ChromaDB: /tmp/chroma.log"
echo "- Visualizer: /tmp/visualizer.log"
echo ""
echo "To stop: pkill -f 'chroma run' && pkill -f 'chromadb_visualizer'"
