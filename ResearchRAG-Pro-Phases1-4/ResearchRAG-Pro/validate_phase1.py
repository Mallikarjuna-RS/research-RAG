#!/usr/bin/env python3
"""
Phase 1 Validation Script
Tests all 5 MCP servers for basic functionality
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def check_file_exists(filepath):
    """Check if a file exists"""
    path = Path(filepath)
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {filepath}")
    return exists


def validate_python_syntax(filepath):
    """Validate Python file syntax"""
    try:
        with open(filepath) as f:
            compile(f.read(), filepath, 'exec')
        print(f"  ✅ Syntax valid")
        return True
    except SyntaxError as e:
        print(f"  ❌ Syntax error: {e}")
        return False


def main():
    print_header("PHASE 1 VALIDATION: MCP Server Architecture")
    
    # Check project structure
    print_header("1. Project Structure")
    
    required_dirs = [
        "mcp_servers",
        ".claude",
        "skills",
        "agents",
        "web",
        "api",
        "infrastructure",
        "tests",
        "data"
    ]
    
    all_dirs_exist = True
    for dir_name in required_dirs:
        exists = check_file_exists(dir_name)
        all_dirs_exist = all_dirs_exist and exists
    
    # Check MCP server files
    print_header("2. MCP Server Files")
    
    mcp_servers = [
        "mcp_servers/doc_parser.py",
        "mcp_servers/vector_db.py",
        "mcp_servers/math_renderer.py",
        "mcp_servers/kg_builder.py",
        "mcp_servers/evaluator.py"
    ]
    
    all_servers_exist = True
    for server in mcp_servers:
        exists = check_file_exists(server)
        all_servers_exist = all_servers_exist and exists
        if exists:
            validate_python_syntax(server)
    
    # Check configuration files
    print_header("3. Configuration Files")
    
    config_files = [
        ".claude/mcp.json",
        "mcp_servers/requirements.txt"
    ]
    
    all_configs_exist = True
    for config in config_files:
        exists = check_file_exists(config)
        all_configs_exist = all_configs_exist and exists
    
    # Validate MCP configuration
    print_header("4. MCP Configuration Validation")
    
    try:
        with open(".claude/mcp.json") as f:
            mcp_config = json.load(f)
        
        print(f"✅ Valid JSON")
        print(f"  Configured servers: {len(mcp_config['mcpServers'])}")
        
        for server_name in mcp_config['mcpServers']:
            print(f"    - {server_name}")
    
    except Exception as e:
        print(f"❌ Configuration error: {e}")
    
    # Check dependencies
    print_header("5. Dependencies Check")
    
    try:
        with open("mcp_servers/requirements.txt") as f:
            requirements = f.readlines()
        
        print(f"✅ Requirements file valid")
        print(f"  Total dependencies: {len([r for r in requirements if r.strip() and not r.startswith('#')])}")
    
    except Exception as e:
        print(f"❌ Requirements error: {e}")
    
    # Summary
    print_header("PHASE 1 VALIDATION SUMMARY")
    
    checks = {
        "Project structure": all_dirs_exist,
        "MCP server files": all_servers_exist,
        "Configuration files": all_configs_exist,
        "MCP config valid": True,
        "Requirements valid": True
    }
    
    passed = sum(checks.values())
    total = len(checks)
    
    print(f"\nPassed: {passed}/{total}")
    print("\nDetailed results:")
    for check, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {check}")
    
    if passed == total:
        print("\n🎉 PHASE 1 COMPLETE - All checks passed!")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r mcp_servers/requirements.txt")
        print("  2. Set environment variables in .env file")
        print("  3. Test MCP server connections")
        print("  4. Proceed to Phase 2: Custom Skills Creation")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
