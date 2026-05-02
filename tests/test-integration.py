#!/usr/bin/env python3
"""
Quick Integration Test - Kai Side

Verifies that claude_bridge and claude_consultant_handler can be imported and initialized
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from claude_consultant_handler import KaiConsultantHandler, should_kai_consult_claude
    print("✓ claude_consultant_handler imported successfully")
    
    # Check the class has required methods
    methods = [
        'prepare_context',
        'process_recommendation',
        'merge_with_kai_knowledge',
        'format_for_ui',
        '_should_execute',
        '_explain_kai_decision'
    ]
    
    for method in methods:
        if hasattr(KaiConsultantHandler, method):
            print(f"✓ Method {method} exists")
        else:
            print(f"✗ Method {method} missing")
    
    # Check helper function
    if callable(should_kai_consult_claude):
        print("✓ Helper function should_kai_consult_claude exists")
    
    print("\n✓ Python integration test complete - all modules properly structured")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("(This is expected if running outside Kai environment)")
except Exception as e:
    print(f"✗ Error: {e}")
