#!/bin/bash
set -e

# ============================================================================
# RAG Multi-Tenant Project Conflict Resolution Script
# ============================================================================
# This script fixes conflicts between this project and the parent nickberens
# project to allow both to run simultaneously without interference.
#
# Changes made:
# 1. Container names: nickberens → rag-backend
# 2. Network names: nickberens-network → rag-network
# 3. Database ports: 5432 → 5433, 6379 → 6380
# 4. Backend API port: 8000 → 8001
# 5. Frontend dev port: 4321 → 4322
# 6. Clean old SQLite files from parent project
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 RAG Multi-Tenant Project Conflict Resolution"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo ""

# Backup function
backup_file() {
    local file=$1
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup-$(date +%Y%m%d-%H%M%S)"
        echo "  ✓ Backed up: $file"
    fi
}

# ============================================================================
# 1. UPDATE PACKAGE.JSON - Container/Network Names & Ports
# ============================================================================
echo "📦 [1/7] Updating package.json..."
PACKAGE_JSON="$PROJECT_ROOT/package.json"

if [ -f "$PACKAGE_JSON" ]; then
    backup_file "$PACKAGE_JSON"

    # Update container names
    sed -i '' 's/--name nickberens/--name rag-backend/g' "$PACKAGE_JSON"
    sed -i '' 's/podman stop nickberens/podman stop rag-backend/g' "$PACKAGE_JSON"
    sed -i '' 's/podman logs -f nickberens/podman logs -f rag-backend/g' "$PACKAGE_JSON"

    # Update network names
    sed -i '' 's/--network nickberens-network/--network rag-network/g' "$PACKAGE_JSON"

    # Update backend port 8000 → 8001
    sed -i '' 's/-p 8000:8000/-p 8001:8000/g' "$PACKAGE_JSON"

    # Update package name
    sed -i '' 's/"name": "nickberens"/"name": "rag-multi-tenant"/g' "$PACKAGE_JSON"

    # Update Astro dev port 4321 → 4322
    sed -i '' 's/"dev": "astro dev"/"dev": "astro dev --port 4322"/g' "$PACKAGE_JSON"

    echo "  ✓ Container names: nickberens → rag-backend"
    echo "  ✓ Network names: nickberens-network → rag-network"
    echo "  ✓ Backend port: 8000 → 8001"
    echo "  ✓ Frontend port: 4321 → 4322"
    echo "  ✓ Package name: nickberens → rag-multi-tenant"
else
    echo "  ⚠ package.json not found"
fi
echo ""

# ============================================================================
# 2. UPDATE DOCKER-COMPOSE.YML - Database Ports
# ============================================================================
echo "🐳 [2/7] Updating docker-compose.yml..."
DOCKER_COMPOSE="$PROJECT_ROOT/docker-compose.yml"

if [ -f "$DOCKER_COMPOSE" ]; then
    backup_file "$DOCKER_COMPOSE"

    # Update PostgreSQL port
    sed -i '' 's/- "5432:5432"/- "5433:5432"/g' "$DOCKER_COMPOSE"

    # Update Redis port
    sed -i '' 's/- "6379:6379"/- "6380:6379"/g' "$DOCKER_COMPOSE"

    echo "  ✓ PostgreSQL port: 5432 → 5433"
    echo "  ✓ Redis port: 6379 → 6380"
else
    echo "  ⚠ docker-compose.yml not found"
fi
echo ""

# ============================================================================
# 3. UPDATE .ENV FILE - Database URLs
# ============================================================================
echo "🔐 [3/7] Updating .env file..."
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    backup_file "$ENV_FILE"

    # Update DATABASE_URL port
    sed -i '' 's/@postgres:5432/@postgres:5433/g' "$ENV_FILE"
    sed -i '' 's/@localhost:5432/@localhost:5433/g' "$ENV_FILE"

    # Update REDIS_URL port
    sed -i '' 's/redis:\/\/localhost:6379/redis:\/\/localhost:6380/g' "$ENV_FILE"

    echo "  ✓ DATABASE_URL port: 5432 → 5433"
    echo "  ✓ REDIS_URL port: 6379 → 6380"
else
    echo "  ⚠ .env file not found"
fi
echo ""

# ============================================================================
# 4. UPDATE FRONTEND API URLS
# ============================================================================
echo "🎨 [4/7] Updating frontend API URLs..."

# Update ChatBot.vue
CHATBOT_VUE="$PROJECT_ROOT/src/components/ChatBot.vue"
if [ -f "$CHATBOT_VUE" ]; then
    backup_file "$CHATBOT_VUE"
    sed -i '' 's|http://localhost:8000|http://localhost:8001|g' "$CHATBOT_VUE"
    echo "  ✓ Updated ChatBot.vue"
fi

# Update ChatBotWelcome.vue
CHATBOT_WELCOME="$PROJECT_ROOT/src/components/ChatBotWelcome.vue"
if [ -f "$CHATBOT_WELCOME" ]; then
    backup_file "$CHATBOT_WELCOME"
    sed -i '' 's|http://localhost:8000|http://localhost:8001|g' "$CHATBOT_WELCOME"
    echo "  ✓ Updated ChatBotWelcome.vue"
fi

# Update useChatAPI.js
CHAT_API_JS="$PROJECT_ROOT/src/composables/useChatAPI.js"
if [ -f "$CHAT_API_JS" ]; then
    backup_file "$CHAT_API_JS"
    sed -i '' 's|http://localhost:8000|http://localhost:8001|g' "$CHAT_API_JS"
    echo "  ✓ Updated useChatAPI.js"
fi

echo ""

# ============================================================================
# 5. CREATE PODMAN NETWORK
# ============================================================================
echo "🌐 [5/7] Creating Podman network..."
if command -v podman &> /dev/null; then
    if podman network exists rag-network 2>/dev/null; then
        echo "  ✓ Network 'rag-network' already exists"
    else
        podman network create rag-network 2>/dev/null && \
            echo "  ✓ Created network 'rag-network'" || \
            echo "  ⚠ Could not create network (may need to run manually)"
    fi
else
    echo "  ℹ Podman not found - skipping network creation"
    echo "    Run manually: podman network create rag-network"
fi
echo ""

# ============================================================================
# 6. CLEAN OLD SQLITE FILES
# ============================================================================
echo "🧹 [6/7] Cleaning old SQLite files..."
LOGS_DIR="$PROJECT_ROOT/backend/logs"

if [ -d "$LOGS_DIR" ]; then
    # Count files before cleanup
    DB_COUNT=$(find "$LOGS_DIR" -name "*.db" -o -name "*.db-wal" -o -name "*.db-shm" | wc -l | tr -d ' ')

    if [ "$DB_COUNT" -gt 0 ]; then
        echo "  Found $DB_COUNT SQLite database files to clean"

        # Create backup directory
        BACKUP_DIR="$LOGS_DIR/backup-$(date +%Y%m%d-%H%M%S)"
        mkdir -p "$BACKUP_DIR"

        # Move files to backup
        find "$LOGS_DIR" -maxdepth 1 \( -name "*.db" -o -name "*.db-wal" -o -name "*.db-shm" \) \
            -exec mv {} "$BACKUP_DIR/" \; 2>/dev/null || true

        echo "  ✓ Moved old SQLite files to: $BACKUP_DIR"
        echo "  ℹ Using PostgreSQL now - these SQLite files are obsolete"
    else
        echo "  ✓ No SQLite files to clean"
    fi
else
    echo "  ℹ Logs directory not found: $LOGS_DIR"
fi
echo ""

# ============================================================================
# 7. VERIFY CHANGES
# ============================================================================
echo "✅ [7/7] Verifying changes..."
echo ""

# Check package.json
if grep -q "rag-backend" "$PACKAGE_JSON" 2>/dev/null; then
    echo "  ✓ package.json: Container name updated"
else
    echo "  ✗ package.json: Container name NOT updated"
fi

if grep -q "rag-network" "$PACKAGE_JSON" 2>/dev/null; then
    echo "  ✓ package.json: Network name updated"
else
    echo "  ✗ package.json: Network name NOT updated"
fi

# Check docker-compose.yml
if grep -q "5433:5432" "$DOCKER_COMPOSE" 2>/dev/null; then
    echo "  ✓ docker-compose.yml: PostgreSQL port updated"
else
    echo "  ✗ docker-compose.yml: PostgreSQL port NOT updated"
fi

if grep -q "6380:6379" "$DOCKER_COMPOSE" 2>/dev/null; then
    echo "  ✓ docker-compose.yml: Redis port updated"
else
    echo "  ✗ docker-compose.yml: Redis port NOT updated"
fi

# Check .env
if grep -q "5433" "$ENV_FILE" 2>/dev/null; then
    echo "  ✓ .env: Database port updated"
else
    echo "  ✗ .env: Database port NOT updated"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Conflict Resolution Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Summary of Changes:"
echo "  • Container name:    nickberens → rag-backend"
echo "  • Network name:      nickberens-network → rag-network"
echo "  • Package name:      nickberens → rag-multi-tenant"
echo "  • Backend port:      8000 → 8001"
echo "  • Frontend port:     4321 → 4322"
echo "  • PostgreSQL port:   5432 → 5433"
echo "  • Redis port:        6379 → 6380"
echo "  • Old SQLite files:  Backed up and removed"
echo ""
echo "🚀 Next Steps:"
echo "  1. Start databases:  docker-compose up -d"
echo "  2. Start backend:    npm run backend:dev"
echo "  3. Start frontend:   npm run dev"
echo ""
echo "📁 Backup files created with .backup-TIMESTAMP extension"
echo "   You can safely delete these after verifying everything works."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
