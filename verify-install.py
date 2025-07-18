#!/usr/bin/env python3
"""
Auto-SBM Installation Verification Script
Run this script to verify your auto-sbm installation is working correctly.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_command(cmd, description):
    """Check if a command is available and working."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ {description}: OK")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ {description}: FAILED - {e}")
        return False

def check_import(module_name, description):
    """Check if a Python module can be imported."""
    try:
        __import__(module_name)
        print(f"✅ {description}: OK")
        return True
    except ImportError as e:
        print(f"❌ {description}: FAILED - {e}")
        return False

def check_file(file_path, description):
    """Check if a file exists."""
    if Path(file_path).exists():
        print(f"✅ {description}: OK")
        return True
    else:
        print(f"❌ {description}: MISSING")
        return False

def main():
    print("🔍 Auto-SBM Installation Verification")
    print("=" * 40)
    
    checks_passed = 0
    total_checks = 0
    
    # System requirements
    print("\n📋 System Requirements:")
    total_checks += 1
    if check_command(["python3", "--version"], "Python 3"):
        checks_passed += 1
        
    total_checks += 1
    if check_command(["git", "--version"], "Git"):
        checks_passed += 1
        
    total_checks += 1
    if check_command(["gh", "--version"], "GitHub CLI"):
        checks_passed += 1
    
    # Python dependencies
    print("\n📦 Python Dependencies:")
    dependencies = [
        ("pydantic", "Pydantic v2"),
        ("pydantic_settings", "Pydantic Settings"),
        ("rich", "Rich UI"),
        ("click", "Click CLI"),
        ("git", "GitPython"),
    ]
    
    for module, description in dependencies:
        total_checks += 1
        if check_import(module, description):
            checks_passed += 1
    
    # Auto-SBM specific
    print("\n🔧 Auto-SBM Components:")
    total_checks += 1
    if check_import("auto_sbm", "Auto-SBM package"):
        checks_passed += 1
        
    total_checks += 1
    if check_import("auto_sbm.config", "Auto-SBM config"):
        checks_passed += 1
    
    # Configuration files
    print("\n⚙️  Configuration:")
    total_checks += 1
    if check_file(".env.example", ".env.example template"):
        checks_passed += 1
        
    total_checks += 1
    if check_file("pyproject.toml", "pyproject.toml"):
        checks_passed += 1
    
    # Environment variables
    print("\n🌍 Environment:")
    if os.getenv("GITHUB_TOKEN"):
        print("✅ GITHUB_TOKEN: Configured")
        checks_passed += 1
    else:
        print("⚠️  GITHUB_TOKEN: Not set (configure in .env)")
    total_checks += 1
    
    # CLI availability
    print("\n🚀 CLI Commands:")
    total_checks += 1
    if check_command(["sbm", "--help"], "Global sbm command"):
        checks_passed += 1
    else:
        # Try module execution as fallback
        total_checks += 1
        if check_command(["python", "-m", "auto_sbm.main", "--help"], "Module execution"):
            checks_passed += 1
    
    # Summary
    print("\n" + "=" * 40)
    print(f"📊 Summary: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("🎉 All checks passed! Auto-SBM is ready to use.")
        print("\n🚀 Try running: sbm --help")
        return 0
    else:
        print("⚠️  Some checks failed. Please review the output above.")
        if checks_passed < total_checks * 0.8:
            print("💡 Try running setup.sh to fix common issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
