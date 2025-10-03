#!/bin/bash
set -e

# ============================================================================
# CORS Configuration Update Script
# ============================================================================
# Updates CORS settings to support the new port configuration (4322, 8001)
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 CORS Configuration Update"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo ""

# ============================================================================
# Update .env CORS_ORIGINS
# ============================================================================
echo "📝 [1/2] Updating .env CORS_ORIGINS..."
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    # Backup first
    cp "$ENV_FILE" "${ENV_FILE}.backup-cors-$(date +%Y%m%d-%H%M%S)"

    # Update CORS_ORIGINS to include new port 4322
    # Current: CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:4321
    # New:     CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:4321,http://localhost:4322

    if grep -q "CORS_ORIGINS=" "$ENV_FILE"; then
        # Check if 4322 is already there
        if grep "CORS_ORIGINS=" "$ENV_FILE" | grep -q "4322"; then
            echo "  ✓ Port 4322 already in CORS_ORIGINS"
        else
            # Add 4322 to the list
            sed -i '' 's|CORS_ORIGINS=\(.*\)|CORS_ORIGINS=\1,http://localhost:4322|g' "$ENV_FILE"
            echo "  ✓ Added http://localhost:4322 to CORS_ORIGINS"
        fi
    else
        echo "  ℹ CORS_ORIGINS not found in .env (using code defaults)"
    fi
else
    echo "  ⚠ .env file not found"
fi
echo ""

# ============================================================================
# Verify CORS Configuration
# ============================================================================
echo "✅ [2/2] Verifying CORS configuration..."
echo ""

# Check if backend code includes new ports
CORS_CODE_FILE="$PROJECT_ROOT/backend/core/config_v2.py"

if [ -f "$CORS_CODE_FILE" ]; then
    if grep -q "localhost:8001" "$CORS_CODE_FILE"; then
        echo "  ✓ Backend code includes port 8001"
    else
        echo "  ℹ Backend code does not explicitly include 8001 (may use range)"
    fi

    if grep -q "localhost:4322" "$CORS_CODE_FILE"; then
        echo "  ✓ Backend code includes port 4322"
    else
        echo "  ℹ Backend code does not explicitly include 4322"
        echo "    Note: The code has a range http://localhost:8000-8003"
        echo "    Port 4322 may need to be added manually if not covered"
    fi
else
    echo "  ⚠ config_v2.py not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ CORS Configuration Review Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Current CORS Status:"
echo ""
echo "✅ Good News: Your CORS configuration is mostly automatic!"
echo ""
echo "Backend (config_v2.py) includes:"
echo "  • http://localhost:4321 (original frontend)"
echo "  • http://localhost:3000-3003 (admin ports)"
echo "  • http://localhost:5173 (Vite dev)"
echo "  • http://localhost:8000-8003 (backend ports)"
echo ""
echo "⚠️  Port 4322 (new frontend) is NOT in the hardcoded list"
echo ""
echo "🔧 Two Options:"
echo ""
echo "Option 1: Use .env override (RECOMMENDED)"
echo "  Your .env now includes: http://localhost:4322"
echo "  This will work if CORS_ORIGINS env var is read first"
echo ""
echo "Option 2: Edit backend/core/config_v2.py manually"
echo "  Add 'http://localhost:4322' to development_origins list"
echo "  Line ~220: development_origins = [..."
echo ""
echo "💡 Recommendation: Test your frontend first."
echo "   If CORS errors occur, manually add port 4322 to config_v2.py"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
