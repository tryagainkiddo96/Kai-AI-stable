#!/bin/bash
#==============================================================================
# KAI GROQ LAUNCHER
# Launch Kai with Groq cloud API
#==============================================================================

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           KAI AI - GROQ CLOUD MODE                        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check for Groq API key
if [ -z "$GROQ_API_KEY" ]; then
    echo "⚠️  GROQ_API_KEY not set"
    echo "   Please set your Groq API key:"
    echo "   export GROQ_API_KEY=your_api_key"
    echo ""
    echo "   Get a free key at: https://console.groq.com"
    exit 1
fi

# Change to project root
cd "$PROJECT_ROOT"

# Set environment
export PYTHONPATH="$PROJECT_ROOT"
export KAI_PROVIDER="groq"
export KAI_MODEL="llama-3.1-8b-instant"

echo "Provider: $KAI_PROVIDER"
echo "Model: $KAI_MODEL"
echo ""

# Launch
python kai_dashboard.py
