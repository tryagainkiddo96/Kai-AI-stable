#!/bin/bash
#==============================================================================
# KAI UNIFIED LAUNCHER
# Cross-platform launcher for Kai AI Dashboard
# Works on: Linux, macOS, WSL, Git Bash, Cygwin
#==============================================================================

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              KAI AI UNIFIED LAUNCHER                         ║"
echo "║         Beautiful Terminal UI for Kai AI                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Detect environment
detect_env() {
    if [ -f /proc/version ] && grep -qi microsoft /proc/version; then
        echo "📍 Environment: WSL (Windows Subsystem for Linux)"
        return "wsl"
    elif [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "📍 Environment: $PRETTY_NAME ($NAME)"
        return "linux"
    elif [ "$(uname)" = "Darwin" ]; then
        echo "📍 Environment: macOS"
        return "macos"
    elif [ "$OSTYPE" = "cygwin" ]; then
        echo "📍 Environment: Cygwin"
        return "cygwin"
    else
        echo "📍 Environment: Unknown"
        return "unknown"
    fi
}

# Check Python installation
check_python() {
    echo ""
    echo "🔍 Checking Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Python not found. Please install Python 3.10+"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    echo "✅ Python found: $PYTHON_VERSION"
    
    # Check for required modules
    echo "🔍 Checking required packages..."
    
    if $PYTHON_CMD -c "import rich" &> /dev/null; then
        echo "✅ rich module installed"
    else
        echo "📦 Installing rich..."
        $PYTHON_CMD -m pip install rich -q
    fi
}

# Check for Ollama (optional)
check_ollama() {
    echo ""
    echo "🔍 Checking Ollama..."
    
    if command -v ollama &> /dev/null; then
        echo "✅ Ollama found"
        if curl -s http://localhost:11434/api/tags &> /dev/null; then
            echo "✅ Ollama service is running"
        else
            echo "⚠️  Ollama installed but not running"
            echo "   Run 'ollama serve' to start it"
        fi
    else
        echo "⚠️  Ollama not found (optional)"
        echo "   Install from https://ollama.ai for local AI models"
    fi
}

# Launch Kai Dashboard
launch_kai() {
    echo ""
    echo "🚀 Launching Kai Dashboard..."
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Set PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT"
    
    # Pass through any additional arguments
    $PYTHON_CMD kai_dashboard.py "$@"
}

# Main execution
main() {
    ENV=$(detect_env)
    check_python
    check_ollama
    launch_kai "$@"
}

# Run main with all arguments
main "$@"
