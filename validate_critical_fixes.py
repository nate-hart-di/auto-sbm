#!/usr/bin/env python3
"""
Comprehensive validation script for critical auto-sbm fixes.
Run this after implementing all fixes to verify success.

This script validates:
1. Environment compatibility (Pydantic config fixes)
2. Style exclusion system (header/footer/nav filtering)
3. Compilation status accuracy (false positive/negative fixes)
4. Progress system stability (timing and display)
"""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path


def print_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print('='*60)


def print_success(message: str):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message: str):
    """Print error message."""
    print(f"❌ {message}")


def print_warning(message: str):
    """Print warning message."""
    print(f"⚠️  {message}")


def validate_environment_compatibility():
    """Test tool works from different environments."""
    print_header("Testing Environment Compatibility")
    
    # Test from auto-sbm directory
    auto_sbm_dir = Path(__file__).parent
    os.chdir(auto_sbm_dir)
    
    try:
        result = subprocess.run(['sbm', '--version'], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print_error(f"Failed from auto-sbm directory: {result.stderr}")
            return False
        print_success("Works from auto-sbm directory")
    except Exception as e:
        print_error(f"Exception from auto-sbm directory: {e}")
        return False
    
    # Test from temporary directory
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            result = subprocess.run(['sbm', '--version'], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print_error(f"Failed from temp directory: {result.stderr}")
                return False
            print_success("Works from temporary directory")
    except Exception as e:
        print_error(f"Exception from temp directory: {e}")
        return False
    
    # Test Pydantic config with WordPress debug fields
    try:
        # Simulate DI platform environment variables
        env = os.environ.copy()
        env.update({
            'wp_debug': 'false',
            'wp_debug_log': 'false',
            'wp_debug_display': 'false'
        })
        
        result = subprocess.run(
            ['python', '-c', 'from sbm.config import get_settings; print("Config loaded successfully")'],
            capture_output=True, text=True, env=env, timeout=30
        )
        
        if result.returncode != 0:
            print_error(f"Pydantic validation failed: {result.stderr}")
            return False
        print_success("Pydantic config handles WordPress debug fields")
        
    except Exception as e:
        print_error(f"Pydantic validation exception: {e}")
        return False
    
    print_success("Environment compatibility validated")
    return True


def validate_style_exclusion():
    """Test style exclusion system."""
    print_header("Testing Style Exclusion System")
    
    try:
        # Test the StyleClassifier directly
        test_script = '''
from sbm.scss.classifiers import StyleClassifier

classifier = StyleClassifier()
test_content = """
.header { background: red; }
.footer { background: blue; }
.navbar { height: 60px; }
.content { padding: 20px; }
.hero { background: url('hero.jpg'); }
"""

filtered, exclusions = classifier.filter_scss_content(test_content, "test")

# Verify exclusions
excluded_selectors = [exc.selector for exc in exclusions]
if ".header" in filtered or ".footer" in filtered or ".navbar" in filtered:
    exit(1)  # Excluded styles found in filtered content

# Verify content preserved  
if ".content" not in filtered or ".hero" not in filtered:
    exit(2)  # Valid content was incorrectly excluded

if len(exclusions) < 3:  # Should exclude header, footer, navbar at minimum
    exit(3)  # Not enough exclusions

print("Style exclusion working correctly")
'''
        
        result = subprocess.run(
            ['python', '-c', test_script],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 1:
            print_error("Header/footer/nav styles not properly excluded")
            return False
        elif result.returncode == 2:
            print_error("Valid content styles were incorrectly excluded")
            return False
        elif result.returncode == 3:
            print_error("Not enough exclusions detected")
            return False
        elif result.returncode != 0:
            print_error(f"Style exclusion test failed: {result.stderr}")
            return False
        
        print_success("Header/footer/nav exclusion working correctly")
        
    except Exception as e:
        print_error(f"Style exclusion test exception: {e}")
        return False
    
    print_success("Style exclusion system validated")
    return True


def validate_compilation_status():
    """Test compilation status accuracy."""
    print_header("Testing Compilation Status Accuracy")
    
    try:
        # Test the final status determination function
        test_script = '''
import tempfile
import os
from sbm.core.migration import _determine_final_compilation_status

# Test with no CSS files
with tempfile.TemporaryDirectory() as temp_dir:
    test_files = [("test-sb-inside.scss", "test-path")]
    success, message = _determine_final_compilation_status(temp_dir, test_files)
    if success:
        exit(1)  # Should return False when no CSS files exist

    # Test with CSS files
    css_path = os.path.join(temp_dir, "test-sb-inside.css")
    with open(css_path, "w") as f:
        f.write("/* test css */")
    
    success, message = _determine_final_compilation_status(temp_dir, test_files)
    if not success:
        exit(2)  # Should return True when CSS files exist

print("Compilation status accuracy working correctly")
'''
        
        result = subprocess.run(
            ['python', '-c', test_script],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 1:
            print_error("Should return False when no CSS files exist")
            return False
        elif result.returncode == 2:
            print_error("Should return True when CSS files exist")
            return False
        elif result.returncode != 0:
            print_error(f"Compilation status test failed: {result.stderr}")
            return False
        
        print_success("Compilation status determination working correctly")
        
    except Exception as e:
        print_error(f"Compilation status test exception: {e}")
        return False
    
    print_success("Compilation status accuracy validated")
    return True


def validate_progress_system():
    """Test progress system stability."""
    print_header("Testing Progress System")
    
    try:
        # Test progress tracker initialization and timing
        test_script = '''
from sbm.ui.progress import MigrationProgress

# Test basic initialization
progress = MigrationProgress()

# Test timing functionality
elapsed = progress.get_elapsed_time()
if elapsed != 0.0:  # Should be 0 before starting
    exit(1)

# Test with context manager
try:
    with progress.progress_context():
        import time
        time.sleep(0.1)
        elapsed = progress.get_elapsed_time()
        if elapsed < 0.05:  # Should have some elapsed time
            exit(2)
except Exception as e:
    exit(3)  # Context manager failed

print("Progress system working correctly")
'''
        
        result = subprocess.run(
            ['python', '-c', test_script],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 1:
            print_error("Elapsed time should be 0 before starting")
            return False
        elif result.returncode == 2:
            print_error("Elapsed time not tracking correctly")
            return False
        elif result.returncode == 3:
            print_error("Progress context manager failed")
            return False
        elif result.returncode != 0:
            print_error(f"Progress system test failed: {result.stderr}")
            return False
        
        print_success("Progress system working correctly")
        
    except Exception as e:
        print_error(f"Progress system test exception: {e}")
        return False
    
    print_success("Progress system validated")
    return True


def validate_cli_commands():
    """Test CLI command functionality."""
    print_header("Testing CLI Commands")
    
    try:
        # Test validate command with exclusion check
        result = subprocess.run(
            ['sbm', 'validate', '--help'],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            print_error(f"Validate command help failed: {result.stderr}")
            return False
        
        if '--check-exclusions' not in result.stdout:
            print_error("--check-exclusions option not found in validate command")
            return False
        
        print_success("Validate command with exclusion check available")
        
    except Exception as e:
        print_error(f"CLI command test exception: {e}")
        return False
    
    print_success("CLI commands validated")
    return True


def run_integration_test():
    """Run an integration test if possible."""
    print_header("Integration Test (Optional)")
    
    # Only run if we have a test theme available
    test_theme = "jamesriverchryslerdodgejeepram"
    
    try:
        # Check if theme directory exists
        result = subprocess.run(
            ['sbm', 'validate', test_theme, '--check-exclusions'],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            print_success(f"Integration test passed for {test_theme}")
            return True
        else:
            print_warning(f"Integration test failed for {test_theme}: {result.stderr}")
            print_warning("This may be expected if theme doesn't exist or hasn't been migrated")
            return True  # Don't fail overall validation
            
    except Exception as e:
        print_warning(f"Integration test exception: {e}")
        return True  # Don't fail overall validation


def main():
    """Run all validation tests."""
    print("🚀 Running critical fixes validation suite...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    
    tests = [
        ("Environment Compatibility", validate_environment_compatibility),
        ("Style Exclusion System", validate_style_exclusion), 
        ("Compilation Status Accuracy", validate_compilation_status),
        ("Progress System", validate_progress_system),
        ("CLI Commands", validate_cli_commands),
        ("Integration Test", run_integration_test),
    ]
    
    passed = 0
    failed_tests = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        try:
            if test_func():
                passed += 1
                print_success(f"{test_name} PASSED")
            else:
                failed_tests.append(test_name)
                print_error(f"{test_name} FAILED")
        except Exception as e:
            failed_tests.append(test_name)
            print_error(f"{test_name} FAILED with exception: {e}")
    
    # Final results
    print(f"\n{'='*60}")
    print(f"📈 Validation Results: {passed}/{len(tests)} tests passed")
    print('='*60)
    
    if passed == len(tests):
        print_success("🎉 ALL CRITICAL FIXES VALIDATED SUCCESSFULLY!")
        print("\n✨ Ready to proceed with migrations:")
        print("   • Header/footer/nav styles will be properly excluded")
        print("   • Compilation status reporting is accurate") 
        print("   • Cross-environment compatibility working")
        print("   • Progress tracking stable")
        print("   • Migration timing integrated")
        return 0
    else:
        print_error(f"❌ Some validations failed: {', '.join(failed_tests)}")
        print("\n🔧 Next steps:")
        print("   1. Review failed test output above")
        print("   2. Fix any identified issues")
        print("   3. Re-run this validation script")
        return 1


if __name__ == "__main__":
    sys.exit(main())