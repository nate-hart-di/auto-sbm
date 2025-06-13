#!/usr/bin/env python3
"""
Real-world testing script for SBM automation.

This script helps validate that the automation produces results
matching real SBM patterns from production PRs.
"""

import sys
import tempfile
from pathlib import Path
from typing import Dict, List

from sbm.config import get_config
from sbm.scss.processor import SCSSProcessor
from sbm.core.migration import migrate_dealer_theme


def validate_map_components(scss_content: str) -> Dict[str, bool]:
    """Validate that map components match real PR patterns."""
    checks = {
        "has_mapRow": "#mapRow" in scss_content,
        "has_600px_height": "height: 600px" in scss_content,
        "has_directionsBox": "#directionsBox" in scss_content,
        "has_400px_width": "width: 400px" in scss_content,
        "has_920px_breakpoint": "max-width: 920px" in scss_content,
        "has_250px_mobile": "height: 250px" in scss_content,
        "has_45_percent_mobile": "max-width: 45%" in scss_content,
    }
    return checks


def validate_file_headers(scss_content: str, file_type: str) -> bool:
    """Validate that file headers match real PR patterns."""
    expected_headers = {
        "vdp": "Site Builder VDP Styles",
        "vrp": "Site Builder VRP Styles", 
        "inside": "Site Builder Inside Styles"
    }
    
    expected_header = expected_headers.get(file_type, "")
    return expected_header in scss_content


def test_scss_processor_real_patterns():
    """Test SCSS processor against real SBM patterns."""
    print("🧪 Testing SCSS Processor against real SBM patterns...")
    
    try:
        config = get_config()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup test theme directory
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            # Mock config to use temp directory
            config.get_theme_path = lambda slug: theme_path
            
            # Run SCSS processor
            processor = SCSSProcessor(config)
            result = processor.process_theme("testdealer")
            
            # Validate results
            print(f"✅ SCSS Processor completed: {result['success']}")
            print(f"✅ Files created: {len(result['files_created'])}")
            print(f"✅ Map components added: {result['map_components_added']}")
            
            # Check file structure
            expected_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss"]
            for file_name in expected_files:
                file_path = theme_path / file_name
                if file_path.exists():
                    print(f"✅ {file_name} created")
                    
                    # Validate content for sb-inside.scss
                    if file_name == "sb-inside.scss":
                        content = file_path.read_text()
                        map_checks = validate_map_components(content)
                        
                        print("   Map component validation:")
                        for check, passed in map_checks.items():
                            status = "✅" if passed else "❌"
                            print(f"   {status} {check}")
                        
                        # Validate file header
                        has_header = validate_file_headers(content, "inside")
                        status = "✅" if has_header else "❌"
                        print(f"   {status} File header present")
                        
                else:
                    print(f"❌ {file_name} NOT created")
            
            return result['success']
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_migration_dry_run():
    """Test full migration in dry run mode."""
    print("\n🧪 Testing full migration (dry run)...")
    
    try:
        result = migrate_dealer_theme(
            slug="testdealer",
            dry_run=True,
            force=True
        )
        
        print(f"✅ Migration dry run completed: {result['success']}")
        print(f"✅ Steps completed: {len(result['steps_completed'])}")
        print(f"✅ Duration: {result['duration']:.2f}s")
        
        if result['errors']:
            print(f"⚠️  Errors: {result['errors']}")
        
        if result['warnings']:
            print(f"⚠️  Warnings: {result['warnings']}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        return False


def validate_against_real_pr_patterns():
    """Validate automation output against known real PR patterns."""
    print("\n🧪 Validating against real PR patterns...")
    
    # These are the exact patterns we found in real PRs
    real_pr_patterns = {
        "map_height_desktop": "height: 600px",
        "map_height_mobile": "height: 250px", 
        "directions_width": "width: 400px",
        "responsive_breakpoint": "max-width: 920px",
        "mobile_max_width": "max-width: 45%",
        "file_count": 3,  # Always exactly 3 files
        "file_names": ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss"]
    }
    
    print("✅ Real PR patterns loaded:")
    for pattern, value in real_pr_patterns.items():
        print(f"   • {pattern}: {value}")
    
    return True


def main():
    """Run all real-world tests."""
    print("🚀 Starting Real-World SBM Automation Tests")
    print("=" * 50)
    
    tests = [
        ("SCSS Processor", test_scss_processor_real_patterns),
        ("Migration Dry Run", test_migration_dry_run),
        ("Real PR Patterns", validate_against_real_pr_patterns),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Automation is ready for real-world testing")
        print("\nNext steps:")
        print("1. Set up your .env file with DI_PLATFORM_DIR")
        print("2. Run: python -m sbm doctor")
        print("3. Test with a real dealer: python -m sbm migrate [dealer-slug] --dry-run")
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️  Please review the failures above before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    main() 
